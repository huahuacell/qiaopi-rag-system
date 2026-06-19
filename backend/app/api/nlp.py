from fastapi import APIRouter

from app.nlp.pipeline import analyze_qiaopi_text
from app.schemas import NlpAnalyzeRequest, NlpAnalyzeResponse


router = APIRouter(prefix="/api/nlp", tags=["nlp"])


@router.post("/analyze", response_model=NlpAnalyzeResponse)
def analyze_text(request: NlpAnalyzeRequest) -> NlpAnalyzeResponse:
    return NlpAnalyzeResponse(**analyze_qiaopi_text(request.text, request.task))
