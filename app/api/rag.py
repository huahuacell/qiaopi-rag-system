from fastapi import APIRouter

from app.schemas import (
    RagContextRequest,
    RagContextResponse,
    StyleContextRequest,
    StyleContextResponse,
)
from app.services.rag_context_service import prepare_rag_context, prepare_style_context


router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/context", response_model=RagContextResponse)
def rag_context(request: RagContextRequest) -> RagContextResponse:
    return RagContextResponse(**prepare_rag_context(request))


@router.post("/style-context", response_model=StyleContextResponse)
def style_context(request: StyleContextRequest) -> StyleContextResponse:
    return StyleContextResponse(**prepare_style_context(request))
