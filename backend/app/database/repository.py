import re
from typing import Any, Optional

import jieba

from app.database.connection import get_connection


def get_record_by_id(record_id: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM qiaopi_text_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    return dict(row) if row else None


def count_rows(table_name: str) -> int:
    allowed_tables = {
        "qiaopi_metadata_records",
        "qiaopi_text_records",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table: {table_name}")
    with get_connection() as connection:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def fetch_chart_items(
    *,
    table_name: str,
    label_expression: str,
    where_clause: str = "",
    group_expression: str | None = None,
    order_expression: str = "value DESC",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    allowed_tables = {
        "qiaopi_metadata_records",
        "qiaopi_text_records",
        "qiaopi_entity_mentions",
        "qiaopi_amount_mentions",
    }
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table: {table_name}")

    group_by = group_expression or label_expression
    sql = (
        f"SELECT {label_expression} AS label, COUNT(*) AS value "
        f"FROM {table_name} "
        f"{where_clause} "
        f"GROUP BY {group_by} "
        f"ORDER BY {order_expression}"
    )
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)

    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [
        {"label": str(row["label"] or ""), "value": int(row["value"])}
        for row in rows
        if str(row["label"] or "").strip()
    ]


def get_record_entities(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT entity_type, entity_text, normalized_text, source_field, confidence
            FROM qiaopi_entity_mentions
            WHERE record_id = ?
            ORDER BY mention_id
            """,
            (record_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_record_evidence(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT evidence_type, evidence_text, source_column
            FROM qiaopi_evidence_spans
            WHERE record_id = ?
            ORDER BY evidence_id
            """,
            (record_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_primary_amount(record_id: str) -> Optional[dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT raw_text, amount_text, amount_number, currency, sentence, source_field
            FROM qiaopi_amount_mentions
            WHERE record_id = ?
            ORDER BY is_primary_candidate DESC, mention_id
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
    return dict(row) if row else None


_QUERY_ALIASES = {
    "eight": ["八", "捌"],
    "yuan": ["元"],
    "mother": ["母亲", "慈亲", "双亲"],
    "father": ["父亲", "严亲", "双亲"],
    "letter": ["侨批", "家书"],
    "singapore": ["新加坡", "叻坡", "叻"],
    "八元": ["八元", "捌元"],
    "十元": ["十元", "拾元"],
    "母亲": ["母亲", "慈亲", "双亲"],
}


def _query_terms(query: str) -> list[str]:
    raw_terms = [
        term
        for term in re.split(r"[\s,，。；;、]+", query.strip())
        if term
    ]
    if (
        len(raw_terms) == 1
        and len(raw_terms[0]) > 4
        and re.search(r"[\u4e00-\u9fff]", raw_terms[0])
    ):
        raw_terms = [
            term
            for term in jieba.lcut(raw_terms[0])
            if len(term.strip()) > 1 and term not in {"这个", "一封", "相关"}
        ]
    expanded: list[str] = []
    for term in raw_terms:
        aliases = _QUERY_ALIASES.get(term.lower(), [term])
        for alias in aliases:
            if alias not in expanded:
                expanded.append(alias)
    return expanded


def _fts_query(query: str) -> str:
    terms = _query_terms(query)
    return " OR ".join(f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms)


def _matches_filter(row: dict[str, Any], key: str, value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True

    if key == "origin_place":
        return normalized in str(row.get("origin_place", "")).lower()
    if key == "destination_place":
        return normalized in str(row.get("destination_place", "")).lower()
    if key == "kinship":
        kinship_text = " ".join(
            [
                str(row.get("kinship", "")),
                str(row.get("recipient", "")),
                str(row.get("relationship_type", "")),
                str(row.get("body_clean", "")),
            ]
        ).lower()
        aliases = _QUERY_ALIASES.get(normalized, [normalized])
        return any(alias.lower() in kinship_text for alias in aliases)
    return normalized in str(row.get(key, "")).lower()


def search_text_records(
    query: str,
    *,
    filters: dict[str, Optional[str]],
) -> list[dict[str, Any]]:
    fts_query = _fts_query(query)
    with get_connection() as connection:
        if fts_query:
            rows = connection.execute(
                """
                SELECT
                    qiaopi_retrieval_units_fts.record_id,
                    qiaopi_retrieval_units_fts.unit_id,
                    qiaopi_retrieval_units_fts.unit_type,
                    qiaopi_retrieval_units_fts.unit_text,
                    bm25(qiaopi_retrieval_units_fts) AS rank,
                    t.*,
                    (
                        SELECT COALESCE(NULLIF(a.raw_text, ''), a.amount_text)
                        FROM qiaopi_amount_mentions AS a
                        WHERE a.record_id = t.record_id
                        ORDER BY a.is_primary_candidate DESC, a.mention_id
                        LIMIT 1
                    ) AS money,
                    (
                        SELECT COALESCE(NULLIF(e.normalized_text, ''), e.entity_text)
                        FROM qiaopi_entity_mentions AS e
                        WHERE e.record_id = t.record_id AND e.entity_type = 'kinship'
                        ORDER BY e.mention_id
                        LIMIT 1
                    ) AS kinship
                FROM qiaopi_retrieval_units_fts
                JOIN qiaopi_text_records AS t
                  ON t.record_id = qiaopi_retrieval_units_fts.record_id
                WHERE qiaopi_retrieval_units_fts MATCH ?
                ORDER BY rank
                LIMIT 2000
                """,
                (fts_query,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    t.record_id,
                    '' AS unit_id,
                    'record_full' AS unit_type,
                    COALESCE(NULLIF(t.body_core, ''), t.body_clean) AS unit_text,
                    0.0 AS rank,
                    t.*,
                    (
                        SELECT COALESCE(NULLIF(a.raw_text, ''), a.amount_text)
                        FROM qiaopi_amount_mentions AS a
                        WHERE a.record_id = t.record_id
                        ORDER BY a.is_primary_candidate DESC, a.mention_id
                        LIMIT 1
                    ) AS money,
                    (
                        SELECT COALESCE(NULLIF(e.normalized_text, ''), e.entity_text)
                        FROM qiaopi_entity_mentions AS e
                        WHERE e.record_id = t.record_id AND e.entity_type = 'kinship'
                        ORDER BY e.mention_id
                        LIMIT 1
                    ) AS kinship
                FROM qiaopi_text_records AS t
                ORDER BY t.record_id
                """
            ).fetchall()

    deduplicated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for db_row in rows:
        row = dict(db_row)
        record_id = str(row["record_id"])
        if record_id in seen:
            continue
        if not all(
            _matches_filter(row, key, value)
            for key, value in filters.items()
            if value
        ):
            continue
        seen.add(record_id)
        deduplicated.append(row)
    return deduplicated
