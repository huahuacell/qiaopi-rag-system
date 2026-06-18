from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Iterable, Mapping, Optional

from app.database.connection import get_connection
from app.search.fts_index import search_fts
from app.utils.date_normalizer import normalize_qiaopi_date
from app.utils.place_normalizer import normalize_qiaopi_place_fields


TEXT_RECORD_COLUMNS: tuple[str, ...] = (
    "record_id",
    "title_reference",
    "sender",
    "recipient",
    "sender_name_clean",
    "recipient_name_clean",
    "date_text",
    "year_normalized",
    "date_standard",
    "date_year",
    "date_month",
    "date_day",
    "date_precision",
    "date_calendar",
    "date_parse_confidence",
    "date_parse_note",
    "body_clean",
    "body_core",
    "main_intent",
    "theme_tags",
    "text_quality_level",
    "has_full_text",
    "has_remittance",
    "relationship_type",
    "origin_place",
    "destination_place",
    "place_mentions_normalized",
    "country_or_region",
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

METADATA_RECORD_COLUMNS: tuple[str, ...] = (
    "metadata_id",
    "source_index",
    "title_raw",
    "title_clean",
    "sender_raw",
    "recipient_raw",
    "sender_name_clean",
    "recipient_name_clean",
    "date_text",
    "year_normalized",
    "date_standard",
    "date_year",
    "date_month",
    "date_day",
    "date_precision",
    "date_calendar",
    "date_parse_confidence",
    "date_parse_note",
    "era_text",
    "origin_place",
    "destination_place",
    "place_mentions",
    "country_or_region",
    "remittance_raw",
    "amount_number",
    "currency",
    "has_remittance",
    "kinship_terms",
    "relationship_type",
    "theme_tags",
    "main_intent",
    "has_linked_text",
    "linked_record_id",
    "parse_confidence",
    "needs_review",
    "warnings",
    "raw_json",
)

METADATA_LINK_COLUMNS: tuple[str, ...] = (
    "link_id",
    "record_id",
    "metadata_id",
    "link_method",
    "link_confidence",
    "title_similarity",
    "matched_fields_json",
)

METADATA_LINK_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "record_id",
    "metadata_id",
    "candidate_method",
    "candidate_confidence",
    "title_similarity",
    "matched_fields_json",
    "reason",
)

