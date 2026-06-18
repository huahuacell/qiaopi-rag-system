from __future__ import annotations

from typing import Any, Mapping

from app.search.keyword_retriever import retrieve_keyword
from app.search.query_expansion import expand_query


def retrieve_advanced(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    return retrieve_keyword(
        query=query,
        top_k=top_k,
        unit_types=unit_types or [],
        filters=filters or {},
        expansion=expand_query(query),
        expansion_mode=expansion_mode,
    )
