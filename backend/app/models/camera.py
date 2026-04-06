"""
Camera model for surveillance camera management
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.core.timezone import utc_now

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    
    # Camera source
    source_type = Column(String(20), nullable=False)  # webcam, rtsp, file
    source_url = Column(String(500), nullable=False)  # "0" for webcam, rtsp://... for IP cam
    
    # Location
    location = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Configuration
    resolution_width = Column(Integer, default=1280)
    resolution_height = Column(Integer, default=720)
    fps = Column(Integer, default=10)
    
    # AI Processing settings
    enable_face_detection = Column(Boolean, default=True)
    enable_emotion_detection = Column(Boolean, default=True)
    enable_pose_estimation = Column(Boolean, default=True)
    enable_behavior_analysis = Column(Boolean, default=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Health monitoring
    health_status = Column(String(20), default="unknown")  # healthy, degraded, offline
    error_count = Column(Integer, default=0)
    last_error = Column(String(500), nullable=True)
    
    # Metadata (Renamed to avoid conflict)
    camera_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    detections = relationship("Detection", back_populates="camera", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Camera(id={self.id}, name={self.name}, type={self.source_type})>"