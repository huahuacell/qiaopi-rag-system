from __future__ import annotations

import re
from typing import Any, Mapping

from app.database.repository import search_retrieval_units
from app.schemas import SearchRequest


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


def _search_result(row: Mapping[str, Any], query: str) -> dict:
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
        "bm25_score": float(row.get("score") or 0.0),
        "evidence_type": row.get("evidence_type", ""),
        "source_column": row.get("source_column", ""),
    }


def run_keyword_search(request: SearchRequest) -> dict:
    rows = search_retrieval_units(
        query=request.query,
        top_k=request.top_k,
        unit_types=request.unit_types,
        filters=request.filters,
    )
    return {
        "query": request.query,
        "top_k": request.top_k,
        "results": [_search_result(row, request.query) for row in rows],
    }
