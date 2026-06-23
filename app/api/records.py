from fastapi import APIRouter, HTTPException

from app.schemas import (
    AmountsResponse,
    EntityResponse,
    EvidenceResponse,
    PlacesResponse,
    RecordDetailResponse,
    RetrievalUnitsResponse,
)
from app.services.record_service import (
    get_record_amounts,
    get_record_detail,
    get_record_entities,
    get_record_evidence,
    get_record_places,
    get_record_retrieval_units,
)


router = APIRouter(prefix="/api/records", tags=["records"])


def _not_found(record_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Record not found: {record_id}")


@router.get("/{record_id}", response_model=RecordDetailResponse)
def record_detail(record_id: str) -> RecordDetailResponse:
    detail = get_record_detail(record_id)
    if detail is None:
        raise _not_found(record_id)
    return RecordDetailResponse(**detail)


@router.get("/{record_id}/amounts", response_model=AmountsResponse)
def record_amounts(record_id: str) -> AmountsResponse:
    amounts = get_record_amounts(record_id)
    if amounts is None:
        raise _not_found(record_id)
    return AmountsResponse(record_id=record_id, amounts=amounts)


@router.get("/{record_id}/entities", response_model=EntityResponse)
def record_entities(record_id: str) -> EntityResponse:
    entities = get_record_entities(record_id)
    if entities is None:
        raise _not_found(record_id)
    return EntityResponse(record_id=record_id, entities=entities)


@router.get("/{record_id}/places", response_model=PlacesResponse)
def record_places(record_id: str) -> PlacesResponse:
    places = get_record_places(record_id)
    if places is None:
        raise _not_found(record_id)
    return PlacesResponse(record_id=record_id, places=places)


@router.get("/{record_id}/evidence", response_model=EvidenceResponse)
def record_evidence(record_id: str) -> EvidenceResponse:
    evidence = get_record_evidence(record_id)
    if evidence is None:
        raise _not_found(record_id)
    return EvidenceResponse(record_id=record_id, evidence=evidence)


@router.get("/{record_id}/retrieval-units", response_model=RetrievalUnitsResponse)
def record_retrieval_units(record_id: str) -> RetrievalUnitsResponse:
    retrieval_units = get_record_retrieval_units(record_id)
    if retrieval_units is None:
        raise _not_found(record_id)
    return RetrievalUnitsResponse(record_id=record_id, retrieval_units=retrieval_units)
