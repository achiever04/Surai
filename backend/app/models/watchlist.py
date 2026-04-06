"""
Watchlist person model for persons of interest
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.core.timezone import utc_now
import enum

class PersonCategory(str, enum.Enum):
    MISSING = "missing"
    CRIMINAL = "criminal"
    VIP = "vip"
    PERSON_OF_INTEREST = "person_of_interest"
    EMPLOYEE = "employee"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WatchlistPerson(Base):
    __tablename__ = "watchlist_persons"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Personal information
    name = Column(String(200), nullable=False, index=True)
    alias = Column(JSON, nullable=True)  # List of known aliases
    age = Column(Integer, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    nationality = Column(String(50), nullable=True)
    
    # Physical description
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    hair_color = Column(String(50), nullable=True)
    eye_color = Column(String(50), nullable=True)
    distinguishing_marks = Column(Text, nullable=True)
    
    # Classification
    category = Column(String(50), nullable=False, index=True)
    risk_level = Column(String(20), nullable=False, default="low", index=True)
    priority = Column(Integer, default=5)  # 1-10, higher = more important
    
    # Biometric data
    face_embeddings = Column(JSON, nullable=False)  # List of 512-dim embeddings
    photo_hashes = Column(JSON, nullable=False)  # SHA-256 of enrollment photos
    num_photos = Column(Integer, default=0)
    gait_features = Column(JSON, nullable=True)
    voice_features = Column(JSON, nullable=True)
    
    # Storage
    photos_ipfs_cids = Column(JSON, nullable=True)
    photos_local_paths = Column(JSON, nullable=False)
    
    # Tracking
    last_seen_at = Column(DateTime, nullable=True, index=True)
    last_seen_location = Column(String(200), nullable=True)
    last_seen_camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    total_detections = Column(Integer, default=0)
    
    # Legal & Authorization
    authorization_ref = Column(String(200), nullable=True)  # Court order number, etc.
    authorization_document = Column(String(500), nullable=True)  # Path to document
    legal_notes = Column(Text, nullable=True)
    case_number = Column(String(100), nullable=True)
    enrolled_by = Column(String(100), nullable=False)
    approved_by = Column(String(100), nullable=True)
    
    # Validity
    enrolled_at = Column(DateTime, default=utc_now, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Blockchain
    blockchain_enrollment_tx = Column(String(100), nullable=True)
    blockchain_receipt = Column(JSON, nullable=True)
    
    # Alert settings
    alert_on_detection = Column(Boolean, default=True)
    alert_contacts = Column(JSON, nullable=True)  # List of email/phone numbers
    
    # Notes & Context
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    related_cases = Column(JSON, nullable=True)
    
    # Metadata (Renamed to avoid conflict)
    person_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    detections = relationship("Detection", back_populates="matched_person")
    last_seen_camera = relationship("Camera", foreign_keys=[last_seen_camera_id])
    
    def __repr__(self):
        return f"<WatchlistPerson(name={self.name}, category={self.category})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "name": self.name,
            "category": self.category,
            "risk_level": self.risk_level,
            "age": self.age,
            "gender": self.gender,
            "is_active": self.is_active,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "total_detections": self.total_detections
        }