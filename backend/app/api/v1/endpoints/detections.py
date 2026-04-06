"""
Detection management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.detection import Detection
from app.models.user import User
from app.schemas.detection import DetectionResponse, DetectionDetail, DetectionUpdate
from app.api.deps import get_current_user, require_role

router = APIRouter()

@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    camera_id: Optional[int] = None,
    detection_type: Optional[str] = None,
    is_verified: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detections with filters"""
    query = select(Detection)
    
    if camera_id:
        query = query.where(Detection.camera_id == camera_id)
    
    if detection_type:
        query = query.where(Detection.detection_type == detection_type)
    
    if is_verified is not None:
        query = query.where(Detection.is_verified == is_verified)
    
    if start_date:
        query = query.where(Detection.timestamp >= start_date)
    
    if end_date:
        query = query.where(Detection.timestamp <= end_date)
    
    query = query.order_by(Detection.timestamp.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    detections = result.scalars().all()
    
    return detections

@router.get("/{detection_id}")
async def get_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detection by ID, including matched person photos if available"""
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id)
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )
    
    # Build response dict from the ORM model
    response = {
        "id": detection.id,
        "event_id": detection.event_id,
        "camera_id": detection.camera_id,
        "detection_type": detection.detection_type,
        "confidence": detection.confidence,
        "emotion": detection.emotion,
        "timestamp": detection.timestamp,
        "matched_person_id": detection.matched_person_id,
        "is_verified": detection.is_verified,
        "is_false_positive": detection.is_false_positive,
        "operator_action": detection.operator_action,
        "blockchain_tx_id": detection.blockchain_tx_id,
        "face_bbox": detection.face_bbox,
        "behavior_tags": detection.behavior_tags,
        "local_path": detection.local_path,
        "thumbnail_path": detection.thumbnail_path,
        "notes": detection.notes,
        "detection_metadata": detection.detection_metadata,
    }
    
    import base64
    import os
    
    # Load detected frame image (saved by _handle_detection_sync at detection time)
    # This works for ALL detection types: face, weapon, watchlist match
    if detection.local_path:
        try:
            if os.path.exists(detection.local_path):
                with open(detection.local_path, 'rb') as f:
                    frame_data = base64.b64encode(f.read()).decode('utf-8')
                    response["detected_frame"] = f"data:image/jpeg;base64,{frame_data}"
        except Exception:
            response["detected_frame"] = None
    
    # If this detection matched a watchlist person, load their name and photos
    if detection.matched_person_id:
        from app.models.watchlist import WatchlistPerson
        
        person_result = await db.execute(
            select(WatchlistPerson).where(WatchlistPerson.id == detection.matched_person_id)
        )
        person = person_result.scalar_one_or_none()
        
        if person:
            photos = []
            if person.photos_local_paths:
                for photo_path in person.photos_local_paths:
                    try:
                        if os.path.exists(photo_path):
                            with open(photo_path, 'rb') as f:
                                photo_data = base64.b64encode(f.read()).decode('utf-8')
                                photos.append(f"data:image/jpeg;base64,{photo_data}")
                    except Exception:
                        pass
            
            response["matched_person_name"] = person.name
            response["matched_person_category"] = person.category
            response["matched_person_photos"] = photos
    
    return response

@router.patch("/{detection_id}", response_model=DetectionResponse)
async def update_detection(
    detection_id: int,
    detection_update: DetectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """Update detection (operator action)"""
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id)
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )
    
    # Update fields
    update_data = detection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(detection, field, value)
    
    detection.operator_id = current_user.id
    detection.action_timestamp = datetime.now(timezone.utc)
    detection.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(detection)
    
    return detection

@router.get("/stats/summary")
async def get_detection_summary(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detection statistics summary"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total detections
    total_result = await db.execute(
        select(func.count(Detection.id))
        .where(Detection.timestamp >= start_date)
    )
    total = total_result.scalar() or 0
    
    # By type
    type_result = await db.execute(
        select(Detection.detection_type, func.count(Detection.id))
        .where(Detection.timestamp >= start_date)
        .group_by(Detection.detection_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}
    
    # Verified vs unverified
    verified_result = await db.execute(
        select(Detection.is_verified, func.count(Detection.id))
        .where(Detection.timestamp >= start_date)
        .group_by(Detection.is_verified)
    )
    verification = {row[0]: row[1] for row in verified_result.all()}
    
    return {
        "period_days": days,
        "total_detections": total,
        "by_type": by_type,
        "verified": verification.get(True, 0),
        "unverified": verification.get(False, 0)
    }

@router.delete("/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete detection (admin only)"""
    result = await db.execute(
        select(Detection).where(Detection.id == detection_id)
    )
    detection = result.scalar_one_or_none()
    
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found"
        )
    
    # Store event_id before deletion
    event_id = detection.event_id
    
    await db.delete(detection)
    await db.commit()
    
    # Broadcast deletion event to all connected clients
    try:
        from app.core.websocket import manager
        await manager.broadcast({
            "type": "detection_deleted",
            "detection_id": detection_id,
            "event_id": event_id
        })
    except Exception as e:
        # Don't fail deletion if broadcast fails
        print(f"Failed to broadcast deletion: {e}")


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_detections(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Bulk delete detections (admin only)"""
    ids = payload.get("ids", [])
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No detection IDs provided"
        )
    
    deleted_count = 0
    deleted_events = []
    
    for detection_id in ids:
        result = await db.execute(
            select(Detection).where(Detection.id == detection_id)
        )
        detection = result.scalar_one_or_none()
        if detection:
            deleted_events.append({
                "detection_id": detection.id,
                "event_id": detection.event_id
            })
            await db.delete(detection)
            deleted_count += 1
    
    await db.commit()
    
    # Broadcast deletion events
    try:
        from app.core.websocket import manager
        for event in deleted_events:
            await manager.broadcast({
                "type": "detection_deleted",
                **event
            })
    except Exception:
        pass
    
    return {"deleted": deleted_count, "total_requested": len(ids)}