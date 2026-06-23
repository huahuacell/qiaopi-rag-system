from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.database.repository import search_retrieval_units
from app.search.query_expansion import (
    QueryExpansion,
    expand_query,
    terms_for_expansion_mode,
)
from app.search.reranker import rerank_units
from app.search.result_aggregator import group_results_by_record


def _query_from_terms(terms: Iterable[str]) -> str:
    return " ".join(term for term in terms if term)


def _merge_unique_rows(existing_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {row.get("unit_id") for row in existing_rows}
    merged_rows = list(existing_rows)
    for row in new_rows:
        unit_id = row.get("unit_id")
        if not unit_id or unit_id in seen:
            continue
        seen.add(unit_id)
        merged_rows.append(row)
    return merged_rows


def _search_stage(
    terms: list[str],
    internal_limit: int,
    unit_types: list[str],
    filters: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not terms:
        return []
    return search_retrieval_units(
        query=_query_from_terms(terms),
        top_k=internal_limit,
        unit_types=unit_types,
        filters=filters,
    )


def _retrieve_staged(
    expansion: QueryExpansion,
    expansion_mode: str,
    top_k: int,
    unit_types: list[str],
    filters: Mapping[str, Any],
) -> list[dict[str, Any]]:
    internal_limit = max(100, top_k * 10)
    mode = expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced"
    if mode in {"strict", "broad"}:
        return _search_stage(
            terms_for_expansion_mode(expansion, mode),
            internal_limit,
            unit_types,
            filters,
        )

    rows = _search_stage(
        terms_for_expansion_mode(expansion, "balanced", stage=1),
        internal_limit,
        unit_types,
        filters,
    )
    if len(rows) < top_k:
        rows = _merge_unique_rows(
            rows,
            _search_stage(
                terms_for_expansion_mode(expansion, "balanced", stage=2),
                internal_limit,
                unit_types,
                filters,
            ),
        )
    if len(rows) < top_k:
        rows = _merge_unique_rows(
            rows,
            _search_stage(
                terms_for_expansion_mode(expansion, "balanced", stage=3),
                internal_limit,
                unit_types,
                filters,
            ),
        )
    return rows


def retrieve_keyword(
    query: str,
    top_k: int = 10,
    unit_types: list[str] | None = None,
    filters: Mapping[str, Any] | None = None,
    expansion: QueryExpansion | None = None,
    expansion_mode: str = "balanced",
) -> dict[str, Any]:
    query_expansion = expansion or expand_query(query)
    requested_unit_types = unit_types or []
    rows = _retrieve_staged(
        expansion=query_expansion,
        expansion_mode=expansion_mode,
        top_k=top_k,
        unit_types=requested_unit_types,
        filters=filters or {},
    )
    reranked_results = rerank_units(
        rows,
        expansion=query_expansion,
        requested_unit_types=requested_unit_types,
        top_k=top_k,
    )
    return {
        "expansion": query_expansion,
        "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
        "results": reranked_results,
        "grouped_by_record": group_results_by_record(reranked_results),
    }
