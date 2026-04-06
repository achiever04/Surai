"""
Watchlist management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import json
from loguru import logger

from app.db.session import get_db
from app.models.watchlist import WatchlistPerson
from app.models.user import User
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistResponse, WatchlistDetail
from app.api.deps import get_current_user, require_role
from app.services.watchlist_service import WatchlistService

router = APIRouter()

@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlist(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all watchlist persons with filters"""
    query = select(WatchlistPerson)
    
    if category:
        query = query.where(WatchlistPerson.category == category)
    
    if risk_level:
        query = query.where(WatchlistPerson.risk_level == risk_level)
    
    if is_active is not None:
        query = query.where(WatchlistPerson.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(WatchlistPerson.priority.desc())
    
    result = await db.execute(query)
    persons = result.scalars().all()
    
    return persons

@router.get("/{person_id}", response_model=WatchlistDetail)
async def get_watchlist_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get watchlist person by ID"""
    result = await db.execute(
        select(WatchlistPerson).where(WatchlistPerson.id == person_id)
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found in watchlist"
        )
    
    # PHOTO DISPLAY FIX: Load photos from local paths
    import base64
    import os
    photos = []
    
    # DEBUG: Log photo paths from database
    logger.info(f"[PHOTO DEBUG] Person {person_id} has {len(person.photos_local_paths or [])} photo paths in database")
    
    if person.photos_local_paths:
        for idx, photo_path in enumerate(person.photos_local_paths):
            logger.info(f"[PHOTO DEBUG] Photo {idx + 1}: {photo_path}")
            logger.info(f"[PHOTO DEBUG] File exists: {os.path.exists(photo_path)}")
            
            try:
                if os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        photo_data = base64.b64encode(f.read()).decode('utf-8')
                        data_uri = f"data:image/jpeg;base64,{photo_data}"
                        photos.append(data_uri)
                        logger.info(f"[PHOTO DEBUG] Successfully loaded photo {idx + 1} ({len(photo_data)} bytes)")
                else:
                    logger.warning(f"[PHOTO DEBUG] Photo file not found: {photo_path}")
            except Exception as e:
                logger.error(f"[PHOTO DEBUG] Failed to load photo {photo_path}: {e}")
    else:
        logger.warning(f"[PHOTO DEBUG] Person {person_id} has no photo paths in database")
    
    # CRITICAL FIX: Use Pydantic model to serialize, then add photos
    # person.__dict__ doesn't work properly with SQLAlchemy
    response = WatchlistDetail.from_orm(person)
    response_dict = response.dict()
    response_dict['photos'] = photos
    
    logger.info(f"[PHOTO DEBUG] Returning watchlist person {person_id} with {len(photos)} photos in response")
    logger.info(f"[PHOTO DEBUG] Response keys: {list(response_dict.keys())}")
    return response_dict

@router.post("/", status_code=status.HTTP_201_CREATED)
async def enroll_person(
    person_data: str = Form(...),  # JSON string from FormData
    photos: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """Enroll new person in watchlist with photos"""
    # Parse person data
    try:
        person_dict = json.loads(person_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in person_data"
        )
    
    # Check if person_id already exists
    result = await db.execute(
        select(WatchlistPerson).where(WatchlistPerson.person_id == person_dict["person_id"])
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person ID already exists"
        )
    
    # Use service to process enrollment
    service = WatchlistService(db)
    person = await service.enroll_person(person_dict, photos, current_user.username)
    
    # Build response with age validation info
    response = WatchlistResponse.from_orm(person)
    response_dict = response.dict()
    # AGE PROGRESSION: Include photo-detected age and warning
    response_dict["photo_detected_age"] = getattr(person, '_photo_detected_age', None)
    response_dict["age_warning"] = getattr(person, '_age_warning', None)
    
    return response_dict

@router.put("/{person_id}", response_model=WatchlistResponse)
async def update_watchlist_person(
    person_id: int,
    person_update: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """Update watchlist person"""
    result = await db.execute(
        select(WatchlistPerson).where(WatchlistPerson.id == person_id)
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    # Update fields
    update_data = person_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(person, field, value)
    
    person.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(person)
    
    return person

@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete person from watchlist"""
    result = await db.execute(
        select(WatchlistPerson).where(WatchlistPerson.id == person_id)
    )
    person = result.scalar_one_or_none()
    
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    
    await db.delete(person)
    await db.commit()

@router.get("/search/by-name")
async def search_by_name(
    name: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search watchlist by name"""
    result = await db.execute(
        select(WatchlistPerson)
        .where(WatchlistPerson.name.ilike(f"%{name}%"))
        .where(WatchlistPerson.is_active == True)
    )
    persons = result.scalars().all()
    
    return [p.to_dict() for p in persons]