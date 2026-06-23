from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.database.connection import get_connection, resolve_database_path
from app.database.repository import (
    count_rows,
    insert_amount_mentions,
    insert_entity_mentions,
    insert_evidence_spans,
    insert_place_mentions,
    insert_retrieval_units,
    insert_text_records,
)
from app.database.schema import reset_database
from app.ingestion.build_retrieval_units import build_retrieval_units
from app.search.fts_index import rebuild_fts_index, search_fts
from app.settings import (
    QIAOPI_AMOUNT_MENTIONS_CSV,
    QIAOPI_ENTITY_MENTIONS_CSV,
    QIAOPI_EVIDENCE_SPANS_CSV,
    QIAOPI_PLACE_MENTIONS_CSV,
    QIAOPI_WIDE_TABLE_CSV,
    QIAOPI_WIDE_TABLE_XLSX,
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required processed CSV is missing: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")


def read_wide_table(processed_dir: Path | None = None) -> pd.DataFrame:
    wide_table_csv = (
        processed_dir / QIAOPI_WIDE_TABLE_CSV.name
        if processed_dir is not None
        else QIAOPI_WIDE_TABLE_CSV
    )
    wide_table_xlsx = (
        processed_dir / QIAOPI_WIDE_TABLE_XLSX.name
        if processed_dir is not None
        else QIAOPI_WIDE_TABLE_XLSX
    )
    if wide_table_csv.exists():
        return _read_csv(wide_table_csv)
    if wide_table_xlsx.exists():
        return pd.read_excel(wide_table_xlsx, dtype=str).fillna("")
    raise FileNotFoundError(
        "Wide table source is missing. Expected either "
        f"{wide_table_csv} or {wide_table_xlsx}."
    )


def read_processed_inputs(processed_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    def source_path(default_path: Path) -> Path:
        return processed_dir / default_path.name if processed_dir is not None else default_path

    return {
        "wide_table": read_wide_table(processed_dir),
        "amount_mentions": _read_csv(source_path(QIAOPI_AMOUNT_MENTIONS_CSV)),
        "entity_mentions": _read_csv(source_path(QIAOPI_ENTITY_MENTIONS_CSV)),
        "place_mentions": _read_csv(source_path(QIAOPI_PLACE_MENTIONS_CSV)),
        "evidence_spans": _read_csv(source_path(QIAOPI_EVIDENCE_SPANS_CSV)),
    }


def _distribution(df: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in df.columns:
        return {}
    counts = df[column].fillna("").astype(str).value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def _print_distribution(title: str, distribution: dict[str, int]) -> None:
    print(f"{title}:")
    if not distribution:
        print("  <missing>")
        return
    for key, value in distribution.items():
        label = key if key else "<blank>"
        print(f"  {label}: {value}")


def _sample_units(connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT unit_id, record_id, unit_type, source_column, substr(unit_text, 1, 80) AS unit_text
        FROM qiaopi_retrieval_units
        ORDER BY record_id, unit_type, unit_id
        LIMIT 5
        """
    ).fetchall()
    return [dict(row) for row in rows]


def build_database(
    db_path: Path | None = None,
    *,
    processed_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_db_path = resolve_database_path(db_path)
    inputs = read_processed_inputs(processed_dir)
    wide_table = inputs["wide_table"]
    amount_mentions = inputs["amount_mentions"]
    entity_mentions = inputs["entity_mentions"]
    place_mentions = inputs["place_mentions"]
    evidence_spans = inputs["evidence_spans"]
    retrieval_units = build_retrieval_units(wide_table, evidence_spans)

    with get_connection(resolved_db_path) as connection:
        reset_database(connection)
        inserted_text_records = insert_text_records(
            connection,
            wide_table.to_dict("records"),
        )
        inserted_amount_mentions = insert_amount_mentions(
            connection,
            amount_mentions.to_dict("records"),
        )
        inserted_entity_mentions = insert_entity_mentions(
            connection,
            entity_mentions.to_dict("records"),
        )
        inserted_place_mentions = insert_place_mentions(
            connection,
            place_mentions.to_dict("records"),
        )
        inserted_evidence_spans = insert_evidence_spans(
            connection,
            evidence_spans.to_dict("records"),
        )
        inserted_retrieval_units = insert_retrieval_units(
            connection,
            retrieval_units,
        )
        fts_row_count = rebuild_fts_index(connection)
        fts_sample_results = search_fts(connection, "母亲 寄款 查收", top_k=5)

        stats: dict[str, Any] = {
            "database_path": str(resolved_db_path),
            "text_record_count": inserted_text_records,
            "amount_mention_count": inserted_amount_mentions,
            "entity_mention_count": inserted_entity_mentions,
            "place_mention_count": inserted_place_mentions,
            "evidence_span_count": inserted_evidence_spans,
            "retrieval_unit_count": inserted_retrieval_units,
            "fts_row_count": fts_row_count,
            "text_quality_distribution": _distribution(wide_table, "text_quality_level"),
            "main_intent_distribution": _distribution(wide_table, "main_intent"),
            "sample_retrieval_units": _sample_units(connection),
            "sample_fts_results": fts_sample_results,
            "table_counts": {
                "qiaopi_text_records": count_rows(connection, "qiaopi_text_records"),
                "qiaopi_amount_mentions": count_rows(connection, "qiaopi_amount_mentions"),
                "qiaopi_entity_mentions": count_rows(connection, "qiaopi_entity_mentions"),
                "qiaopi_place_mentions": count_rows(connection, "qiaopi_place_mentions"),
                "qiaopi_evidence_spans": count_rows(connection, "qiaopi_evidence_spans"),
                "qiaopi_retrieval_units": count_rows(connection, "qiaopi_retrieval_units"),
                "qiaopi_retrieval_units_fts": count_rows(connection, "qiaopi_retrieval_units_fts"),
            },
        }
    return stats


def build_database_from_excel() -> dict[str, Any]:
    return build_database()


def print_build_stats(stats: dict[str, Any]) -> None:
    print(f"Database path: {stats['database_path']}")
    print(f"text record count: {stats['text_record_count']}")
    print(f"amount mention count: {stats['amount_mention_count']}")
    print(f"entity mention count: {stats['entity_mention_count']}")
    print(f"place mention count: {stats['place_mention_count']}")
    print(f"evidence span count: {stats['evidence_span_count']}")
    print(f"retrieval unit count: {stats['retrieval_unit_count']}")
    print(f"FTS row count: {stats['fts_row_count']}")
    _print_distribution("text quality distribution", stats["text_quality_distribution"])
    _print_distribution("main intent distribution", stats["main_intent_distribution"])
    print("sample retrieval units:")
    for unit in stats["sample_retrieval_units"]:
        print(
            "  "
            f"{unit['unit_id']} | {unit['unit_type']} | {unit['source_column']} | "
            f"{unit['unit_text']}"
        )
    print("sample FTS results for: 母亲 寄款 查收")
    for result in stats["sample_fts_results"]:
        print(
            "  "
            f"{result['unit_id']} | {result['unit_type']} | "
            f"score={result['score']:.6f} | {result['unit_text'][:80]}"
        )


def main() -> None:
    stats = build_database()
    print_build_stats(stats)


if __name__ == "__main__":
    main()
