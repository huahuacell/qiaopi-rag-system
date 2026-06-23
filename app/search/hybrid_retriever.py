from __future__ import annotations

from typing import Any, Mapping

from app.search.advanced_retriever import retrieve_advanced
from app.search.result_aggregator import group_results_by_record
from app.search.semantic_retriever import semantic_search


RRF_K = 60


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rank_score(rank: int) -> float:
    return 1.0 / (RRF_K + rank)


def _keyword_fallback(keyword_result: dict[str, Any], error_message: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in keyword_result["results"]:
        prepared_row = dict(row)
        prepared_row["semantic_score"] = 0.0
        prepared_row["retrieval_sources"] = ["keyword"]
        rows.append(prepared_row)
    return {
        **keyword_result,
        "results": rows,
        "grouped_by_record": group_results_by_record(rows),
        "semantic_enabled": False,
        "semantic_quality": "disabled",
        "fusion_method": "keyword_fallback",
        "error_message": error_message,
    }


def retrieve_hybrid(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    requested_unit_types = unit_types or []
    active_filters = filters or {}
    keyword_result = retrieve_advanced(
        query=query,
        top_k=max(top_k * 4, top_k, 20),
        unit_types=requested_unit_types,
        filters=active_filters,
        expansion_mode=expansion_mode,
    )
    semantic_result = semantic_search(
        query=query,
        top_k=max(top_k * 4, top_k, 20),
        unit_types=requested_unit_types,
        filters=active_filters,
    )
    if not semantic_result.get("semantic_enabled"):
        return _keyword_fallback(
            keyword_result,
            error_message=semantic_result.get("error_message"),
        )

    combined: dict[str, dict[str, Any]] = {}
    rrf_scores: dict[str, float] = {}

    def add_row(row: Mapping[str, Any], source: str, rank: int) -> None:
        unit_id = str(row.get("unit_id", ""))
        if not unit_id:
            return
        if unit_id not in combined:
            combined[unit_id] = dict(row)
            combined[unit_id]["bm25_score"] = _float(row.get("bm25_score"))
            combined[unit_id]["semantic_score"] = _float(row.get("semantic_score"))
            combined[unit_id]["retrieval_sources"] = []
        target = combined[unit_id]
        sources = target["retrieval_sources"]
        if source not in sources:
            sources.append(source)
        if source == "keyword":
            target["bm25_score"] = _float(row.get("bm25_score"))
            target["keyword_final_score"] = _float(row.get("final_score"))
        if source == "semantic":
            target["semantic_score"] = _float(row.get("semantic_score"))
            if not target.get("matched_text"):
                target["matched_text"] = row.get("matched_text", row.get("unit_text", ""))
        existing_reason = str(target.get("matched_reason", "") or "")
        incoming_reason = str(row.get("matched_reason", "") or "")
        if incoming_reason and incoming_reason not in existing_reason:
            target["matched_reason"] = (
                f"{existing_reason}；{incoming_reason}" if existing_reason else incoming_reason
            )
        rrf_scores[unit_id] = rrf_scores.get(unit_id, 0.0) + _rank_score(rank)

    for rank, row in enumerate(keyword_result["results"], start=1):
        add_row(row, "keyword", rank)
    for rank, row in enumerate(semantic_result["results"], start=1):
        add_row(row, "semantic", rank)

    fused_rows: list[dict[str, Any]] = []
    for unit_id, row in combined.items():
        fused_score = rrf_scores.get(unit_id, 0.0)
        prepared_row = dict(row)
        prepared_row["fusion_score"] = round(fused_score, 8)
        prepared_row["final_score"] = round(fused_score, 8)
        prepared_row.setdefault("matched_text", prepared_row.get("unit_text", ""))
        prepared_row.setdefault("original_hit_count", 0)
        prepared_row.setdefault("strong_hit_count", 0)
        prepared_row.setdefault("medium_hit_count", 0)
        prepared_row.setdefault("weak_hit_count", 0)
        fused_rows.append(prepared_row)

    fused_rows = sorted(
        fused_rows,
        key=lambda item: (
            -_float(item.get("fusion_score")),
            -_float(item.get("semantic_score")),
            -_float(item.get("keyword_final_score")),
            str(item.get("unit_id", "")),
        ),
    )[:top_k]

    return {
        "expansion": keyword_result["expansion"],
        "expansion_mode": keyword_result["expansion_mode"],
        "results": fused_rows,
        "grouped_by_record": group_results_by_record(fused_rows),
        "semantic_enabled": True,
        "semantic_quality": semantic_result.get(
            "semantic_quality",
            "disabled",
        ),
        "fusion_method": "rrf",
        "error_message": None,
    }


def retrieve_hybrid_fallback(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    return retrieve_hybrid(
        query=query,
        top_k=top_k,
        unit_types=unit_types,
        filters=filters,
        expansion_mode=expansion_mode,
    )
