"""
Pydantic schemas for Detection API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DetectionBase(BaseModel):
    detection_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    emotion: Optional[str] = None

class DetectionCreate(DetectionBase):
    camera_id: int
    event_id: str
    clip_hash: str
    local_path: str

class DetectionUpdate(BaseModel):
    operator_action: Optional[str] = Field(None, pattern="^(dismissed|escalated|archived|investigating|verified|rejected)$")
    is_verified: Optional[bool] = None
    is_false_positive: Optional[bool] = None
    notes: Optional[str] = None

class DetectionResponse(DetectionBase):
    id: int
    event_id: str
    camera_id: int
    timestamp: datetime
    matched_person_id: Optional[int]
    is_verified: bool
    is_false_positive: bool
    operator_action: Optional[str]
    blockchain_tx_id: Optional[str]
    
    class Config:
        from_attributes = True

class DetectionDetail(DetectionResponse):
    face_bbox: Optional[List[float]]
    behavior_tags: Optional[List[str]]
    local_path: str
    thumbnail_path: Optional[str]
    notes: Optional[str]