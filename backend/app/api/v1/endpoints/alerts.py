"""
Alerts endpoint - provides detection alerts organized by priority/severity
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, desc
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.detection import Detection
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

# Severity mapping based on detection type
SEVERITY_MAP = {
    "weapon_detected": "critical",
    "watchlist_match": "critical",
    "suspicious_object": "high",
    "spoof_attempt": "high",
    "aggressive_pose": "high",
    "emotion_alert": "medium",
    "face_detection": "low",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _get_severity(detection) -> str:
    """Get severity from detection_metadata or infer from detection_type."""
    if detection.detection_metadata and isinstance(detection.detection_metadata, dict):
        severity = detection.detection_metadata.get("severity")
        if severity and severity in SEVERITY_ORDER:
            return severity
    return SEVERITY_MAP.get(detection.detection_type, "low")


def _detection_to_alert(detection) -> dict:
    """Convert a Detection ORM object to an alert response dict."""
    severity = _get_severity(detection)
    metadata = detection.detection_metadata or {}

    return {
        "id": detection.id,
        "event_id": detection.event_id,
        "camera_id": detection.camera_id,
        "detection_type": detection.detection_type,
        "severity": severity,
        "confidence": detection.confidence,
        "timestamp": detection.timestamp.isoformat() if detection.timestamp else None,
        "matched_person_id": detection.matched_person_id,
        "emotion": metadata.get("emotion") or detection.emotion,
        "is_verified": detection.is_verified,
        "is_real_face": metadata.get("is_real_face", True),
        "has_weapon": metadata.get("has_weapon", False),
        "weapons_detected": metadata.get("weapons_detected", []),
        "thumbnail_path": detection.thumbnail_path,
        "operator_action": detection.operator_action,
    }


@router.get("/")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    detection_type: Optional[str] = Query(None, description="Filter by detection type"),
    hours: int = Query(24, ge=1, le=720, description="Lookback window in hours"),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alerts sorted by severity then timestamp."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = select(Detection).where(Detection.timestamp >= since)

    if detection_type:
        query = query.where(Detection.detection_type == detection_type)

    # For severity filtering we need to filter in memory after query
    # because severity lives in the JSON metadata field
    query = query.order_by(Detection.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    detections = result.scalars().all()

    alerts = [_detection_to_alert(d) for d in detections]

    # Apply severity filter in memory
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]

    # Sort by severity priority then timestamp desc
    alerts.sort(key=lambda a: (SEVERITY_ORDER.get(a["severity"], 99), -(
        datetime.fromisoformat(a["timestamp"]).timestamp() if a["timestamp"] else 0
    )))

    return alerts


@router.get("/summary")
async def get_alerts_summary(
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alert count breakdown by severity and type."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = await db.execute(
        select(Detection).where(Detection.timestamp >= since)
    )
    detections = result.scalars().all()

    # Count by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    type_counts = {}

    for d in detections:
        sev = _get_severity(d)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        dtype = d.detection_type or "unknown"
        type_counts[dtype] = type_counts.get(dtype, 0) + 1

    return {
        "total": len(detections),
        "by_severity": severity_counts,
        "by_type": type_counts,
        "hours": hours,
    }
