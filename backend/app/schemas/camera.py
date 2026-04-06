"""
Pydantic schemas for Camera API
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    source_type: str = Field(..., pattern="^(webcam|rtsp|file)$")
    source_url: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class CameraCreate(CameraBase):
    resolution_width: int = Field(default=1280, ge=320, le=1920)
    resolution_height: int = Field(default=720, ge=240, le=1080)
    fps: int = Field(default=10, ge=1, le=30)

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    enable_face_detection: Optional[bool] = None
    enable_emotion_detection: Optional[bool] = None
    enable_pose_estimation: Optional[bool] = None
    enable_behavior_analysis: Optional[bool] = None

class CameraResponse(CameraBase):
    id: int
    is_active: bool
    is_online: bool
    health_status: str
    created_at: datetime
    last_seen: Optional[datetime]
    
    class Config:
        from_attributes = True

class CameraStats(BaseModel):
    camera_id: int
    total_detections: int
    detections_today: int
    uptime_percentage: float
    avg_fps: float