METADATA_FTS_TABLE = "qiaopi_metadata_fts"
METADATA_FTS_COLUMNS: tuple[str, ...] = (
    "metadata_id",
    "title_clean",
    "sender_raw",
    "recipient_raw",
    "sender_name_clean",
    "recipient_name_clean",
    "date_text",
    "year_normalized",
    "origin_place",
    "destination_place",
    "place_mentions",
    "country_or_region",
    "remittance_raw",
    "kinship_terms",
    "relationship_type",
    "theme_tags",
    "main_intent",
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


def _date_context(row: Mapping[str, Any], *columns: str) -> str:
    return "；".join(_text(row.get(column)) for column in columns if _text(row.get(column)))


def _normalized_date_fields(
    row: Mapping[str, Any],
    *,
    context_columns: tuple[str, ...],
) -> dict[str, Any]:
    normalized = normalize_qiaopi_date(
        row.get("date_text"),
        context_text=_date_context(row, *context_columns),
        year_hint=row.get("year_normalized"),
    )
    return normalized.as_db_fields()


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
        record.update(
            _normalized_date_fields(
                row,
                context_columns=("title_reference",),
            )
        )
        record.update(normalize_qiaopi_place_fields(row).as_db_fields())
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


def insert_metadata_records(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        record = {column: _text(row.get(column)) for column in METADATA_RECORD_COLUMNS}
        record.update(
            _normalized_date_fields(
                row,
                context_columns=("title_raw", "era_text"),
            )
        )
        record["source_index"] = _int_or_none(row.get("source_index")) or 0
        record["amount_number"] = _number_or_none(row.get("amount_number"))
        record["has_remittance"] = _flag_or_none(row.get("has_remittance")) or 0
        record["has_linked_text"] = _flag_or_none(row.get("has_linked_text")) or 0
        record["parse_confidence"] = _number_or_none(row.get("parse_confidence")) or 0.0
        record["needs_review"] = _flag_or_none(row.get("needs_review")) or 0
        prepared_rows.append(record)
    return _insert_rows(
        connection,
        "qiaopi_metadata_records",
        METADATA_RECORD_COLUMNS,
        prepared_rows,
    )


def _assert_metadata_fts5_available(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.__metadata_fts5_check USING fts5(value)")
        connection.execute("DROP TABLE temp.__metadata_fts5_check")
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "SQLite FTS5 is required for qiaopi metadata search, but this sqlite3 "
            "build does not support FTS5. Use a Python/SQLite build with FTS5 enabled."
        ) from exc


def create_metadata_fts_index(connection: sqlite3.Connection) -> None:
    _assert_metadata_fts5_available(connection)
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {METADATA_FTS_TABLE}
        USING fts5(
            metadata_id UNINDEXED,
            title_clean,
            sender_raw,
            recipient_raw,
            sender_name_clean,
            recipient_name_clean,
            date_text,
            year_normalized,
            origin_place,
            destination_place,
            place_mentions,
            country_or_region,
            remittance_raw,
            kinship_terms,
            relationship_type,
            theme_tags,
            main_intent,
            tokenize='unicode61'
        )
        """
    )


def reset_metadata_catalog_tables(connection: sqlite3.Connection) -> None:
    connection.execute(f"DROP TABLE IF EXISTS {METADATA_FTS_TABLE}")
    connection.execute("DELETE FROM qiaopi_text_metadata_link_candidates")
    connection.execute("DELETE FROM qiaopi_text_metadata_links")
    connection.execute("DELETE FROM qiaopi_metadata_records")


def rebuild_metadata_fts_index(connection: sqlite3.Connection) -> int:
    create_metadata_fts_index(connection)
    connection.execute(f"DELETE FROM {METADATA_FTS_TABLE}")
    column_sql = ", ".join(METADATA_FTS_COLUMNS)
    connection.execute(
        f"""
        INSERT INTO {METADATA_FTS_TABLE} ({column_sql})
        SELECT {column_sql}
        FROM qiaopi_metadata_records
        ORDER BY source_index
        """
    )
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {METADATA_FTS_TABLE}").fetchone()
    return int(row["count"])


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
            "metadata_record_count": count_rows(connection, "qiaopi_metadata_records"),
            "metadata_linked_text_count": _safe_int(
                connection.execute(
                    "SELECT COUNT(*) FROM qiaopi_metadata_records WHERE has_linked_text = 1"
                ).fetchone()[0]
            ),
            "metadata_link_candidate_count": count_rows(connection, "qiaopi_text_metadata_link_candidates"),
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


def _metadata_match_query(query: str) -> str:
    tokens = [
        token.strip()
        for token in re.split(r"[\s；;，,、。！？!?：:（）()【】\[\]《》<>“”\"'‘’/|\\]+", query)
        if token.strip()
    ]
    if not tokens:
        return ""
    escaped_tokens = [token.replace('"', '""') for token in tokens]
    return " OR ".join(f'"{token}"' for token in escaped_tokens)


def _metadata_filter_sql(filters: Mapping[str, Any] | None) -> tuple[str, list[Any]]:
    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []
    if filters.get("year_from") not in (None, ""):
        clauses.append("CAST(NULLIF(m.year_normalized, '') AS INTEGER) >= ?")
        params.append(int(filters["year_from"]))
    if filters.get("year_to") not in (None, ""):
        clauses.append("CAST(NULLIF(m.year_normalized, '') AS INTEGER) <= ?")
        params.append(int(filters["year_to"]))
    for key in ("country_or_region", "relationship_type", "main_intent"):
        if filters.get(key) not in (None, ""):
            clauses.append(f"m.{key} = ?")
            params.append(str(filters[key]))
    for key in ("origin_place", "destination_place", "place"):
        if filters.get(key) not in (None, ""):
            column = "place_mentions" if key == "place" else key
            clauses.append(f"m.{column} LIKE ?")
            params.append(f"%{filters[key]}%")
    for key in ("has_remittance", "has_linked_text", "needs_review"):
        if filters.get(key) not in (None, ""):
            expected = 1 if str(filters[key]).lower() in {"1", "true", "yes"} else 0
            clauses.append(f"m.{key} = ?")
            params.append(expected)
    where_sql = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


def fetch_metadata_stats() -> dict[str, Any]:
    with get_connection() as connection:
        year_row = connection.execute(
            """
            SELECT
                MIN(CAST(NULLIF(year_normalized, '') AS INTEGER)) AS year_min,
                MAX(CAST(NULLIF(year_normalized, '') AS INTEGER)) AS year_max
            FROM qiaopi_metadata_records
            WHERE year_normalized != ''
            """
        ).fetchone()
        total_count = count_rows(connection, "qiaopi_metadata_records")
        linked_count = _safe_int(
            connection.execute(
                "SELECT COUNT(*) FROM qiaopi_metadata_records WHERE has_linked_text = 1"
            ).fetchone()[0]
        )
        return {
            "total_metadata_records": total_count,
            "linked_text_count": linked_count,
            "unlinked_metadata_count": max(total_count - linked_count, 0),
            "link_candidate_count": count_rows(connection, "qiaopi_text_metadata_link_candidates"),
            "has_remittance_count": _safe_int(
                connection.execute(
                    "SELECT COUNT(*) FROM qiaopi_metadata_records WHERE has_remittance = 1"
                ).fetchone()[0]
            ),
            "needs_review_count": _safe_int(
                connection.execute(
                    "SELECT COUNT(*) FROM qiaopi_metadata_records WHERE needs_review = 1"
                ).fetchone()[0]
            ),
            "year_min": year_row["year_min"],
            "year_max": year_row["year_max"],
        }


def _distribution_for_metadata_column(
    connection: sqlite3.Connection,
    column: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT COALESCE(NULLIF({column}, ''), 'unknown') AS label,
               COUNT(*) AS value
        FROM qiaopi_metadata_records
        GROUP BY label
        ORDER BY value DESC, label ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return _chart_rows(rows)


def _split_distribution_for_metadata_column(
    connection: sqlite3.Connection,
    column: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"SELECT {column} FROM qiaopi_metadata_records WHERE {column} != ''"
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        for value in str(row[column]).split("；"):
            clean_value = value.strip()
            if not clean_value:
                continue
            counts[clean_value] = counts.get(clean_value, 0) + 1
    return [
        {"label": label, "value": value}
        for label, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def fetch_metadata_distributions(limit: int = 20) -> dict[str, list[dict[str, Any]]]:
    with get_connection() as connection:
        return {
            "year_distribution": _distribution_for_metadata_column(connection, "year_normalized", limit),
            "country_or_region_distribution": _distribution_for_metadata_column(
                connection, "country_or_region", limit
            ),
            "origin_place_distribution": _distribution_for_metadata_column(connection, "origin_place", limit),
            "destination_place_distribution": _distribution_for_metadata_column(
                connection, "destination_place", limit
            ),
            "relationship_distribution": _distribution_for_metadata_column(
                connection, "relationship_type", limit
            ),
            "theme_distribution": _split_distribution_for_metadata_column(connection, "theme_tags", limit),
            "has_remittance_distribution": [
                {"label": "true", "value": _safe_int(connection.execute("SELECT COUNT(*) FROM qiaopi_metadata_records WHERE has_remittance = 1").fetchone()[0])},
                {"label": "false", "value": _safe_int(connection.execute("SELECT COUNT(*) FROM qiaopi_metadata_records WHERE has_remittance = 0").fetchone()[0])},
            ],
        }


def search_metadata_records(
    query: str,
    top_k: int = 20,
    filters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    where_sql, filter_params = _metadata_filter_sql(filters)
    with get_connection() as connection:
        create_metadata_fts_index(connection)
        match_query = _metadata_match_query(query)
        if match_query:
            rows = connection.execute(
                f"""
                SELECT
                    m.metadata_id,
                    m.title_clean,
                    m.sender_raw,
                    m.recipient_raw,
                    m.date_text,
                    m.year_normalized,
                    m.origin_place,
                    m.destination_place,
                    m.country_or_region,
                    m.remittance_raw,
                    m.has_remittance,
                    m.has_linked_text,
                    m.linked_record_id,
                    bm25({METADATA_FTS_TABLE}) AS score,
                    snippet({METADATA_FTS_TABLE}, 1, '', '', '...', 18) AS snippet
                FROM {METADATA_FTS_TABLE}
                JOIN qiaopi_metadata_records AS m
                    ON m.metadata_id = {METADATA_FTS_TABLE}.metadata_id
                WHERE {METADATA_FTS_TABLE} MATCH ?
                {where_sql}
                ORDER BY score ASC, m.source_index ASC
                LIMIT ?
                """,
                [match_query, *filter_params, top_k],
            ).fetchall()
        else:
            rows = connection.execute(
                f"""
                SELECT
                    m.metadata_id,
                    m.title_clean,
                    m.sender_raw,
                    m.recipient_raw,
                    m.date_text,
                    m.year_normalized,
                    m.origin_place,
                    m.destination_place,
                    m.country_or_region,
                    m.remittance_raw,
                    m.has_remittance,
                    m.has_linked_text,
                    m.linked_record_id,
                    0.0 AS score,
                    m.title_clean AS snippet
                FROM qiaopi_metadata_records AS m
                WHERE 1 = 1
                {where_sql}
                ORDER BY m.source_index ASC
                LIMIT ?
                """,
                [*filter_params, top_k],
            ).fetchall()
    return _rows_to_dicts(rows)


def fetch_metadata_record(metadata_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM qiaopi_metadata_records WHERE metadata_id = ?",
            (metadata_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_linked_text_for_metadata(metadata_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                m.metadata_id,
                m.has_linked_text,
                m.linked_record_id,
                t.record_id,
                t.title_reference,
                t.sender,
                t.recipient,
                t.date_text,
                t.year_normalized,
                t.main_intent,
                t.theme_tags,
                t.has_remittance,
                t.place_mentions_normalized
            FROM qiaopi_metadata_records AS m
            LEFT JOIN qiaopi_text_records AS t
                ON t.record_id = m.linked_record_id
            WHERE m.metadata_id = ?
            """,
            (metadata_id,),
        ).fetchone()
    return dict(row) if row else None


def fetch_metadata_link_stats() -> dict[str, Any]:
    with get_connection() as connection:
        text_count = count_rows(connection, "qiaopi_text_records")
        auto_link_count = count_rows(connection, "qiaopi_text_metadata_links")
        method_rows = connection.execute(
            """
            SELECT link_method AS label, COUNT(*) AS value
            FROM qiaopi_text_metadata_links
            GROUP BY link_method
            ORDER BY value DESC, label ASC
            """
        ).fetchall()
        average_row = connection.execute(
            "SELECT AVG(link_confidence) FROM qiaopi_text_metadata_links"
        ).fetchone()
        return {
            "auto_link_count": auto_link_count,
            "candidate_link_count": count_rows(connection, "qiaopi_text_metadata_link_candidates"),
            "unlinked_full_text_count": max(text_count - auto_link_count, 0),
            "link_method_distribution": _chart_rows(method_rows),
            "average_link_confidence": float(average_row[0] or 0.0),
        }


def fetch_text_records_for_metadata_linking() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                record_id,
                title_reference,
                sender,
                recipient,
                sender_name_clean,
                recipient_name_clean,
                date_text,
                year_normalized,
                place_mentions_normalized,
                has_remittance,
                retrieval_keywords
            FROM qiaopi_text_records
            ORDER BY record_id
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def fetch_metadata_records_for_linking() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                metadata_id,
                source_index,
                title_clean,
                sender_raw,
                recipient_raw,
                sender_name_clean,
                recipient_name_clean,
                date_text,
                year_normalized,
                origin_place,
                destination_place,
                place_mentions,
                country_or_region,
                remittance_raw,
                has_remittance,
                kinship_terms
            FROM qiaopi_metadata_records
            ORDER BY source_index
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def reset_metadata_links(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM qiaopi_text_metadata_link_candidates")
    connection.execute("DELETE FROM qiaopi_text_metadata_links")
    connection.execute(
        """
        UPDATE qiaopi_metadata_records
        SET has_linked_text = 0,
            linked_record_id = ''
        """
    )


def insert_metadata_links(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "link_id": _text(row.get("link_id")),
                "record_id": _text(row.get("record_id")),
                "metadata_id": _text(row.get("metadata_id")),
                "link_method": _text(row.get("link_method")),
                "link_confidence": _number_or_none(row.get("link_confidence")) or 0.0,
                "title_similarity": _number_or_none(row.get("title_similarity")) or 0.0,
                "matched_fields_json": _text(row.get("matched_fields_json")),
            }
        )
    inserted_count = _insert_rows(
        connection,
        "qiaopi_text_metadata_links",
        METADATA_LINK_COLUMNS,
        prepared_rows,
    )
    for row in prepared_rows:
        connection.execute(
            """
            UPDATE qiaopi_metadata_records
            SET has_linked_text = 1,
                linked_record_id = ?
            WHERE metadata_id = ?
            """,
            (row["record_id"], row["metadata_id"]),
        )
    return inserted_count


def insert_metadata_link_candidates(
    connection: sqlite3.Connection,
    rows: Iterable[Mapping[str, Any]],
) -> int:
    prepared_rows = []
    for row in rows:
        prepared_rows.append(
            {
                "candidate_id": _text(row.get("candidate_id")),
                "record_id": _text(row.get("record_id")),
                "metadata_id": _text(row.get("metadata_id")),
                "candidate_method": _text(row.get("candidate_method")),
                "candidate_confidence": _number_or_none(row.get("candidate_confidence")) or 0.0,
                "title_similarity": _number_or_none(row.get("title_similarity")) or 0.0,
                "matched_fields_json": _text(row.get("matched_fields_json")),
                "reason": _text(row.get("reason")),
            }
        )
    return _insert_rows(
        connection,
        "qiaopi_text_metadata_link_candidates",
        METADATA_LINK_CANDIDATE_COLUMNS,
        prepared_rows,
    )
