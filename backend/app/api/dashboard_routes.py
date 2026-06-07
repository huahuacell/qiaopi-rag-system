from fastapi import APIRouter

from app.schemas import DashboardStatsResponse
from app.services.dashboard_service import get_dashboard_stats


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats() -> DashboardStatsResponse:
    return DashboardStatsResponse(**get_dashboard_stats())

