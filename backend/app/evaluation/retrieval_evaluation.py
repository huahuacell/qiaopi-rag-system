from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from app import settings
from app.database.connection import get_connection
from app.database.repository import search_metadata_records
from app.ingestion.build_semantic_index import build_semantic_index
from app.search.corpus_domains import (
    FULL_TEXT_EVIDENCE_DOMAIN,
    METADATA_CATALOG_DOMAIN,
)
from app.search.hybrid_retriever import retrieve_hybrid
from app.search.keyword_retriever import retrieve_keyword
from app.search.metadata_semantic_retriever import (
    metadata_semantic_status,
    search_metadata_hybrid,
    search_metadata_semantic,
)
from app.search.semantic_retriever import semantic_search, semantic_status


DEFAULT_BENCHMARK_PATH = (
    settings.DATA_DIR / "evaluation" / "retrieval_benchmark.jsonl"
)
DEFAULT_REPORT_PATH = settings.OUTPUT_DIR / "retrieval_evaluation.json"
DEFAULT_CUTOFFS: tuple[int, ...] = (1, 3, 5, 10)
FULL_TEXT_METHODS: tuple[str, ...] = ("keyword", "semantic", "hybrid")
METADATA_METHODS: tuple[str, ...] = ("keyword", "semantic", "hybrid")
EXPECTED_METADATA_RECORD_COUNT = 50064
EXPECTED_TEXT_RECORD_COUNT = 213
EXPECTED_RETRIEVAL_UNIT_COUNT = 1959


