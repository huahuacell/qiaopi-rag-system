from fastapi import APIRouter

from app.schemas import SearchRequest, SearchResponse
from app.services.search_service import (
    run_advanced_search,
    run_hybrid_search,
    run_keyword_search,
)


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/keyword", response_model=SearchResponse)
def keyword_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_keyword_search(request))


@router.post("/advanced", response_model=SearchResponse)
def advanced_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_advanced_search(request))


@router.post("/hybrid", response_model=SearchResponse)
def hybrid_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_hybrid_search(request))
