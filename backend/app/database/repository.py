from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable, Mapping, Optional

from app.database.connection import get_connection


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
