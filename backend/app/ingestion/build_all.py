from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from app import settings
from app.database.connection import get_connection
from app.database.repository import count_rows
from app.ingestion.build_database import build_database
from app.ingestion.build_knowledge_graph import build_knowledge_graph
from app.ingestion.build_metadata_database import build_metadata_database
from app.ingestion.build_semantic_index import (
    DEFAULT_REGRESSION_QUERIES,
    build_semantic_index,
)
from app.ingestion.link_metadata_text_records import link_metadata_text_records
from app.ingestion.preprocess_qiaopi_wide_table import (
    DEFAULT_SHEET,
    build_auxiliary_tables,
    build_wide_table,
    write_auxiliary_outputs,
    write_outputs,
)


PIPELINE_VERSION = "1"
BUILD_MANIFEST_NAME = "qiaopi_build_manifest.json"
SEMANTIC_MANIFEST_NAME = "qiaopi_retrieval_units_manifest.json"
EXPECTED_TEXT_RECORD_COUNT = 213
EXPECTED_METADATA_RECORD_COUNT = 50_064

PROCESSED_ARTIFACT_NAMES: tuple[str, ...] = (
    settings.QIAOPI_WIDE_TABLE_CSV.name,
    settings.QIAOPI_WIDE_TABLE_XLSX.name,
    settings.QIAOPI_AMOUNT_MENTIONS_CSV.name,
    settings.QIAOPI_ENTITY_MENTIONS_CSV.name,
    settings.QIAOPI_PLACE_MENTIONS_CSV.name,
    settings.QIAOPI_EVIDENCE_SPANS_CSV.name,
)

RELATIONAL_TABLES: tuple[str, ...] = (
    "qiaopi_text_records",
    "qiaopi_metadata_records",
    "qiaopi_text_metadata_links",
    "qiaopi_text_metadata_link_candidates",
    "qiaopi_amount_mentions",
    "qiaopi_entity_mentions",
    "qiaopi_place_mentions",
    "qiaopi_evidence_spans",
    "qiaopi_retrieval_units",
    "qiaopi_kg_nodes",
    "qiaopi_kg_edges",
    "qiaopi_generation_cache",
    "qiaopi_generation_logs",
    "qiaopi_query_logs",
)

NON_DETERMINISTIC_COLUMNS = {"created_at"}


class BuildAllError(RuntimeError):
    """Raised when the isolated build or its acceptance checks fail."""


@dataclass(frozen=True)
class BuildPaths:
    root: Path
    processed_dir: Path
    index_dir: Path
    database_path: Path
    semantic_index_path: Path
    semantic_metadata_path: Path
    semantic_manifest_path: Path
    build_manifest_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _prepare_build_paths(staging_dir: Path | None) -> BuildPaths:
    live_processed = settings.PROCESSED_DATA_DIR.resolve()
    live_index = settings.INDEX_DIR.resolve()
    if staging_dir is None:
        builds_dir = settings.DATA_DIR / "builds"
        builds_dir.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="qiaopi-build-", dir=builds_dir))
    else:
        root = staging_dir.resolve()
        if (
            root in {live_processed, live_index}
            or _is_relative_to(root, live_processed)
            or _is_relative_to(root, live_index)
        ):
            raise BuildAllError(
                "Staging directory must be separate from live processed and index directories."
            )
        if root.exists() and any(root.iterdir()):
            raise BuildAllError(f"Staging directory is not empty: {root}")
        root.mkdir(parents=True, exist_ok=True)

    processed_dir = root / "processed"
    index_dir = root / "index"
    processed_dir.mkdir(parents=True, exist_ok=False)
    index_dir.mkdir(parents=True, exist_ok=False)
    return BuildPaths(
        root=root,
        processed_dir=processed_dir,
        index_dir=index_dir,
        database_path=processed_dir / settings.QIAOPI_DB_PATH.name,
        semantic_index_path=index_dir / settings.SEMANTIC_FAISS_INDEX_PATH.name,
        semantic_metadata_path=index_dir / settings.SEMANTIC_FAISS_METADATA_PATH.name,
        semantic_manifest_path=index_dir / SEMANTIC_MANIFEST_NAME,
        build_manifest_path=root / BUILD_MANIFEST_NAME,
    )


