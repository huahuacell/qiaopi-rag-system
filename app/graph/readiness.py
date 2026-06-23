from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from app import settings
from app.database.connection import get_readonly_connection, resolve_database_path
from app.search.semantic_retriever import load_semantic_index


LOGGER = logging.getLogger(__name__)
BUILD_COMMAND = (
    "python -m app.ingestion.build_all "
    "--embedding-provider hash --promote"
)
BUILD_MANIFEST_NAME = "qiaopi_build_manifest.json"
REQUIRED_TABLES = {
    "qiaopi_text_records",
    "qiaopi_metadata_records",
    "qiaopi_text_metadata_links",
    "qiaopi_text_metadata_link_candidates",
    "qiaopi_amount_mentions",
    "qiaopi_entity_mentions",
    "qiaopi_place_mentions",
    "qiaopi_evidence_spans",
    "qiaopi_retrieval_units",
    "qiaopi_retrieval_units_fts",
    "qiaopi_metadata_fts",
    "qiaopi_kg_nodes",
    "qiaopi_kg_edges",
}


class DataBuildNotReadyError(RuntimeError):
    """Raised when promoted runtime data is absent or failed acceptance."""


def inspect_data_build(
    db_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
    *,
    validate_semantic: bool = True,
) -> dict[str, Any]:
    resolved_db_path = resolve_database_path(db_path).resolve()
    resolved_manifest_path = (
        Path(manifest_path).resolve()
        if manifest_path is not None
        else resolved_db_path.with_name(BUILD_MANIFEST_NAME)
    )

    if not resolved_db_path.is_file():
        return _readiness_result(
            False,
            "database_missing",
            database_path=str(resolved_db_path),
            manifest_path=str(resolved_manifest_path),
        )
    if not resolved_manifest_path.is_file():
        return _readiness_result(
            False,
            "build_manifest_missing",
            database_path=str(resolved_db_path),
            manifest_path=str(resolved_manifest_path),
        )

    try:
        manifest = json.loads(resolved_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return _readiness_result(
            False,
            "build_manifest_invalid",
            database_path=str(resolved_db_path),
            manifest_path=str(resolved_manifest_path),
            error=str(error),
        )
    if manifest.get("status") != "accepted":
        return _readiness_result(
            False,
            "build_not_accepted",
            database_path=str(resolved_db_path),
            manifest_path=str(resolved_manifest_path),
            manifest_status=str(manifest.get("status") or ""),
        )

    try:
        with get_readonly_connection(resolved_db_path) as connection:
            tables = {
                str(row["name"])
                for row in connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }
            missing_tables = sorted(REQUIRED_TABLES - tables)
            if missing_tables:
                return _readiness_result(
                    False,
                    "required_tables_missing",
                    database_path=str(resolved_db_path),
                    manifest_path=str(resolved_manifest_path),
                    missing_tables=missing_tables,
                )

            counts = {
                table_name: _count(connection, table_name)
                for table_name in REQUIRED_TABLES
            }
            manifest_counts = (
                manifest.get("database_acceptance", {}).get("counts", {})
            )
            count_mismatches = {
                table_name: {
                    "manifest": int(manifest_count),
                    "database": counts.get(table_name),
                }
                for table_name, manifest_count in manifest_counts.items()
                if table_name in counts
                and counts.get(table_name) != int(manifest_count)
            }
            if count_mismatches:
                return _readiness_result(
                    False,
                    "manifest_database_count_mismatch",
                    database_path=str(resolved_db_path),
                    manifest_path=str(resolved_manifest_path),
                    count_mismatches=count_mismatches,
                )

            source_record_count = counts["qiaopi_text_records"]
            metadata_record_count = counts["qiaopi_metadata_records"]
            graph_record_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM qiaopi_kg_nodes
                    WHERE node_type = 'record'
                    """
                ).fetchone()[0]
            )
            missing_graph_record_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM qiaopi_text_records AS records
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM qiaopi_kg_nodes AS nodes
                        WHERE nodes.node_id = 'record:' || records.record_id
                          AND nodes.node_type = 'record'
                    )
                    """
                ).fetchone()[0]
            )
            if source_record_count <= 0 or metadata_record_count <= 0:
                return _readiness_result(
                    False,
                    "required_corpus_empty",
                    database_path=str(resolved_db_path),
                    manifest_path=str(resolved_manifest_path),
                    source_record_count=source_record_count,
                    metadata_record_count=metadata_record_count,
                )
            if (
                graph_record_count != source_record_count
                or missing_graph_record_count > 0
                or counts["qiaopi_kg_edges"] <= 0
            ):
                return _readiness_result(
                    False,
                    "knowledge_graph_incomplete",
                    database_path=str(resolved_db_path),
                    manifest_path=str(resolved_manifest_path),
                    source_record_count=source_record_count,
                    graph_record_count=graph_record_count,
                    graph_edge_count=counts["qiaopi_kg_edges"],
                    missing_graph_record_count=missing_graph_record_count,
                )

            quick_check = str(
                connection.execute("PRAGMA quick_check").fetchone()[0]
            )
            if quick_check != "ok":
                return _readiness_result(
                    False,
                    "sqlite_quick_check_failed",
                    database_path=str(resolved_db_path),
                    manifest_path=str(resolved_manifest_path),
                    quick_check=quick_check,
                )

            semantic_vector_count = 0
            if validate_semantic:
                semantic_paths = (
                    settings.SEMANTIC_FAISS_INDEX_PATH,
                    settings.SEMANTIC_FAISS_METADATA_PATH,
                    settings.SEMANTIC_FAISS_MANIFEST_PATH,
                )
                missing_semantic_paths = [
                    str(path)
                    for path in semantic_paths
                    if not path.is_file()
                ]
                if missing_semantic_paths:
                    return _readiness_result(
                        False,
                        "semantic_artifacts_missing",
                        database_path=str(resolved_db_path),
                        manifest_path=str(resolved_manifest_path),
                        missing_semantic_paths=missing_semantic_paths,
                    )
                semantic_bundle = load_semantic_index(
                    settings.SEMANTIC_FAISS_INDEX_PATH,
                    settings.SEMANTIC_FAISS_METADATA_PATH,
                    settings.SEMANTIC_FAISS_MANIFEST_PATH,
                    validate_runtime=False,
                )
                semantic_vector_count = len(semantic_bundle.metadata)
                if semantic_vector_count != counts["qiaopi_retrieval_units"]:
                    return _readiness_result(
                        False,
                        "semantic_database_count_mismatch",
                        database_path=str(resolved_db_path),
                        manifest_path=str(resolved_manifest_path),
                        retrieval_unit_count=counts["qiaopi_retrieval_units"],
                        semantic_vector_count=semantic_vector_count,
                    )

            return _readiness_result(
                True,
                "ready",
                database_path=str(resolved_db_path),
                manifest_path=str(resolved_manifest_path),
                source_record_count=source_record_count,
                metadata_record_count=metadata_record_count,
                graph_record_count=graph_record_count,
                graph_edge_count=counts["qiaopi_kg_edges"],
                retrieval_unit_count=counts["qiaopi_retrieval_units"],
                semantic_vector_count=semantic_vector_count,
                evidence_count=counts["qiaopi_evidence_spans"],
            )
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        sqlite3.Error,
        TypeError,
        ValueError,
    ) as error:
        return _readiness_result(
            False,
            "database_error",
            database_path=str(resolved_db_path),
            manifest_path=str(resolved_manifest_path),
            error=str(error),
        )


def require_data_build(
    db_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
    *,
    validate_semantic: bool = True,
) -> dict[str, Any]:
    status = inspect_data_build(
        db_path,
        manifest_path,
        validate_semantic=validate_semantic,
    )
    if status["ready"]:
        return status
    detail = json.dumps(status, ensure_ascii=False, sort_keys=True)
    raise DataBuildNotReadyError(
        "Qiaopi runtime data is not ready. From the backend directory run "
        f"`{BUILD_COMMAND}` before starting Uvicorn. Validation details: {detail}"
    )


def _count(connection: sqlite3.Connection, table_name: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _readiness_result(
    ready: bool,
    reason: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "ready": ready,
        "reason": reason,
        **details,
    }
