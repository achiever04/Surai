"""
Alert model for critical detection events (weapons, aggressive poses)
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey
from app.db.base import Base
from datetime import datetime
from app.core.timezone import utc_now


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=True)
    alert_type = Column(String(50), nullable=False, index=True)  # weapon_detected, aggressive_pose
    severity = Column(String(20), nullable=False, default="high")  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=True)
    camera_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    is_acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    # Renamed from 'metadata' to avoid SQLAlchemy 2.x reserved attribute conflict
    alert_metadata = Column("metadata", JSON, nullable=True)

