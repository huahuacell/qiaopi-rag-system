from __future__ import annotations

from app.database.repository import insert_query_log
from app.schemas import RagContextRequest, StyleContextRequest
from app.search.context_builder import build_rag_context, build_style_context


def _log_query(
    *,
    endpoint: str,
    query: str,
    filters: dict,
    top_k: int,
    returned_count: int,
) -> None:
    try:
        insert_query_log(
            endpoint=endpoint,
            query=query,
            filters=filters,
            top_k=top_k,
            returned_count=returned_count,
        )
    except Exception:
        return


def prepare_rag_context(request: RagContextRequest) -> dict:
    response = build_rag_context(
        query=request.query,
        top_k=request.top_k,
        unit_types=request.unit_types,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
        retrieval_mode=request.retrieval_mode,
    )
    _log_query(
        endpoint="/api/rag/context",
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
        returned_count=response["evidence_count"],
    )
    return response


def prepare_style_context(request: StyleContextRequest) -> dict:
    response = build_style_context(
        query=request.query,
        top_k=request.top_k,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )
    returned_count = sum(len(examples) for examples in response["style_slots"].values())
    _log_query(
        endpoint="/api/rag/style-context",
        query=request.query,
        filters=request.filters,
        top_k=request.top_k,
        returned_count=returned_count,
    )
    return response
