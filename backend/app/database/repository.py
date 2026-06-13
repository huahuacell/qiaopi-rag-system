from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Mapping, Optional

from app.database.connection import get_connection
from app.search.fts_index import search_fts


TEXT_RECORD_COLUMNS: tuple[str, ...] = (
    "record_id",
    "title_reference",
    "sender",
    "recipient",
    "sender_name_clean",
    "recipient_name_clean",
    "date_text",
    "year_normalized",
    "body_clean",
    "body_core",
    "main_intent",
    "theme_tags",
    "text_quality_level",
    "has_full_text",
    "has_remittance",
    "relationship_type",
    "place_mentions_normalized",
    "retrieval_keywords",
    "rag_summary_text",
    "style_reference_text",
    "raw_json",
)

AMOUNT_COLUMNS: tuple[str, ...] = (
    "mention_id",
    "record_id",
    "raw_text",
    "amount_text",
    "amount_number",
    "currency",
    "sentence",
    "is_primary_candidate",
    "source_field",
)

ENTITY_COLUMNS: tuple[str, ...] = (
    "mention_id",
    "record_id",
    "entity_type",
    "entity_text",
    "normalized_text",
    "source_field",
    "confidence",
)

PLACE_COLUMNS: tuple[str, ...] = (
    "mention_id",
    "record_id",
    "alias_text",
    "normalized_place",
    "country_or_region",
    "source_field",
)

EVIDENCE_COLUMNS: tuple[str, ...] = (
    "evidence_id",
    "record_id",
    "evidence_type",
    "evidence_text",
    "source_column",
    "start_char",
    "end_char",
)

RETRIEVAL_UNIT_COLUMNS: tuple[str, ...] = (
    "unit_id",
    "record_id",
    "unit_type",
    "source_column",
    "unit_text",
    "title_reference",
    "sender",
    "recipient",
    "date_text",
    "main_intent",
    "theme_tags",
    "style_keywords",
    "relationship_type",
    "place_mentions_normalized",
    "retrieval_keywords",
    "weight",
    "evidence_type",
    "fts_text",
    "raw_json",
)


def _clean_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return value


def _text(value: Any) -> str:
    value = _clean_value(value)
    return str(value).strip()


def _number_or_none(value: Any) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int_or_none(value: Any) -> int | None:
    text = _text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _flag_or_none(value: Any) -> int | None:
    text = _text(value).lower()
    if text in {"1", "true", "yes", "y"}:
        return 1
    if text in {"0", "false", "no", "n"}:
        return 0
    return _int_or_none(value)


def _json_dump(row: Mapping[str, Any]) -> str:
    clean_row = {key: _text(value) for key, value in row.items()}
    return json.dumps(clean_row, ensure_ascii=False, sort_keys=True)


def _insert_rows(
    connection: sqlite3.Connection,
    table_name: str,
    columns: tuple[str, ...],
    rows: Iterable[Mapping[str, Any]],
) -> int:
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table_name} ({column_sql}) VALUES ({placeholders})"
    values = [tuple(row.get(column) for column in columns) for row in rows]
    if values:
        connection.executemany(sql, values)
    return len(values)


