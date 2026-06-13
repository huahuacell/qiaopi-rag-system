from fastapi import APIRouter

from app.schemas import (
    HybridSearchResponse,
    SearchRequest,
    SearchResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticStatusResponse,
)
from app.services.search_service import (
    run_advanced_search,
    run_hybrid_search,
    run_keyword_search,
    run_semantic_search,
)
from app.search.semantic_retriever import semantic_status


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/keyword", response_model=SearchResponse)
def keyword_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_keyword_search(request))


@router.post("/advanced", response_model=SearchResponse)
def advanced_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_advanced_search(request))


@router.post("/semantic", response_model=SemanticSearchResponse)
def semantic_search_endpoint(request: SemanticSearchRequest) -> SemanticSearchResponse:
    return SemanticSearchResponse(**run_semantic_search(request))


@router.get("/semantic/status", response_model=SemanticStatusResponse)
def semantic_search_status() -> SemanticStatusResponse:
    return SemanticStatusResponse(**semantic_status())


@router.post("/hybrid", response_model=HybridSearchResponse)
def hybrid_search(request: SearchRequest) -> HybridSearchResponse:
    return HybridSearchResponse(**run_hybrid_search(request))
