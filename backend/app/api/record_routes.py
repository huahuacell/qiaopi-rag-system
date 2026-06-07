from fastapi import APIRouter

from app.schemas import EntityResponse, RecordDetailResponse, SearchResponse
from app.services.record_service import get_record_detail, get_record_entities, get_similar_records


router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/{record_id}", response_model=RecordDetailResponse)
def record_detail(record_id: str) -> RecordDetailResponse:
    return RecordDetailResponse(**get_record_detail(record_id))


@router.get("/{record_id}/entities", response_model=EntityResponse)
def record_entities(record_id: str) -> EntityResponse:
    return EntityResponse(**get_record_entities(record_id))


@router.get("/{record_id}/similar", response_model=SearchResponse)
def similar_records(record_id: str) -> SearchResponse:
    return SearchResponse(**get_similar_records(record_id))

