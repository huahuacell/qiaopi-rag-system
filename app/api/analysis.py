from fastapi import APIRouter

from app.schemas import EmotionAnalysisResponse
from app.services.analysis_service import get_emotion_analysis


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/emotions", response_model=EmotionAnalysisResponse)
def emotion_analysis() -> EmotionAnalysisResponse:
    return EmotionAnalysisResponse(**get_emotion_analysis())