def insert_text_records(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        record = {column: _text(row.get(column)) for column in TEXT_RECORD_COLUMNS}
        record["has_full_text"] = _flag_or_none(row.get("has_full_text"))
        record["has_remittance"] = _flag_or_none(row.get("has_remittance"))
        record["raw_json"] = _json_dump(row)
        prepared_rows.append(record)
    return _insert_rows(
        connection,
        "qiaopi_text_records",
        TEXT_RECORD_COLUMNS,
        prepared_rows,
    )


def insert_amount_mentions(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "mention_id": _text(row.get("mention_id")),
                "record_id": _text(row.get("record_id")),
                "raw_text": _text(row.get("raw_text")),
                "amount_text": _text(row.get("amount_text")),
                "amount_number": _number_or_none(row.get("amount_number")),
                "currency": _text(row.get("currency")),
                "sentence": _text(row.get("sentence")),
                "is_primary_candidate": _flag_or_none(row.get("is_primary_candidate")),
                "source_field": _text(row.get("source_field")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_amount_mentions",
        AMOUNT_COLUMNS,
        prepared_rows,
    )


def insert_entity_mentions(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "mention_id": _text(row.get("mention_id")),
                "record_id": _text(row.get("record_id")),
                "entity_type": _text(row.get("entity_type")),
                "entity_text": _text(row.get("entity_text")),
                "normalized_text": _text(row.get("normalized_text")),
                "source_field": _text(row.get("source_field")),
                "confidence": _number_or_none(row.get("confidence")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_entity_mentions",
        ENTITY_COLUMNS,
        prepared_rows,
    )


def insert_place_mentions(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "mention_id": _text(row.get("mention_id")),
                "record_id": _text(row.get("record_id")),
                "alias_text": _text(row.get("alias_text")),
                "normalized_place": _text(row.get("normalized_place")),
                "country_or_region": _text(row.get("country_or_region")),
                "source_field": _text(row.get("source_field")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_place_mentions",
        PLACE_COLUMNS,
        prepared_rows,
    )


def insert_evidence_spans(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "evidence_id": _text(row.get("evidence_id")),
                "record_id": _text(row.get("record_id")),
                "evidence_type": _text(row.get("evidence_type")),
                "evidence_text": _text(row.get("evidence_text")),
                "source_column": _text(row.get("source_column")),
                "start_char": _int_or_none(row.get("start_char")),
                "end_char": _int_or_none(row.get("end_char")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_evidence_spans",
        EVIDENCE_COLUMNS,
        prepared_rows,
    )


def insert_retrieval_units(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "unit_id": _text(row.get("unit_id")),
                "record_id": _text(row.get("record_id")),
                "unit_type": _text(row.get("unit_type")),
                "source_column": _text(row.get("source_column")),
                "unit_text": _text(row.get("unit_text")),
                "title_reference": _text(row.get("title_reference")),
                "sender": _text(row.get("sender")),
                "recipient": _text(row.get("recipient")),
                "date_text": _text(row.get("date_text")),
                "main_intent": _text(row.get("main_intent")),
                "theme_tags": _text(row.get("theme_tags")),
                "style_keywords": _text(row.get("style_keywords")),
                "relationship_type": _text(row.get("relationship_type")),
                "place_mentions_normalized": _text(row.get("place_mentions_normalized")),
                "retrieval_keywords": _text(row.get("retrieval_keywords")),
                "weight": _number_or_none(row.get("weight")) or 1.0,
                "evidence_type": _text(row.get("evidence_type")),
                "fts_text": _text(row.get("fts_text")),
                "raw_json": _text(row.get("raw_json")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_retrieval_units",
        RETRIEVAL_UNIT_COLUMNS,
        prepared_rows,
    )


def count_rows(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])


def get_record_by_id(record_id: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM qiaopi_text_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    return dict(row) if row else None


def list_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type IN ('table', 'view')
        ORDER BY name
        """
    ).fetchall()
    return [row["name"] for row in rows]


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _chart_rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, int | str]]:
    return [
        {
            "label": row["label"] if row["label"] not in (None, "") else "unknown",
            "value": int(row["value"]),
        }
        for row in rows
    ]


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def fetch_dashboard_stats() -> dict[str, int]:
    with get_connection() as connection:
        return {
            "total_text_records": count_rows(connection, "qiaopi_text_records"),
            "full_text_count": _safe_int(
                connection.execute(
                    "SELECT COUNT(*) FROM qiaopi_text_records WHERE has_full_text = 1"
                ).fetchone()[0]
            ),
            "metadata_only_count": _safe_int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM qiaopi_text_records
                    WHERE text_quality_level = 'metadata_only'
                    """
                ).fetchone()[0]
            ),
            "retrieval_unit_count": count_rows(connection, "qiaopi_retrieval_units"),
            "fts_row_count": count_rows(connection, "qiaopi_retrieval_units_fts"),
            "amount_mention_count": count_rows(connection, "qiaopi_amount_mentions"),
            "entity_mention_count": count_rows(connection, "qiaopi_entity_mentions"),
            "place_mention_count": count_rows(connection, "qiaopi_place_mentions"),
            "evidence_count": count_rows(connection, "qiaopi_evidence_spans"),
            "remittance_record_count": _safe_int(
                connection.execute(
                    "SELECT COUNT(*) FROM qiaopi_text_records WHERE has_remittance = 1"
                ).fetchone()[0]
            ),
        }


def fetch_dashboard_distributions(limit: int = 10) -> dict[str, list[dict[str, int | str]]]:
    with get_connection() as connection:
        text_quality_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(text_quality_level, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_text_records
            GROUP BY label
            ORDER BY value DESC, label ASC
            """
        ).fetchall()
        main_intent_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(main_intent, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_text_records
            GROUP BY label
            ORDER BY value DESC, label ASC
            """
        ).fetchall()
        relationship_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(relationship_type, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_text_records
            GROUP BY label
            ORDER BY value DESC, label ASC
            """
        ).fetchall()
        unit_type_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(unit_type, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_retrieval_units
            GROUP BY label
            ORDER BY value DESC, label ASC
            """
        ).fetchall()
        top_place_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(normalized_place, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_place_mentions
            GROUP BY label
            ORDER BY value DESC, label ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        top_country_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(country_or_region, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_place_mentions
            GROUP BY label
            ORDER BY value DESC, label ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        year_rows = connection.execute(
            """
            SELECT COALESCE(NULLIF(year_normalized, ''), 'unknown') AS label,
                   COUNT(*) AS value
            FROM qiaopi_text_records
            GROUP BY label
            ORDER BY label ASC
            """
        ).fetchall()

    return {
        "text_quality_distribution": _chart_rows(text_quality_rows),
        "main_intent_distribution": _chart_rows(main_intent_rows),
        "relationship_distribution": _chart_rows(relationship_rows),
        "unit_type_distribution": _chart_rows(unit_type_rows),
        "top_places": _chart_rows(top_place_rows),
        "top_countries_or_regions": _chart_rows(top_country_rows),
        "year_distribution": _chart_rows(year_rows),
    }


def fetch_text_record(record_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM qiaopi_text_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_amount_mentions(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_amount_mentions
            WHERE record_id = ?
            ORDER BY mention_id
            """,
            (record_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_entity_mentions(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_entity_mentions
            WHERE record_id = ?
            ORDER BY mention_id
            """,
            (record_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_place_mentions(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_place_mentions
            WHERE record_id = ?
            ORDER BY mention_id
            """,
            (record_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_evidence_spans(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM qiaopi_evidence_spans
            WHERE record_id = ?
            ORDER BY evidence_id
            """,
            (record_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_retrieval_units(record_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                unit_id,
                record_id,
                unit_type,
                source_column,
                unit_text,
                title_reference,
                sender,
                recipient,
                date_text,
                main_intent,
                theme_tags,
                style_keywords,
                relationship_type,
                place_mentions_normalized,
                retrieval_keywords,
                weight,
                evidence_type,
                fts_text
            FROM qiaopi_retrieval_units
            WHERE record_id = ?
            ORDER BY unit_type, unit_id
            """,
            (record_id,),
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_all_retrieval_units() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                r.unit_id,
                r.record_id,
                r.unit_type,
                r.source_column,
                r.unit_text,
                r.title_reference,
                r.sender,
                r.recipient,
                r.date_text,
                r.main_intent,
                r.theme_tags,
                r.style_keywords,
                r.relationship_type,
                r.place_mentions_normalized,
                r.retrieval_keywords,
                r.weight,
                r.evidence_type,
                r.fts_text,
                t.text_quality_level,
                t.has_remittance,
                t.year_normalized,
                COALESCE(p.normalized_places, '') AS normalized_places,
                COALESCE(p.countries_or_regions, '') AS countries_or_regions
            FROM qiaopi_retrieval_units AS r
            JOIN qiaopi_text_records AS t
                ON t.record_id = r.record_id
            LEFT JOIN (
                SELECT
                    record_id,
                    GROUP_CONCAT(DISTINCT normalized_place) AS normalized_places,
                    GROUP_CONCAT(DISTINCT country_or_region) AS countries_or_regions
                FROM qiaopi_place_mentions
                GROUP BY record_id
            ) AS p
                ON p.record_id = r.record_id
            ORDER BY r.unit_id
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def _matches_filters(row: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    if not filters:
        return True
    exact_keys = {
        "record_id",
        "unit_id",
        "sender",
        "recipient",
        "date_text",
        "main_intent",
        "relationship_type",
        "text_quality_level",
        "year_normalized",
        "evidence_type",
        "source_column",
    }
    for key, value in filters.items():
        if value in (None, "", []):
            continue
        if key in exact_keys and str(row.get(key, "")) != str(value):
            return False
        if key == "unit_type" and str(row.get("unit_type", "")) != str(value):
            return False
        if key == "unit_types":
            values = {str(item) for item in value}
            if str(row.get("unit_type", "")) not in values:
                return False
        if key == "theme" and str(value) not in str(row.get("theme_tags", "")):
            return False
        if key == "place":
            haystack = "；".join(
                [
                    str(row.get("place_mentions_normalized", "")),
                    str(row.get("normalized_places", "")),
                ]
            )
            if str(value) not in haystack:
                return False
        if key == "country_or_region":
            if str(value) not in str(row.get("countries_or_regions", "")):
                return False
        if key == "has_remittance":
            expected = 1 if str(value).lower() in {"1", "true", "yes"} else 0
            if _safe_int(row.get("has_remittance")) != expected:
                return False
    return True


def _fetch_top_retrieval_units(top_k: int, unit_types: Iterable[str] | None) -> list[dict[str, Any]]:
    unit_types = [unit_type for unit_type in (unit_types or []) if unit_type]
    params: list[Any] = []
    unit_type_clause = ""
    if unit_types:
        placeholders = ", ".join("?" for _ in unit_types)
        unit_type_clause = f"WHERE unit_type IN ({placeholders})"
        params.extend(unit_types)
    params.append(top_k)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                r.unit_id,
                r.record_id,
                r.unit_type,
                r.title_reference,
                r.sender,
                r.recipient,
                r.date_text,
                r.main_intent,
                r.unit_text,
                0.0 AS score,
                0.0 AS bm25_score,
                r.evidence_type,
                r.source_column,
                r.theme_tags,
                r.style_keywords,
                r.relationship_type,
                r.place_mentions_normalized,
                r.retrieval_keywords,
                r.fts_text,
                r.weight,
                t.text_quality_level,
                t.has_remittance,
                t.year_normalized,
                COALESCE(p.normalized_places, '') AS normalized_places,
                COALESCE(p.countries_or_regions, '') AS countries_or_regions
            FROM qiaopi_retrieval_units AS r
            JOIN qiaopi_text_records AS t
                ON t.record_id = r.record_id
            LEFT JOIN (
                SELECT
                    record_id,
                    GROUP_CONCAT(DISTINCT normalized_place) AS normalized_places,
                    GROUP_CONCAT(DISTINCT country_or_region) AS countries_or_regions
                FROM qiaopi_place_mentions
                GROUP BY record_id
            ) AS p
                ON p.record_id = r.record_id
            {unit_type_clause}
            ORDER BY r.weight DESC, r.unit_id ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return _rows_to_dicts(rows)


def search_retrieval_units(
    query: str,
    top_k: int = 10,
    unit_types: Iterable[str] | None = None,
    filters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    filters = filters or {}
    if not query.strip():
        results = _fetch_top_retrieval_units(max(top_k * 5, top_k), unit_types)
    else:
        with get_connection() as connection:
            results = search_fts(
                connection,
                query=query,
                top_k=max(top_k * 5, top_k),
                unit_types=unit_types,
            )
    filtered_results = [row for row in results if _matches_filters(row, filters)]
    return filtered_results[:top_k]


def insert_query_log(
    *,
    endpoint: str,
    query: str,
    filters: Mapping[str, Any] | None,
    top_k: int,
    returned_count: int,
) -> None:
    filters_json = json.dumps(filters or {}, ensure_ascii=False, sort_keys=True)
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO qiaopi_query_logs (
                endpoint,
                query,
                filters_json,
                top_k,
                returned_count
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (endpoint, query, filters_json, top_k, returned_count),
        )
