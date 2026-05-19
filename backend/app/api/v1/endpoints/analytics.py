from fastapi import APIRouter, Depends, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.models.user import User
from app.middleware.deps import get_current_user
from app.services.analytics_service import TelemetryService

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary")
async def get_analytics_summary(current_user: User = Depends(get_current_user)):
    """
    Returns aggregated time-series metrics for the current user's API keys (hourly trends,
    status distribution, latency profile, and top active credentials) for frontend charts ingestion.
    """
    summary = await TelemetryService.get_analytics_summary(str(current_user.id))
    return summary

@router.get("/metrics")
def prometheus_metrics():
    """
    Analytics-nested scraper endpoint returning standard Prometheus text format.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