def preprocess_full_text(
    *,
    source_path: Path,
    sheet_name: str,
    output_dir: Path,
) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(f"Full-text source workbook is missing: {source_path}")
    source = pd.read_excel(source_path, sheet_name=sheet_name)
    wide_table = build_wide_table(source)
    auxiliary_tables = build_auxiliary_tables(wide_table)
    auxiliary_paths = write_auxiliary_outputs(auxiliary_tables, output_dir)
    csv_path, xlsx_path = write_outputs(
        wide_table,
        output_dir,
        "qiaopi_213_wide_table",
    )
    return {
        "source_path": str(source_path),
        "source_sha256": _sha256_file(source_path),
        "sheet_name": sheet_name,
        "text_record_count": len(wide_table),
        "amount_mention_count": len(auxiliary_tables["qiaopi_amount_mentions.csv"]),
        "entity_mention_count": len(auxiliary_tables["qiaopi_entity_mentions.csv"]),
        "place_mention_count": len(auxiliary_tables["qiaopi_place_mentions.csv"]),
        "evidence_span_count": len(auxiliary_tables["qiaopi_evidence_spans.csv"]),
        "csv_path": str(csv_path),
        "xlsx_path": str(xlsx_path),
        "auxiliary_paths": {
            name: str(path)
            for name, path in sorted(auxiliary_paths.items())
        },
    }


