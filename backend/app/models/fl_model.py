"""
Federated Learning model version tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Float
from datetime import datetime
from app.db.base import Base
from app.core.timezone import utc_now

class FLModel(Base):
    __tablename__ = "fl_models"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Version info
    version = Column(String(50), unique=True, index=True, nullable=False)
    epoch = Column(Integer, nullable=False, index=True)
    
    # Model details
    model_type = Column(String(50), nullable=False)  # face_recognition, behavior_classifier
    model_hash = Column(String(64), nullable=False)  # SHA-256 of model weights
    model_path = Column(String(500), nullable=False)
    model_size_bytes = Column(Integer, nullable=False)
    
    # Training metadata
    num_clients = Column(Integer, nullable=False)
    total_samples = Column(Integer, nullable=False)
    client_contributions = Column(JSON, nullable=False)  # {client_id: sample_count}
    
    # Performance metrics
    accuracy = Column(Float, nullable=True)
    loss = Column(Float, nullable=True)
    validation_metrics = Column(JSON, nullable=True)
    
    # Blockchain verification
    blockchain_tx_id = Column(String(100), nullable=True)
    blockchain_receipt = Column(JSON, nullable=True)
    update_receipts = Column(JSON, nullable=True)  # List of client update receipts
    
    # Status
    is_active = Column(Boolean, default=False)
    is_deployed = Column(Boolean, default=False)
    deployed_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    
    def __repr__(self):
        return f""