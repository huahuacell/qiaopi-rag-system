from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.database.connection import get_connection
from app.database.repository import (
    count_rows,
    fetch_metadata_distributions,
    fetch_metadata_stats,
    insert_metadata_records,
    rebuild_metadata_fts_index,
    reset_metadata_catalog_tables,
)
from app.database.schema import create_tables
from app.metadata.metadata_parser import parse_metadata_excel, resolve_metadata_excel_path
from app.settings import QIAOPI_DB_PATH


def _print_distribution_sample(title: str, rows: list[dict[str, Any]], limit: int = 8) -> None:
    print(f"{title}:")
    if not rows:
        print("  <empty>")
        return
    for row in rows[:limit]:
        print(f"  {row['label']}: {row['value']}")


def build_metadata_database(
    *,
    source_path: Path | None = None,
    db_path: Path = QIAOPI_DB_PATH,
) -> dict[str, Any]:
    resolved_source_path = resolve_metadata_excel_path(source_path)
    metadata_rows = parse_metadata_excel(resolved_source_path)

    with get_connection(db_path) as connection:
        create_tables(connection)
        reset_metadata_catalog_tables(connection)
        metadata_record_count = insert_metadata_records(connection, metadata_rows)
        fts_row_count = rebuild_metadata_fts_index(connection)
        connection.commit()
        stats = fetch_metadata_stats(db_path)
        distributions = fetch_metadata_distributions(limit=8, db_path=db_path)
        table_count = count_rows(connection, "qiaopi_metadata_records")

    return {
        "database_path": str(db_path),
        "source_path": str(resolved_source_path),
        "metadata_record_count": metadata_record_count,
        "table_metadata_record_count": table_count,
        "fts_row_count": fts_row_count,
        "year_distribution_sample": distributions["year_distribution"],
        "top_countries_or_regions": distributions["country_or_region_distribution"],
        "has_remittance_count": stats["has_remittance_count"],
        "needs_review_count": stats["needs_review_count"],
    }


def print_build_stats(stats: dict[str, Any]) -> None:
    print(f"Database path: {stats['database_path']}")
    print(f"Metadata source path: {stats['source_path']}")
    print(f"metadata record count: {stats['metadata_record_count']}")
    print(f"FTS row count: {stats['fts_row_count']}")
    _print_distribution_sample("year distribution sample", stats["year_distribution_sample"])
    _print_distribution_sample("top countries/regions", stats["top_countries_or_regions"])
    print(f"has_remittance count: {stats['has_remittance_count']}")
    print(f"needs_review count: {stats['needs_review_count']}")


def main() -> None:
    stats = build_metadata_database()
    print_build_stats(stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
