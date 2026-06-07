from fastapi import APIRouter

from app.schemas import (
    PlainInterpretationRequest,
    PlainInterpretationResponse,
    StyleTransferRequest,
    StyleTransferResponse,
)
from app.services.generation_service import generate_plain_interpretation, generate_style_transfer


router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("/plain-interpretation", response_model=PlainInterpretationResponse)
def plain_interpretation(request: PlainInterpretationRequest) -> PlainInterpretationResponse:
    return PlainInterpretationResponse(**generate_plain_interpretation(request))


@router.post("/style-transfer", response_model=StyleTransferResponse)
def style_transfer(request: StyleTransferRequest) -> StyleTransferResponse:
    return StyleTransferResponse(**generate_style_transfer(request))