def _copy_processed_inputs(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    source_dir = source_dir.resolve()
    copied: dict[str, str] = {}
    for name in PROCESSED_ARTIFACT_NAMES:
        source = source_dir / name
        if not source.exists():
            raise FileNotFoundError(f"Processed build input is missing: {source}")
        target = output_dir / name
        shutil.copy2(source, target)
        copied[name] = str(target)
    frame = pd.read_csv(
        output_dir / settings.QIAOPI_WIDE_TABLE_CSV.name,
        dtype=str,
        keep_default_na=False,
    )
    return {
        "mode": "reused_processed_inputs",
        "source_dir": str(source_dir),
        "text_record_count": len(frame),
        "copied_paths": copied,
    }


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_signature(
    connection: sqlite3.Connection,
    table_name: str,
) -> dict[str, Any]:
    if not _table_exists(connection, table_name):
        raise BuildAllError(f"Required relational table is missing: {table_name}")
    table_info = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    columns = [
        str(row["name"])
        for row in table_info
        if str(row["name"]) not in NON_DETERMINISTIC_COLUMNS
    ]
    primary_key_columns = [
        str(row["name"])
        for row in sorted(table_info, key=lambda item: int(item["pk"]))
        if int(row["pk"]) > 0 and str(row["name"]) in columns
    ]
    order_columns = primary_key_columns or columns
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    quoted_order = ", ".join(f'"{column}"' for column in order_columns)
    cursor = connection.execute(
        f'SELECT {quoted_columns} FROM "{table_name}" ORDER BY {quoted_order}'
    )
    digest = hashlib.sha256()
    digest.update(
        json.dumps(columns, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    digest.update(b"\n")
    row_count = 0
    for row in cursor:
        values = [row[column] for column in columns]
        digest.update(
            json.dumps(
                values,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        )
        digest.update(b"\n")
        row_count += 1
    return {
        "row_count": row_count,
        "sha256": digest.hexdigest(),
        "columns": columns,
        "excluded_columns": sorted(NON_DETERMINISTIC_COLUMNS.intersection(
            {str(row["name"]) for row in table_info}
        )),
    }


def relational_signature(db_path: Path) -> dict[str, Any]:
    with get_connection(db_path) as connection:
        table_signatures = {
            table_name: _table_signature(connection, table_name)
            for table_name in RELATIONAL_TABLES
        }
        schema_rows = connection.execute(
            """
            SELECT type, name, tbl_name, COALESCE(sql, '') AS sql
            FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY type, name
            """
        ).fetchall()
        schema_digest = hashlib.sha256()
        for row in schema_rows:
            schema_digest.update(
                json.dumps(
                    list(row),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            schema_digest.update(b"\n")

    combined_digest = hashlib.sha256()
    for table_name, signature in table_signatures.items():
        combined_digest.update(
            f"{table_name}:{signature['row_count']}:{signature['sha256']}\n".encode(
                "utf-8"
            )
        )
    return {
        "tables": table_signatures,
        "combined_sha256": combined_digest.hexdigest(),
        "schema_sha256": schema_digest.hexdigest(),
    }


def _validate_database(
    *,
    db_path: Path,
    preprocess_stats: Mapping[str, Any],
    database_stats: Mapping[str, Any],
    metadata_stats: Mapping[str, Any],
    link_stats: Mapping[str, Any],
    graph_stats: Mapping[str, Any],
) -> dict[str, Any]:
    with get_connection(db_path) as connection:
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        foreign_key_errors = [
            dict(row)
            for row in connection.execute("PRAGMA foreign_key_check").fetchall()
        ]
        counts = {
            table_name: count_rows(connection, table_name)
            for table_name in RELATIONAL_TABLES
        }
        counts["qiaopi_retrieval_units_fts"] = count_rows(
            connection, "qiaopi_retrieval_units_fts"
        )
        counts["qiaopi_metadata_fts"] = count_rows(
            connection, "qiaopi_metadata_fts"
        )

    expected = {
        "qiaopi_text_records": int(preprocess_stats["text_record_count"]),
        "qiaopi_amount_mentions": int(database_stats["amount_mention_count"]),
        "qiaopi_entity_mentions": int(database_stats["entity_mention_count"]),
        "qiaopi_place_mentions": int(database_stats["place_mention_count"]),
        "qiaopi_evidence_spans": int(database_stats["evidence_span_count"]),
        "qiaopi_retrieval_units": int(database_stats["retrieval_unit_count"]),
        "qiaopi_retrieval_units_fts": int(database_stats["fts_row_count"]),
        "qiaopi_metadata_records": int(metadata_stats["metadata_record_count"]),
        "qiaopi_metadata_fts": int(metadata_stats["fts_row_count"]),
        "qiaopi_text_metadata_links": int(link_stats["auto_link_count"]),
        "qiaopi_text_metadata_link_candidates": int(
            link_stats["candidate_link_count"]
        ),
        "qiaopi_kg_nodes": int(graph_stats["node_count"]),
        "qiaopi_kg_edges": int(graph_stats["edge_count"]),
        "qiaopi_generation_cache": 0,
        "qiaopi_generation_logs": 0,
        "qiaopi_query_logs": 0,
    }
    mismatches = {
        name: {"expected": expected_count, "actual": counts.get(name)}
        for name, expected_count in expected.items()
        if counts.get(name) != expected_count
    }
    if quick_check != "ok":
        raise BuildAllError(f"SQLite quick_check failed: {quick_check}")
    if foreign_key_errors:
        raise BuildAllError(
            f"SQLite foreign_key_check found {len(foreign_key_errors)} error(s)."
        )
    if mismatches:
        raise BuildAllError(
            "Relational count acceptance failed: "
            + json.dumps(mismatches, ensure_ascii=False, sort_keys=True)
        )
    if counts["qiaopi_text_records"] != EXPECTED_TEXT_RECORD_COUNT:
        raise BuildAllError(
            "Full-text corpus scale changed: "
            f"expected {EXPECTED_TEXT_RECORD_COUNT}, "
            f"got {counts['qiaopi_text_records']}."
        )
    if counts["qiaopi_metadata_records"] != EXPECTED_METADATA_RECORD_COUNT:
        raise BuildAllError(
            "Metadata corpus scale changed: "
            f"expected {EXPECTED_METADATA_RECORD_COUNT}, "
            f"got {counts['qiaopi_metadata_records']}."
        )
    if counts["qiaopi_retrieval_units"] <= counts["qiaopi_text_records"]:
        raise BuildAllError("Retrieval-unit build did not expand the full-text corpus.")
    if counts["qiaopi_kg_nodes"] <= 0 or counts["qiaopi_kg_edges"] <= 0:
        raise BuildAllError("Knowledge-graph build returned no nodes or edges.")
    return {
        "quick_check": quick_check,
        "foreign_key_error_count": 0,
        "counts": counts,
        "expected_counts": expected,
    }


def _validate_vector(
    *,
    semantic_stats: Mapping[str, Any],
    retrieval_unit_count: int,
) -> dict[str, Any]:
    failures: list[str] = []
    if int(semantic_stats["retrieval_unit_count"]) != retrieval_unit_count:
        failures.append("vector count does not match retrieval unit count")
    if int(semantic_stats["embedding_dimension"]) <= 0:
        failures.append("embedding dimension is not positive")
    if not str(semantic_stats["embedding_model"]).strip():
        failures.append("embedding model identifier is empty")
    if len(str(semantic_stats["corpus_fingerprint"])) != 64:
        failures.append("corpus fingerprint is invalid")
    regressions = list(semantic_stats.get("retrieval_regression") or [])
    if not regressions:
        failures.append("retrieval regression queries are missing")
    for regression in regressions:
        if not regression.get("hits"):
            failures.append(
                f"retrieval regression returned no hits: {regression.get('query', '')}"
            )
        if any(not hit.get("unit_id") for hit in regression.get("hits", [])):
            failures.append(
                f"retrieval regression contains an empty unit_id: {regression.get('query', '')}"
            )
    if failures:
        raise BuildAllError("Vector acceptance failed: " + "; ".join(failures))
    return {
        "vector_count": int(semantic_stats["retrieval_unit_count"]),
        "embedding_provider": semantic_stats["embedding_provider"],
        "embedding_model": semantic_stats["embedding_model"],
        "embedding_dimension": int(semantic_stats["embedding_dimension"]),
        "corpus_fingerprint": semantic_stats["corpus_fingerprint"],
        "retrieval_regression": regressions,
        "byte_checksum_enforced": False,
    }


def _regression_unit_ids(vector_section: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        str(item["query"]): [
            str(hit["unit_id"])
            for hit in item.get("hits", [])
        ]
        for item in vector_section.get("retrieval_regression", [])
    }


def compare_acceptance_manifests(
    current: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    current_relational = current["relational"]
    baseline_relational = baseline["relational"]
    current_vector = current["vector"]
    baseline_vector = baseline["vector"]
    differences: dict[str, Any] = {}
    current_inputs = current.get("inputs", {})
    baseline_inputs = baseline.get("inputs", {})
    for input_name in ("text_source", "metadata_source"):
        current_sha = current_inputs.get(input_name, {}).get("sha256")
        baseline_sha = baseline_inputs.get(input_name, {}).get("sha256")
        if current_sha != baseline_sha:
            differences[f"inputs.{input_name}.sha256"] = {
                "baseline": baseline_sha,
                "current": current_sha,
            }
    current_tables = current_relational.get("tables", {})
    baseline_tables = baseline_relational.get("tables", {})
    for table_name in sorted(set(current_tables) | set(baseline_tables)):
        current_table = current_tables.get(table_name, {})
        baseline_table = baseline_tables.get(table_name, {})
        for key in ("row_count", "sha256"):
            if current_table.get(key) != baseline_table.get(key):
                differences[f"relational.tables.{table_name}.{key}"] = {
                    "baseline": baseline_table.get(key),
                    "current": current_table.get(key),
                }
    for key in ("combined_sha256", "schema_sha256"):
        if current_relational.get(key) != baseline_relational.get(key):
            differences[f"relational.{key}"] = {
                "baseline": baseline_relational.get(key),
                "current": current_relational.get(key),
            }
    for key in (
        "embedding_provider",
        "embedding_model",
        "embedding_dimension",
        "corpus_fingerprint",
        "vector_count",
    ):
        if current_vector.get(key) != baseline_vector.get(key):
            differences[f"vector.{key}"] = {
                "baseline": baseline_vector.get(key),
                "current": current_vector.get(key),
            }
    current_regression = _regression_unit_ids(current_vector)
    baseline_regression = _regression_unit_ids(baseline_vector)
    if current_regression != baseline_regression:
        differences["vector.retrieval_regression_unit_ids"] = {
            "baseline": baseline_regression,
            "current": current_regression,
        }
    return {
        "matches": not differences,
        "differences": differences,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _promotion_artifacts(paths: BuildPaths) -> list[tuple[Path, Path]]:
    artifacts = [
        (
            paths.processed_dir / artifact_name,
            settings.PROCESSED_DATA_DIR / artifact_name,
        )
        for artifact_name in PROCESSED_ARTIFACT_NAMES
    ]
    artifacts.extend(
        [
            (paths.database_path, settings.QIAOPI_DB_PATH),
            (paths.semantic_index_path, settings.SEMANTIC_FAISS_INDEX_PATH),
            (paths.semantic_metadata_path, settings.SEMANTIC_FAISS_METADATA_PATH),
            (
                paths.semantic_manifest_path,
                settings.SEMANTIC_FAISS_MANIFEST_PATH,
            ),
            (
                paths.build_manifest_path,
                settings.PROCESSED_DATA_DIR / BUILD_MANIFEST_NAME,
            ),
        ]
    )
    missing = [str(source) for source, _target in artifacts if not source.exists()]
    if missing:
        raise BuildAllError(
            "Cannot promote because staged artifacts are missing: "
            + ", ".join(missing)
        )
    return artifacts


def promote_artifacts(artifacts: Iterable[tuple[Path, Path]]) -> list[str]:
    promotion_id = uuid.uuid4().hex
    prepared: list[tuple[Path, Path]] = []
    backups: dict[Path, Path] = {}
    promoted_targets: list[Path] = []
    try:
        for source, target in artifacts:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.{promotion_id}.new")
            shutil.copy2(source, temporary)
            prepared.append((temporary, target))

        for temporary, target in prepared:
            if target.exists():
                backup = target.with_name(f".{target.name}.{promotion_id}.bak")
                os.replace(target, backup)
                backups[target] = backup
            os.replace(temporary, target)
            promoted_targets.append(target)
    except Exception:
        for target in reversed(promoted_targets):
            if target.exists():
                target.unlink()
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)
        raise
    finally:
        for temporary, _target in prepared:
            if temporary.exists():
                temporary.unlink()

    for backup in backups.values():
        if backup.exists():
            backup.unlink()
    return [str(target) for _source, target in artifacts]


def build_all(
    *,
    staging_dir: Path | None = None,
    text_source: Path = settings.TEXT_XLSX_PATH,
    metadata_source: Path = settings.METADATA_XLSX_PATH,
    text_sheet: str = DEFAULT_SHEET,
    embedding_provider: str = "hash",
    baseline_manifest_path: Path | None = None,
    promote: bool = False,
    reuse_processed_dir: Path | None = None,
) -> dict[str, Any]:
    if embedding_provider not in {"hash", "local"}:
        raise BuildAllError(
            "build-all supports only local or hash embeddings; it never calls a remote embedding API."
        )
    if not metadata_source.exists():
        raise FileNotFoundError(f"Metadata source workbook is missing: {metadata_source}")

    paths = _prepare_build_paths(staging_dir)
    preprocess_stats = (
        _copy_processed_inputs(reuse_processed_dir, paths.processed_dir)
        if reuse_processed_dir is not None
        else preprocess_full_text(
            source_path=text_source,
            sheet_name=text_sheet,
            output_dir=paths.processed_dir,
        )
    )
    database_stats = build_database(
        paths.database_path,
        processed_dir=paths.processed_dir,
    )
    metadata_stats = build_metadata_database(
        source_path=metadata_source,
        db_path=paths.database_path,
    )
    link_stats = link_metadata_text_records(paths.database_path)
    graph_stats = build_knowledge_graph(paths.database_path)
    semantic_stats = build_semantic_index(
        provider_name=embedding_provider,
        db_path=paths.database_path,
        index_path=paths.semantic_index_path,
        metadata_path=paths.semantic_metadata_path,
        manifest_path=paths.semantic_manifest_path,
        regression_queries=DEFAULT_REGRESSION_QUERIES,
    )

    database_acceptance = _validate_database(
        db_path=paths.database_path,
        preprocess_stats=preprocess_stats,
        database_stats=database_stats,
        metadata_stats=metadata_stats,
        link_stats=link_stats,
        graph_stats=graph_stats,
    )
    relational = relational_signature(paths.database_path)
    vector = _validate_vector(
        semantic_stats=semantic_stats,
        retrieval_unit_count=database_acceptance["counts"]["qiaopi_retrieval_units"],
    )
    manifest: dict[str, Any] = {
        "manifest_version": PIPELINE_VERSION,
        "pipeline": "qiaopi-build-all",
        "created_at": _utc_now(),
        "status": "accepted",
        "inputs": {
            "text_source": {
                "filename": text_source.name,
                "sha256": (
                    _sha256_file(text_source)
                    if reuse_processed_dir is None
                    else None
                ),
                "sheet": text_sheet,
            },
            "metadata_source": {
                "filename": metadata_source.name,
                "sha256": _sha256_file(metadata_source),
            },
            "processed_input_mode": (
                "reused"
                if reuse_processed_dir is not None
                else "rebuilt_from_raw_excel"
            ),
        },
        "stages": {
            "preprocess": dict(preprocess_stats),
            "text_database": dict(database_stats),
            "metadata_database": dict(metadata_stats),
            "metadata_linking": dict(link_stats),
            "knowledge_graph": dict(graph_stats),
            "semantic_index": dict(semantic_stats),
        },
        "database_acceptance": database_acceptance,
        "relational": relational,
        "vector": vector,
        "artifacts": {
            "database": f"processed/{paths.database_path.name}",
            "semantic_index": f"index/{paths.semantic_index_path.name}",
            "semantic_metadata": f"index/{paths.semantic_metadata_path.name}",
            "semantic_manifest": f"index/{paths.semantic_manifest_path.name}",
            "vector_byte_checksum_enforced": False,
        },
    }

    if baseline_manifest_path is not None:
        baseline = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
        comparison = compare_acceptance_manifests(manifest, baseline)
        manifest["baseline_comparison"] = comparison
        if not comparison["matches"]:
            _write_json(paths.build_manifest_path, manifest)
            raise BuildAllError(
                "Build differs from the requested acceptance baseline: "
                + json.dumps(
                    comparison["differences"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

    _write_json(paths.build_manifest_path, manifest)
    promoted_paths: list[str] = []
    if promote:
        promoted_paths = promote_artifacts(_promotion_artifacts(paths))

    return {
        "status": "accepted",
        "staging_dir": str(paths.root),
        "manifest_path": str(paths.build_manifest_path),
        "promoted": promote,
        "promoted_paths": promoted_paths,
        "relational_combined_sha256": relational["combined_sha256"],
        "vector_corpus_fingerprint": vector["corpus_fingerprint"],
        "counts": database_acceptance["counts"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build every derived Qiaopi data asset in an isolated staging directory, "
            "validate it, and optionally promote it to the live paths."
        )
    )
    parser.add_argument("--staging-dir", type=Path)
    parser.add_argument("--text-source", type=Path, default=settings.TEXT_XLSX_PATH)
    parser.add_argument(
        "--metadata-source",
        type=Path,
        default=settings.METADATA_XLSX_PATH,
    )
    parser.add_argument("--text-sheet", default=DEFAULT_SHEET)
    parser.add_argument(
        "--embedding-provider",
        choices=["hash", "local"],
        default="hash",
        help=(
            "hash is deterministic and dependency-free; local uses the configured "
            "sentence-transformers model. Remote embeddings are intentionally disabled."
        ),
    )
    parser.add_argument(
        "--baseline-manifest",
        type=Path,
        help=(
            "Require relational checksums, vector identity, corpus fingerprint, and "
            "retrieval regression IDs to match a previous accepted manifest."
        ),
    )
    parser.add_argument(
        "--reuse-processed",
        type=Path,
        help=(
            "Copy an existing processed-input directory into staging instead of "
            "preprocessing the raw full-text workbook. Intended for diagnostics/tests."
        ),
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help=(
            "After all acceptance checks pass, replace live processed/index assets "
            "using rollback-capable file promotion."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_all(
        staging_dir=args.staging_dir,
        text_source=args.text_source,
        metadata_source=args.metadata_source,
        text_sheet=args.text_sheet,
        embedding_provider=args.embedding_provider,
        baseline_manifest_path=args.baseline_manifest,
        promote=args.promote,
        reuse_processed_dir=args.reuse_processed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
