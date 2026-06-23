from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.database.connection import get_connection, resolve_database_path
from app.database.repository import (
    count_rows,
    fetch_metadata_link_stats,
    fetch_metadata_records_for_linking,
    fetch_text_records_for_metadata_linking,
    insert_metadata_link_candidates,
    insert_metadata_links,
    reset_metadata_links,
)
from app.database.schema import create_tables
from app.metadata.metadata_linker import build_metadata_text_links
from app.settings import QIAOPI_DB_PATH


def link_metadata_text_records(db_path: Path | None = None) -> dict[str, Any]:
    resolved_db_path = resolve_database_path(db_path)
    text_records = fetch_text_records_for_metadata_linking(resolved_db_path)
    metadata_records = fetch_metadata_records_for_linking(resolved_db_path)
    link_result = build_metadata_text_links(text_records, metadata_records)

    with get_connection(resolved_db_path) as connection:
        create_tables(connection)
        reset_metadata_links(connection)
        auto_link_count = insert_metadata_links(connection, link_result["auto_links"])
        candidate_link_count = insert_metadata_link_candidates(connection, link_result["candidate_links"])
        connection.commit()
        link_stats = fetch_metadata_link_stats(resolved_db_path)
        full_text_record_count = count_rows(connection, "qiaopi_text_records")

    return {
        "database_path": str(resolved_db_path),
        "full_text_record_count": full_text_record_count,
        "auto_link_count": auto_link_count,
        "candidate_link_count": candidate_link_count,
        "unlinked_full_text_count": link_stats["unlinked_full_text_count"],
        "top_link_methods": link_stats["link_method_distribution"],
    }


def print_link_stats(stats: dict[str, Any]) -> None:
    print(f"Database path: {stats['database_path']}")
    print(f"full-text record count: {stats['full_text_record_count']}")
    print(f"auto-link count: {stats['auto_link_count']}")
    print(f"candidate-link count: {stats['candidate_link_count']}")
    print(f"unlinked full-text count: {stats['unlinked_full_text_count']}")
    print("top link methods:")
    if not stats["top_link_methods"]:
        print("  <empty>")
    for row in stats["top_link_methods"]:
        print(f"  {row['label']}: {row['value']}")


def main() -> None:
    stats = link_metadata_text_records()
    print_link_stats(stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
