"""
Analytics endpoints for dashboard and reports
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get main dashboard statistics"""
    service = AnalyticsService(db)
    stats = await service.get_dashboard_stats()
    return stats

@router.get("/trends")
async def get_detection_trends(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detection trends over time"""
    service = AnalyticsService(db)
    trends = await service.get_detection_trends(days)
    return trends

@router.get("/camera-health")
async def get_camera_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get health status of all cameras"""
    service = AnalyticsService(db)
    health = await service.get_camera_health()
    return health