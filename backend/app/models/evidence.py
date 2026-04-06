"""
Evidence metadata model for chain of custody
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.core.timezone import utc_now

class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Reference to detection event
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=False, index=True)
    
    # File information
    file_type = Column(String(20), nullable=False)  # video, image, audio
    file_format = Column(String(10), nullable=False)  # mp4, jpg, wav
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    
    # Storage
    local_path = Column(String(500), nullable=False)
    ipfs_cid = Column(String(100), nullable=True, index=True)
    backup_path = Column(String(500), nullable=True)
    
    # Blockchain
    blockchain_tx_id = Column(String(100), nullable=True, index=True)
    blockchain_receipt = Column(JSON, nullable=True)
    
    # Chain of custody
    chain_of_custody = Column(JSON, nullable=False)  # List of custody events
    
    # Status
    is_sealed = Column(Boolean, default=False)
    is_exported = Column(Boolean, default=False)
    export_count = Column(Integer, default=0)
    
    # Legal
    legal_hold = Column(Boolean, default=False)
    retention_until = Column(DateTime, nullable=True)
    
    # Metadata
    evidence_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    detection = relationship("Detection")
    
    def __repr__(self):
        return f""