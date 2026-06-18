from fastapi import APIRouter

from app import settings
from app.schemas import (
    GenerationInterpretRequest,
    GenerationInterpretResponse,
    GenerationStyleTransferRequest,
    GenerationStyleTransferResponse,
    PromptPreviewRequest,
    PromptPreviewResponse,
    QwenConfigStatusResponse,
)
from app.services.generation_service import (
    generate_interpretation,
    generate_style_transfer,
    preview_prompt,
)


router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.get("/qwen-status", response_model=QwenConfigStatusResponse)
def qwen_status() -> QwenConfigStatusResponse:
    return QwenConfigStatusResponse(**settings.qwen_config_status())


@router.post("/preview-prompt", response_model=PromptPreviewResponse)
def generation_prompt_preview(request: PromptPreviewRequest) -> PromptPreviewResponse:
    return PromptPreviewResponse(**preview_prompt(request))


@router.post("/interpret", response_model=GenerationInterpretResponse)
def interpretation_generation(
    request: GenerationInterpretRequest,
) -> GenerationInterpretResponse:
    return GenerationInterpretResponse(**generate_interpretation(request))


@router.post("/style-transfer", response_model=GenerationStyleTransferResponse)
def style_transfer_generation(
    request: GenerationStyleTransferRequest,
) -> GenerationStyleTransferResponse:
    return GenerationStyleTransferResponse(**generate_style_transfer(request))
