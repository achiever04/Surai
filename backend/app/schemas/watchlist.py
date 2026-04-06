"""
Pydantic schemas for Watchlist API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class WatchlistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(missing|criminal|vip|person_of_interest|employee)$")
    risk_level: str = Field(default="low", pattern="^(low|medium|high|critical)$")
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None

class WatchlistCreate(WatchlistBase):
    person_id: str = Field(..., min_length=1, max_length=50)
    authorization_ref: Optional[str] = None
    description: Optional[str] = None
    alert_on_detection: bool = True

class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    risk_level: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    alert_on_detection: Optional[bool] = None

class WatchlistResponse(WatchlistBase):
    id: int
    person_id: str
    is_active: bool
    enrolled_at: datetime
    last_seen_at: Optional[datetime]
    last_seen_location: Optional[str] = None
    last_seen_camera_id: Optional[int] = None
    total_detections: int
    blockchain_enrollment_tx: Optional[str]
    # Age progression: AI-detected age from enrollment photo
    photo_detected_age: Optional[int] = None
    age_warning: Optional[str] = None
    
    class Config:
        from_attributes = True

class WatchlistDetail(WatchlistResponse):
    alias: Optional[List[str]]
    description: Optional[str]
    notes: Optional[str]
    num_photos: int
    photos_local_paths: List[str]
    photos: Optional[List[str]] = []  # PHOTO DISPLAY FIX: Base64-encoded photos