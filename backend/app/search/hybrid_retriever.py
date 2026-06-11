from __future__ import annotations

from typing import Any, Mapping

from app.search.advanced_retriever import retrieve_advanced


def retrieve_hybrid_fallback(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    result = retrieve_advanced(
        query=query,
        top_k=top_k,
        unit_types=unit_types or [],
        filters=filters or {},
        expansion_mode=expansion_mode,
    )
    result["semantic_enabled"] = False
    return result
