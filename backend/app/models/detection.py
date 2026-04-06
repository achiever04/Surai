"""
Detection model for all detection events
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # References
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    matched_person_id = Column(Integer, ForeignKey("watchlist_persons.id"), nullable=True, index=True)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    
    # Detection type
    detection_type = Column(String(50), nullable=False, index=True)  
    # Types: face_match, suspicious_behavior, emotion_alert, loitering, intrusion
    confidence = Column(Float, nullable=False)
    
    # Face recognition data
    face_bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    face_embedding = Column(JSON, nullable=True)  # 512-dim vector as JSON array
    face_quality_score = Column(Float, nullable=True)
    is_real_face = Column(Boolean, default=True)  # Anti-spoofing result
    
    # Behavior analysis
    behavior_tags = Column(JSON, nullable=True)  # ["loitering", "running", "fighting"]
    pose_data = Column(JSON, nullable=True)  # Pose keypoints
    emotion = Column(String(20), nullable=True)  # happy, sad, angry, neutral, etc.
    gait_features = Column(JSON, nullable=True)
    
    # Evidence storage
    clip_hash = Column(String(64), nullable=False)  # SHA-256 of video clip
    clip_size_bytes = Column(Integer, nullable=True)
    ipfs_cid = Column(String(100), nullable=True)
    local_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    
    # Blockchain anchoring
    blockchain_tx_id = Column(String(100), nullable=True, index=True)
    blockchain_receipt = Column(JSON, nullable=True)
    anchored_at = Column(DateTime, nullable=True)
    
    # Operator actions
    is_verified = Column(Boolean, default=False)
    is_false_positive = Column(Boolean, default=False)
    operator_action = Column(String(50), nullable=True)  # dismissed, escalated, archived, investigating
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_timestamp = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Alert status
    alert_sent = Column(Boolean, default=False)
    alert_recipients = Column(JSON, nullable=True)
    
    # Additional metadata
    detection_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    camera = relationship("Camera", back_populates="detections")
    matched_person = relationship("WatchlistPerson", back_populates="detections")
    operator = relationship("User", foreign_keys=[operator_id])
    
    def __repr__(self):
        return f""
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "detection_type": self.detection_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "matched_person_id": self.matched_person_id,
            "emotion": self.emotion,
            "is_verified": self.is_verified,
            "operator_action": self.operator_action
        }