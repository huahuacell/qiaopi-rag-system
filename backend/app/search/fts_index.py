from __future__ import annotations

import re
import sqlite3
from typing import Iterable


FTS_TABLE = "qiaopi_retrieval_units_fts"


def _assert_fts5_available(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("CREATE VIRTUAL TABLE temp.__fts5_check USING fts5(value)")
        connection.execute("DROP TABLE temp.__fts5_check")
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "SQLite FTS5 is required for qiaopi retrieval search, but this sqlite3 "
            "build does not support FTS5. Use a Python/SQLite build with FTS5 enabled."
        ) from exc


def create_fts_index(connection: sqlite3.Connection) -> None:
    _assert_fts5_available(connection)
    connection.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE}
        USING fts5(
            unit_id UNINDEXED,
            record_id UNINDEXED,
            unit_type,
            title_reference,
            sender,
            recipient,
            unit_text,
            theme_tags,
            style_keywords,
            retrieval_keywords,
            fts_text,
            tokenize='unicode61'
        )
        """
    )


def rebuild_fts_index(connection: sqlite3.Connection) -> int:
    create_fts_index(connection)
    connection.execute(f"DELETE FROM {FTS_TABLE}")
    connection.execute(
        f"""
        INSERT INTO {FTS_TABLE} (
            unit_id,
            record_id,
            unit_type,
            title_reference,
            sender,
            recipient,
            unit_text,
            theme_tags,
            style_keywords,
            retrieval_keywords,
            fts_text
        )
        SELECT
            unit_id,
            record_id,
            unit_type,
            title_reference,
            sender,
            recipient,
            unit_text,
            theme_tags,
            style_keywords,
            retrieval_keywords,
            fts_text
        FROM qiaopi_retrieval_units
        ORDER BY unit_id
        """
    )
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {FTS_TABLE}").fetchone()
    return int(row["count"])


def _normalize_query(query: str) -> str:
    tokens = [
        token.strip()
        for token in re.split(r"[\s；;，,、。！？!?：:（）()【】\[\]《》<>“”\"'‘’/|\\]+", query)
        if token.strip()
    ]
    if not tokens:
        return ""
    escaped_tokens = [token.replace('"', '""') for token in tokens]
    return " OR ".join(f'"{token}"' for token in escaped_tokens)


def search_fts(
    connection: sqlite3.Connection,
    query: str,
    top_k: int = 10,
    unit_types: Iterable[str] | None = None,
) -> list[dict]:
    match_query = _normalize_query(query)
    if not match_query:
        return []

    unit_type_values = [unit_type for unit_type in (unit_types or []) if unit_type]
    params: list[object] = [match_query]
    unit_type_clause = ""
    if unit_type_values:
        placeholders = ", ".join("?" for _ in unit_type_values)
        unit_type_clause = f" AND {FTS_TABLE}.unit_type IN ({placeholders})"
        params.extend(unit_type_values)
    params.append(top_k)

    rows = connection.execute(
        f"""
        SELECT
            {FTS_TABLE}.unit_id,
            {FTS_TABLE}.record_id,
            {FTS_TABLE}.unit_type,
            {FTS_TABLE}.title_reference,
            {FTS_TABLE}.sender,
            {FTS_TABLE}.recipient,
            r.date_text,
            r.main_intent,
            {FTS_TABLE}.unit_text,
            bm25({FTS_TABLE}) AS bm25_score,
            bm25({FTS_TABLE}) AS score,
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
        FROM {FTS_TABLE}
        JOIN qiaopi_retrieval_units AS r
            ON r.unit_id = {FTS_TABLE}.unit_id
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
        WHERE {FTS_TABLE} MATCH ?
        {unit_type_clause}
        ORDER BY bm25_score ASC, {FTS_TABLE}.unit_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]
