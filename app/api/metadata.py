from fastapi import APIRouter, HTTPException

from app.schemas import (
    MetadataDetailResponse,
    MetadataDistributionsResponse,
    MetadataLinkedTextResponse,
    MetadataLinkStatsResponse,
    MetadataSearchRequest,
    MetadataSearchResponse,
    MetadataStatsResponse,
)
from app.services.metadata_service import (
    get_metadata_detail,
    get_metadata_distributions,
    get_metadata_linked_text,
    get_metadata_links_stats,
    get_metadata_stats,
    search_metadata,
)


router = APIRouter(prefix="/api/metadata", tags=["metadata"])


def _not_found(metadata_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Metadata record not found: {metadata_id}")


@router.get("/stats", response_model=MetadataStatsResponse)
def metadata_stats() -> MetadataStatsResponse:
    return MetadataStatsResponse(**get_metadata_stats())


@router.get("/distributions", response_model=MetadataDistributionsResponse)
def metadata_distributions() -> MetadataDistributionsResponse:
    return MetadataDistributionsResponse(**get_metadata_distributions())


@router.post("/search", response_model=MetadataSearchResponse)
def metadata_search(request: MetadataSearchRequest) -> MetadataSearchResponse:
    return MetadataSearchResponse(**search_metadata(request))


@router.get("/links/stats", response_model=MetadataLinkStatsResponse)
def metadata_links_stats() -> MetadataLinkStatsResponse:
    return MetadataLinkStatsResponse(**get_metadata_links_stats())


@router.get("/{metadata_id}", response_model=MetadataDetailResponse)
def metadata_detail(metadata_id: str) -> MetadataDetailResponse:
    detail = get_metadata_detail(metadata_id)
    if detail is None:
        raise _not_found(metadata_id)
    return MetadataDetailResponse(**detail)


@router.get("/{metadata_id}/linked-text", response_model=MetadataLinkedTextResponse)
def metadata_linked_text(metadata_id: str) -> MetadataLinkedTextResponse:
    response = get_metadata_linked_text(metadata_id)
    if response is None:
        raise _not_found(metadata_id)
    return MetadataLinkedTextResponse(**response)
