from fastapi import APIRouter

from app.schemas import SearchRequest, SearchResponse
from app.services.search_service import run_keyword_search


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/keyword", response_model=SearchResponse)
def keyword_search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(**run_keyword_search(request))