class RetrievalBenchmarkError(RuntimeError):
    """Raised when benchmark data or corpus boundaries are invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_benchmark(path: Path = DEFAULT_BENCHMARK_PATH) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen_query_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            clean_line = line.strip()
            if not clean_line:
                continue
            try:
                case = json.loads(clean_line)
            except json.JSONDecodeError as exc:
                raise RetrievalBenchmarkError(
                    f"Invalid JSON on benchmark line {line_number}."
                ) from exc
            query_id = str(case.get("query_id") or "")
            domain = str(case.get("domain") or "")
            query = str(case.get("query") or "").strip()
            if not query_id or query_id in seen_query_ids:
                raise RetrievalBenchmarkError(
                    f"Missing or duplicate query_id on line {line_number}: {query_id}"
                )
            if domain not in {METADATA_CATALOG_DOMAIN, FULL_TEXT_EVIDENCE_DOMAIN}:
                raise RetrievalBenchmarkError(
                    f"Unsupported domain on line {line_number}: {domain}"
                )
            if not query:
                raise RetrievalBenchmarkError(
                    f"Benchmark query is empty on line {line_number}."
                )
            relevance = case.get("relevance")
            if not isinstance(relevance, dict):
                raise RetrievalBenchmarkError(
                    f"Benchmark relevance is missing on line {line_number}."
                )
            if domain == METADATA_CATALOG_DOMAIN:
                judgments = relevance.get("metadata_records")
                if not isinstance(judgments, dict) or not judgments:
                    raise RetrievalBenchmarkError(
                        f"Metadata judgments are missing on line {line_number}."
                    )
                if any(not str(item_id).startswith("CSQP-META-") for item_id in judgments):
                    raise RetrievalBenchmarkError(
                        f"Non-metadata ID found in metadata domain on line {line_number}."
                    )
            else:
                units = relevance.get("units")
                records = relevance.get("records")
                if not isinstance(units, dict) or not units:
                    raise RetrievalBenchmarkError(
                        f"Unit judgments are missing on line {line_number}."
                    )
                if not isinstance(records, dict) or not records:
                    raise RetrievalBenchmarkError(
                        f"Record judgments are missing on line {line_number}."
                    )
                if any(str(item_id).startswith("CSQP-META-") for item_id in units):
                    raise RetrievalBenchmarkError(
                        f"Metadata ID found in full-text domain on line {line_number}."
                    )
            seen_query_ids.add(query_id)
            cases.append(case)
    if not cases:
        raise RetrievalBenchmarkError(f"Benchmark is empty: {path}")
    return cases


def validate_benchmark_against_database(
    cases: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    metadata_ids: set[str] = set()
    record_ids: set[str] = set()
    unit_ids: set[str] = set()
    for case in cases:
        relevance = case["relevance"]
        if case["domain"] == METADATA_CATALOG_DOMAIN:
            metadata_ids.update(relevance["metadata_records"])
        else:
            record_ids.update(relevance["records"])
            unit_ids.update(relevance["units"])

    with get_connection() as connection:
        existing_metadata = _existing_ids(
            connection,
            table_name="qiaopi_metadata_records",
            id_column="metadata_id",
            ids=metadata_ids,
        )
        existing_records = _existing_ids(
            connection,
            table_name="qiaopi_text_records",
            id_column="record_id",
            ids=record_ids,
        )
        existing_units = _existing_ids(
            connection,
            table_name="qiaopi_retrieval_units",
            id_column="unit_id",
            ids=unit_ids,
        )

    missing = {
        "metadata_ids": sorted(metadata_ids - existing_metadata),
        "record_ids": sorted(record_ids - existing_records),
        "unit_ids": sorted(unit_ids - existing_units),
    }
    if any(missing.values()):
        raise RetrievalBenchmarkError(
            "Benchmark references missing corpus IDs: "
            + json.dumps(missing, ensure_ascii=False, sort_keys=True)
        )
    return {
        "metadata_judgment_count": len(metadata_ids),
        "record_judgment_count": len(record_ids),
        "unit_judgment_count": len(unit_ids),
    }


def _existing_ids(
    connection,
    *,
    table_name: str,
    id_column: str,
    ids: set[str],
) -> set[str]:
    if not ids:
        return set()
    placeholders = ", ".join("?" for _ in ids)
    rows = connection.execute(
        f"SELECT {id_column} FROM {table_name} WHERE {id_column} IN ({placeholders})",
        sorted(ids),
    ).fetchall()
    return {str(row[id_column]) for row in rows}


def validate_corpus_boundaries() -> dict[str, Any]:
    with get_connection() as connection:
        metadata_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM qiaopi_metadata_records"
            ).fetchone()[0]
        )
        text_record_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM qiaopi_text_records"
            ).fetchone()[0]
        )
        retrieval_unit_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM qiaopi_retrieval_units"
            ).fetchone()[0]
        )
        metadata_units = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM qiaopi_retrieval_units
                WHERE record_id LIKE 'CSQP-META-%'
                """
            ).fetchone()[0]
        )
        unlinked_metadata_in_rag = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM qiaopi_retrieval_units AS r
                JOIN qiaopi_metadata_records AS m
                  ON r.record_id = m.metadata_id
                WHERE m.has_linked_text = 0
                """
            ).fetchone()[0]
        )
        orphan_retrieval_units = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM qiaopi_retrieval_units AS r
                LEFT JOIN qiaopi_text_records AS t
                  ON t.record_id = r.record_id
                WHERE t.record_id IS NULL
                """
            ).fetchone()[0]
        )
    actual_counts = (
        metadata_count,
        text_record_count,
        retrieval_unit_count,
    )
    expected_counts = (
        EXPECTED_METADATA_RECORD_COUNT,
        EXPECTED_TEXT_RECORD_COUNT,
        EXPECTED_RETRIEVAL_UNIT_COUNT,
    )
    if actual_counts != expected_counts:
        raise RetrievalBenchmarkError(
            "Retrieval corpus size does not match the accepted baseline: "
            f"expected {expected_counts}, got {actual_counts}."
        )
    if metadata_units or unlinked_metadata_in_rag or orphan_retrieval_units:
        raise RetrievalBenchmarkError(
            "Metadata-only records leaked into the full-text/RAG retrieval corpus."
        )
    return {
        "metadata_catalog": {
            "domain": METADATA_CATALOG_DOMAIN,
            "record_count": metadata_count,
            "rag_evidence_allowed": False,
        },
        "full_text_evidence": {
            "domain": FULL_TEXT_EVIDENCE_DOMAIN,
            "record_count": text_record_count,
            "retrieval_unit_count": retrieval_unit_count,
            "rag_evidence_allowed": True,
        },
        "metadata_units_in_full_text_corpus": metadata_units,
        "unlinked_metadata_in_rag_corpus": unlinked_metadata_in_rag,
        "orphan_retrieval_units": orphan_retrieval_units,
    }


def recall_at_k(ranked_ids: list[str], judgments: Mapping[str, int], k: int) -> float:
    relevant = {item_id for item_id, grade in judgments.items() if int(grade) > 0}
    if not relevant:
        return 0.0
    retrieved = set(ranked_ids[:k])
    return len(relevant.intersection(retrieved)) / len(relevant)


