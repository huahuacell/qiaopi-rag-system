from __future__ import annotations

import re
from typing import Any, Mapping

from app.schemas import SearchRequest
from app.search.advanced_retriever import retrieve_advanced
from app.search.hybrid_retriever import retrieve_hybrid_fallback
from app.search.keyword_retriever import retrieve_keyword
from app.search.query_expansion import QueryExpansion, terms_for_expansion_mode


def _snippet(unit_text: str, query: str, length: int = 120) -> str:
    text = unit_text.strip()
    if len(text) <= length:
        return text

    query_terms = [
        term
        for term in re.split(r"[\s；;，,、。！？!?：:（）()【】\[\]《》<>“”\"'‘’/|\\]+", query)
        if term
    ]
    first_match = min(
        (text.find(term) for term in query_terms if term in text),
        default=-1,
    )
    if first_match < 0:
        return text[:length] + "..."

    start = max(0, first_match - 30)
    end = min(len(text), start + length)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end] + suffix


def _unit_result(row: Mapping[str, Any], query: str) -> dict[str, Any]:
    unit_text = str(row.get("unit_text", "") or "")
    return {
        "record_id": row.get("record_id", ""),
        "unit_id": row.get("unit_id", ""),
        "unit_type": row.get("unit_type", ""),
        "title_reference": row.get("title_reference", ""),
        "sender": row.get("sender", ""),
        "recipient": row.get("recipient", ""),
        "date_text": row.get("date_text", ""),
        "main_intent": row.get("main_intent", ""),
        "unit_text": unit_text,
        "snippet": _snippet(unit_text, query),
        "matched_text": row.get("matched_text", unit_text),
        "matched_reason": row.get("matched_reason", ""),
        "bm25_score": float(row.get("bm25_score") or 0.0),
        "final_score": float(row.get("final_score") or 0.0),
        "original_hit_count": int(row.get("original_hit_count") or 0),
        "strong_hit_count": int(row.get("strong_hit_count") or 0),
        "medium_hit_count": int(row.get("medium_hit_count") or 0),
        "weak_hit_count": int(row.get("weak_hit_count") or 0),
        "evidence_type": row.get("evidence_type", ""),
        "source_column": row.get("source_column", ""),
    }


def _response(
    request: SearchRequest,
    retrieval_result: Mapping[str, Any],
    semantic_enabled: bool = False,
) -> dict[str, Any]:
    expansion: QueryExpansion = retrieval_result["expansion"]
    expansion_mode = retrieval_result.get("expansion_mode", request.expansion_mode)
    return {
        "query": expansion.original_query,
        "normalized_query": expansion.normalized_query,
        "expanded_query": " ".join(terms_for_expansion_mode(expansion, expansion_mode)),
        "expansion_mode": expansion_mode,
        "original_terms": expansion.original_terms,
        "strong_expansion_terms": expansion.strong_expansion_terms,
        "medium_expansion_terms": expansion.medium_expansion_terms,
        "weak_expansion_terms": expansion.weak_expansion_terms,
        "expansion_terms": expansion.expansion_terms,
        "top_k": request.top_k,
        "semantic_enabled": semantic_enabled,
        "results": [
            _unit_result(row, expansion.normalized_query)
            for row in retrieval_result["results"]
        ],
        "grouped_by_record": retrieval_result["grouped_by_record"],
    }


def run_keyword_search(request: SearchRequest) -> dict[str, Any]:
    retrieval_result = retrieve_keyword(
        query=request.query,
        top_k=request.top_k,
        unit_types=request.unit_types,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )
    return _response(request, retrieval_result, semantic_enabled=False)


def run_advanced_search(request: SearchRequest) -> dict[str, Any]:
    retrieval_result = retrieve_advanced(
        query=request.query,
        top_k=request.top_k,
        unit_types=request.unit_types,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )
    return _response(request, retrieval_result, semantic_enabled=False)


def run_hybrid_search(request: SearchRequest) -> dict[str, Any]:
    retrieval_result = retrieve_hybrid_fallback(
        query=request.query,
        top_k=request.top_k,
        unit_types=request.unit_types,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )
    return _response(
        request,
        retrieval_result,
        semantic_enabled=bool(retrieval_result.get("semantic_enabled", False)),
    )
