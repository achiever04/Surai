"""
API v1 router - combines all endpoint routers
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    cameras,
    camera_stream_annotated,
    detections,
    watchlist,
    evidence,
    blockchain,
    analytics,
    alerts,
    federated_learning,
    settings
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    cameras.router,
    prefix="/cameras",
    tags=["Cameras"]
)

# Annotated stream endpoint (detection overlays)
api_router.include_router(
    camera_stream_annotated.router,
    prefix="/cameras",
    tags=["Cameras"]
)

api_router.include_router(
    detections.router,
    prefix="/detections",
    tags=["Detections"]
)

api_router.include_router(
    watchlist.router,
    prefix="/watchlist",
    tags=["Watchlist"]
)

api_router.include_router(
    evidence.router,
    prefix="/evidence",
    tags=["Evidence"]
)

api_router.include_router(
    blockchain.router,
    prefix="/blockchain",
    tags=["Blockchain"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

api_router.include_router(
    alerts.router,
    prefix="/alerts",
    tags=["Alerts"]
)

api_router.include_router(
    federated_learning.router,
    prefix="/fl",
    tags=["Federated Learning"]
)

api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["Settings"]
)