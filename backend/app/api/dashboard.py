from fastapi import APIRouter

from app.schemas import DashboardDistributionsResponse, DashboardStatsResponse
from app.services.dashboard_service import (
    get_dashboard_distributions,
    get_dashboard_stats,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats() -> DashboardStatsResponse:
    return DashboardStatsResponse(**get_dashboard_stats())


@router.get("/distributions", response_model=DashboardDistributionsResponse)
def dashboard_distributions() -> DashboardDistributionsResponse:
    return DashboardDistributionsResponse(**get_dashboard_distributions())
