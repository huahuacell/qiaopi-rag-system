from fastapi import APIRouter

from app.schemas import ConsistencyCheckRequest, ConsistencyCheckResponse
from app.services.validation_service import run_consistency_check


router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/consistency-check", response_model=ConsistencyCheckResponse)
def consistency_check(request: ConsistencyCheckRequest) -> ConsistencyCheckResponse:
    return ConsistencyCheckResponse(**run_consistency_check(request))