def reciprocal_rank_at_k(
    ranked_ids: list[str],
    judgments: Mapping[str, int],
    k: int,
) -> float:
    for rank, item_id in enumerate(ranked_ids[:k], start=1):
        if int(judgments.get(item_id, 0)) > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], judgments: Mapping[str, int], k: int) -> float:
    gains = [int(judgments.get(item_id, 0)) for item_id in ranked_ids[:k]]
    ideal_gains = sorted((int(value) for value in judgments.values()), reverse=True)[:k]

    def dcg(values: Iterable[int]) -> float:
        return sum(
            ((2**grade) - 1) / math.log2(rank + 1)
            for rank, grade in enumerate(values, start=1)
        )

    ideal = dcg(ideal_gains)
    return dcg(gains) / ideal if ideal else 0.0


def metric_bundle(
    ranked_ids: list[str],
    judgments: Mapping[str, int],
    cutoffs: Iterable[int] = DEFAULT_CUTOFFS,
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    max_cutoff = max(cutoffs)
    for cutoff in cutoffs:
        metrics[f"recall@{cutoff}"] = recall_at_k(ranked_ids, judgments, cutoff)
        metrics[f"ndcg@{cutoff}"] = ndcg_at_k(ranked_ids, judgments, cutoff)
    metrics[f"mrr@{max_cutoff}"] = reciprocal_rank_at_k(
        ranked_ids,
        judgments,
        max_cutoff,
    )
    return {key: round(value, 6) for key, value in metrics.items()}


def _record_ranking(results: Iterable[Mapping[str, Any]]) -> list[str]:
    ranked: list[str] = []
    seen: set[str] = set()
    for result in results:
        record_id = str(result.get("record_id") or "")
        if record_id and record_id not in seen:
            seen.add(record_id)
            ranked.append(record_id)
    return ranked


def _evaluate_metadata_case(
    case: Mapping[str, Any],
    method: str,
    top_k: int,
) -> dict[str, Any]:
    common = {
        "query": str(case["query"]),
        "top_k": top_k,
        "filters": case.get("filters") or {},
    }
    if method == "semantic":
        retrieval = search_metadata_semantic(**common)
        results = retrieval["results"]
        available = bool(retrieval["semantic_enabled"])
        quality = retrieval["semantic_quality"]
        error_message = retrieval["error_message"]
    elif method == "hybrid":
        retrieval = search_metadata_hybrid(**common)
        results = retrieval["results"]
        available = bool(retrieval["semantic_enabled"])
        quality = retrieval["semantic_quality"]
        error_message = retrieval["error_message"]
    else:
        results = search_metadata_records(**common)
        available = True
        quality = "disabled"
        error_message = None
    ranked_ids = [str(result["metadata_id"]) for result in results]
    judgments = case["relevance"]["metadata_records"]
    return {
        "query_id": case["query_id"],
        "domain": METADATA_CATALOG_DOMAIN,
        "method": (
            "metadata_fts5_bm25"
            if method == "keyword"
            else f"metadata_{method}"
        ),
        "target_level": "metadata_record",
        "ranked_ids": ranked_ids,
        "metrics": metric_bundle(ranked_ids, judgments),
        "available": available,
        "semantic_quality": quality,
        "acceptance_eligible": method == "keyword" or quality == "production",
        "error_message": error_message,
    }


def _full_text_results(
    *,
    method: str,
    case: Mapping[str, Any],
    top_k: int,
) -> dict[str, Any]:
    common = {
        "query": str(case["query"]),
        "top_k": top_k,
        "unit_types": list(case.get("unit_types") or []),
        "filters": case.get("filters") or {},
    }
    if method == "keyword":
        result = retrieve_keyword(expansion_mode="balanced", **common)
        return {
            "results": result["results"],
            "available": True,
            "semantic_quality": "disabled",
            "error_message": None,
        }
    if method == "semantic":
        result = semantic_search(**common)
        return {
            "results": result.get("results", []),
            "available": bool(result.get("semantic_enabled")),
            "semantic_quality": result.get("semantic_quality", "disabled"),
            "error_message": result.get("error_message"),
        }
    result = retrieve_hybrid(expansion_mode="balanced", **common)
    return {
        "results": result.get("results", []),
        "available": bool(result.get("semantic_enabled")),
        "semantic_quality": result.get("semantic_quality", "disabled"),
        "error_message": result.get("error_message"),
        "fusion_method": result.get("fusion_method"),
    }


def _evaluate_full_text_case(
    case: Mapping[str, Any],
    method: str,
    top_k: int,
) -> list[dict[str, Any]]:
    retrieval = _full_text_results(method=method, case=case, top_k=top_k)
    results = retrieval["results"]
    unit_ranking = [str(result.get("unit_id") or "") for result in results]
    unit_ranking = [item_id for item_id in unit_ranking if item_id]
    record_ranking = _record_ranking(results)
    quality = retrieval.get("semantic_quality", "disabled")
    eligible = method == "keyword" or quality == "production"
    common = {
        "query_id": case["query_id"],
        "domain": FULL_TEXT_EVIDENCE_DOMAIN,
        "method": method,
        "available": retrieval["available"] if method != "keyword" else True,
        "semantic_quality": quality,
        "acceptance_eligible": eligible,
        "error_message": retrieval.get("error_message"),
    }
    return [
        {
            **common,
            "target_level": "retrieval_unit",
            "ranked_ids": unit_ranking,
            "metrics": metric_bundle(
                unit_ranking,
                case["relevance"]["units"],
            ),
        },
        {
            **common,
            "target_level": "text_record",
            "ranked_ids": record_ranking,
            "metrics": metric_bundle(
                record_ranking,
                case["relevance"]["records"],
            ),
        },
    ]


def _aggregate(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for entry in entries:
        key = (
            str(entry["domain"]),
            str(entry["method"]),
            str(entry["target_level"]),
        )
        groups.setdefault(key, []).append(entry)

    summaries: list[dict[str, Any]] = []
    for (domain, method, target_level), rows in sorted(groups.items()):
        available_rows = [row for row in rows if row.get("available")]
        metric_names = sorted(
            {
                metric_name
                for row in available_rows
                for metric_name in row["metrics"]
            }
        )
        metrics = {
            metric_name: round(
                sum(float(row["metrics"][metric_name]) for row in available_rows)
                / len(available_rows),
                6,
            )
            for metric_name in metric_names
        } if available_rows else {}
        summaries.append(
            {
                "domain": domain,
                "method": method,
                "target_level": target_level,
                "query_count": len(rows),
                "available_query_count": len(available_rows),
                "acceptance_eligible": (
                    len(available_rows) == len(rows)
                    and all(
                        bool(row.get("acceptance_eligible"))
                        for row in available_rows
                    )
                ),
                "metrics": metrics,
            }
        )
    return summaries


def _metric_summary_map(
    summaries: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(item["method"]), str(item["target_level"])): item
        for item in summaries
        if item["domain"] == FULL_TEXT_EVIDENCE_DOMAIN
    }


def _improvement_report(
    summaries: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    summary_map = _metric_summary_map(summaries)
    comparisons: list[dict[str, Any]] = []
    for method in ("semantic", "hybrid"):
        for target_level in ("retrieval_unit", "text_record"):
            keyword = summary_map.get(("keyword", target_level), {})
            candidate = summary_map.get((method, target_level), {})
            keyword_metrics = keyword.get("metrics", {})
            candidate_metrics = candidate.get("metrics", {})
            deltas = {
                metric_name: round(
                    float(candidate_metrics.get(metric_name, 0.0))
                    - float(keyword_metrics.get(metric_name, 0.0)),
                    6,
                )
                for metric_name in sorted(
                    set(keyword_metrics) | set(candidate_metrics)
                )
            }
            comparisons.append(
                {
                    "method": method,
                    "target_level": target_level,
                    "available": bool(candidate.get("available_query_count")),
                    "acceptance_eligible": bool(
                        candidate.get("acceptance_eligible")
                    ),
                    "delta_vs_keyword": deltas,
                }
            )

    hybrid_rows = [
        row
        for row in comparisons
        if row["method"] == "hybrid" and row["acceptance_eligible"]
    ]
    production_accepted = len(hybrid_rows) == 2 and all(
        row["delta_vs_keyword"].get("ndcg@10", -1.0) >= 0.0
        and row["delta_vs_keyword"].get("mrr@10", -1.0) >= 0.0
        for row in hybrid_rows
    )
    return {
        "comparisons": comparisons,
        "production_semantic_accepted": production_accepted,
        "acceptance_rule": (
            "Production semantic/hybrid evaluation requires a non-Hash manifest. "
            "Hybrid NDCG@10 and MRR@10 must not regress against keyword retrieval "
            "at both retrieval-unit and text-record levels."
        ),
    }


@contextmanager
def _temporary_hash_index(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return
    attribute_names = (
        "SEMANTIC_SEARCH_ENABLED",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_DIM",
        "SEMANTIC_FAISS_INDEX_PATH",
        "SEMANTIC_FAISS_METADATA_PATH",
        "SEMANTIC_FAISS_MANIFEST_PATH",
    )
    original = {name: getattr(settings, name) for name in attribute_names}
    with tempfile.TemporaryDirectory(prefix="qiaopi-eval-hash-") as directory:
        root = Path(directory)
        settings.SEMANTIC_SEARCH_ENABLED = True
        settings.EMBEDDING_PROVIDER = "hash"
        settings.EMBEDDING_DIM = 384
        settings.SEMANTIC_FAISS_INDEX_PATH = root / "semantic.faiss"
        settings.SEMANTIC_FAISS_METADATA_PATH = root / "semantic_meta.jsonl"
        settings.SEMANTIC_FAISS_MANIFEST_PATH = root / "semantic_manifest.json"
        build_semantic_index(provider_name="hash")
        try:
            yield
        finally:
            for name, value in original.items():
                setattr(settings, name, value)


def evaluate_retrieval(
    *,
    benchmark_path: Path = DEFAULT_BENCHMARK_PATH,
    output_path: Path | None = DEFAULT_REPORT_PATH,
    build_hash_test_index: bool = False,
    top_k: int = 10,
) -> dict[str, Any]:
    cases = load_benchmark(benchmark_path)
    benchmark_validation = validate_benchmark_against_database(cases)
    corpus_boundaries = validate_corpus_boundaries()
    entries: list[dict[str, Any]] = []

    with _temporary_hash_index(build_hash_test_index):
        for case in cases:
            if case["domain"] == METADATA_CATALOG_DOMAIN:
                for method in METADATA_METHODS:
                    entries.append(
                        _evaluate_metadata_case(case, method, top_k)
                    )
                continue
            for method in FULL_TEXT_METHODS:
                entries.extend(
                    _evaluate_full_text_case(
                        case,
                        method=method,
                        top_k=top_k,
                    )
                )
        semantic_runtime_status = semantic_status()
        metadata_semantic_runtime_status = metadata_semantic_status()

    summaries = _aggregate(entries)
    report = {
        "report_version": "1",
        "created_at": _utc_now(),
        "benchmark_path": str(benchmark_path),
        "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
        "benchmark_query_count": len(cases),
        "benchmark_domain_counts": {
            domain: sum(1 for case in cases if case["domain"] == domain)
            for domain in (METADATA_CATALOG_DOMAIN, FULL_TEXT_EVIDENCE_DOMAIN)
        },
        "benchmark_validation": benchmark_validation,
        "corpus_boundaries": corpus_boundaries,
        "semantic_runtime_status": semantic_runtime_status,
        "metadata_semantic_runtime_status": metadata_semantic_runtime_status,
        "hash_test_index_used": build_hash_test_index,
        "summaries": summaries,
        "improvement": _improvement_report(summaries),
        "queries": entries,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate metadata-catalog and full-text evidence retrieval with "
            "Recall@K, MRR, and NDCG."
        )
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=DEFAULT_BENCHMARK_PATH,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
    )
    parser.add_argument(
        "--build-hash-test-index",
        action="store_true",
        help=(
            "Build a temporary Hash index for deterministic diagnostics. "
            "Results are marked test-only and cannot pass production semantic acceptance."
        ),
    )
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate_retrieval(
        benchmark_path=args.benchmark,
        output_path=args.output,
        build_hash_test_index=args.build_hash_test_index,
        top_k=max(1, args.top_k),
    )
    print(
        json.dumps(
            {
                "benchmark_query_count": report["benchmark_query_count"],
                "corpus_boundaries": report["corpus_boundaries"],
                "semantic_runtime_status": report["semantic_runtime_status"],
                "summaries": report["summaries"],
                "improvement": report["improvement"],
                "output_path": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
