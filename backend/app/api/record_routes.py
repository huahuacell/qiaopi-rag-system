from fastapi import APIRouter, HTTPException

from app.schemas import EvidenceResponse, EntityResponse, RecordDetailResponse, SearchResponse
from app.services.record_service import (
    get_record_detail,
    get_record_entities,
    get_record_evidence,
    get_similar_records,
)


router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/{record_id}", response_model=RecordDetailResponse)
def record_detail(record_id: str) -> RecordDetailResponse:
    detail = get_record_detail(record_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return RecordDetailResponse(**detail)


@router.get("/{record_id}/entities", response_model=EntityResponse)
def record_entities(record_id: str) -> EntityResponse:
    entities = get_record_entities(record_id)
    if entities is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return EntityResponse(**entities)


@router.get("/{record_id}/evidence", response_model=EvidenceResponse)
def record_evidence(record_id: str) -> EvidenceResponse:
    evidence = get_record_evidence(record_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return EvidenceResponse(**evidence)


@router.get("/{record_id}/similar", response_model=SearchResponse)
def similar_records(record_id: str) -> SearchResponse:
    return SearchResponse(**get_similar_records(record_id))

