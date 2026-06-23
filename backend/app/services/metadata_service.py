from __future__ import annotations

import json
from typing import Any

from app.database.repository import (
    fetch_linked_text_for_metadata,
    fetch_metadata_distributions,
    fetch_metadata_link_stats,
    fetch_metadata_record,
    fetch_metadata_stats,
    search_metadata_records,
)
from app.schemas import MetadataSearchRequest
from app.search.metadata_semantic_retriever import (
    search_metadata_hybrid,
    search_metadata_semantic,
)


def _raw_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _int_flag(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(value)


def get_metadata_stats() -> dict[str, Any]:
    return fetch_metadata_stats()


def get_metadata_distributions() -> dict[str, Any]:
    return fetch_metadata_distributions()


def search_metadata(request: MetadataSearchRequest) -> dict[str, Any]:
    if request.retrieval_mode == "semantic":
        retrieval = search_metadata_semantic(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
        return {
            "query": request.query,
            "top_k": request.top_k,
            "retrieval_mode": "semantic",
            "semantic_enabled": retrieval["semantic_enabled"],
            "semantic_quality": retrieval["semantic_quality"],
            "fusion_method": None,
            "error_message": retrieval["error_message"],
            "results": retrieval["results"],
        }
    if request.retrieval_mode == "hybrid":
        retrieval = search_metadata_hybrid(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )
        return {
            "query": request.query,
            "top_k": request.top_k,
            "retrieval_mode": "hybrid",
            "semantic_enabled": retrieval["semantic_enabled"],
            "semantic_quality": retrieval["semantic_quality"],
            "fusion_method": retrieval["fusion_method"],
            "error_message": retrieval["error_message"],
            "results": retrieval["results"],
        }
    results = []
    for row in search_metadata_records(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
    ):
        prepared = dict(row)
        prepared["bm25_score"] = float(row.get("score") or 0.0)
        prepared["semantic_score"] = 0.0
        prepared["final_score"] = float(row.get("score") or 0.0)
        prepared["retrieval_sources"] = ["keyword"]
        prepared["matched_reason"] = "目录元数据 FTS5 / BM25 命中"
        results.append(prepared)
    return {
        "query": request.query,
        "top_k": request.top_k,
        "retrieval_mode": "keyword",
        "semantic_enabled": False,
        "semantic_quality": "disabled",
        "fusion_method": None,
        "error_message": None,
        "results": results,
    }


def get_metadata_detail(metadata_id: str) -> dict[str, Any] | None:
    record = fetch_metadata_record(metadata_id)
    if not record:
        return None
    result = dict(record)
    result["raw_json"] = _raw_json(record.get("raw_json"))
    result["source_index"] = int(record.get("source_index") or 0)
    result["has_remittance"] = _int_flag(record.get("has_remittance"))
    result["has_linked_text"] = _int_flag(record.get("has_linked_text"))
    result["needs_review"] = _int_flag(record.get("needs_review"))
    result["parse_confidence"] = float(record.get("parse_confidence") or 0.0)
    return result


def get_metadata_linked_text(metadata_id: str) -> dict[str, Any] | None:
    row = fetch_linked_text_for_metadata(metadata_id)
    if not row:
        return None
    if not row.get("has_linked_text") or not row.get("record_id"):
        return {
            "metadata_id": metadata_id,
            "has_linked_text": False,
            "linked_record_id": None,
            "record_detail_summary": None,
            "message": "This metadata record has no linked full-text qiaopi record.",
        }
    return {
        "metadata_id": metadata_id,
        "has_linked_text": True,
        "linked_record_id": row.get("linked_record_id"),
        "record_detail_summary": {
            "record_id": row.get("record_id"),
            "title_reference": row.get("title_reference", ""),
            "sender": row.get("sender", ""),
            "recipient": row.get("recipient", ""),
            "date_text": row.get("date_text", ""),
            "year_normalized": row.get("year_normalized", ""),
            "main_intent": row.get("main_intent", ""),
            "theme_tags": row.get("theme_tags", ""),
            "has_remittance": _int_flag(row.get("has_remittance")),
            "place_mentions_normalized": row.get("place_mentions_normalized", ""),
        },
        "message": None,
    }


def get_metadata_links_stats() -> dict[str, Any]:
    return fetch_metadata_link_stats()
