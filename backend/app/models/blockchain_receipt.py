"""
Blockchain receipt model for tracking on-chain transactions
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime, timezone
from app.db.base import Base

class BlockchainReceipt(Base):
    __tablename__ = "blockchain_receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    tx_id = Column(String(100), unique=True, index=True, nullable=False)
    tx_type = Column(String(50), nullable=False, index=True)  
    # Types: evidence_registration, watchlist_enrollment, custody_update, fl_update
    
    # Related entity
    entity_type = Column(String(50), nullable=False)  # detection, watchlist_person, evidence
    entity_id = Column(String(100), nullable=False, index=True)
    
    # Blockchain details
    channel_name = Column(String(100), nullable=False)
    chaincode_name = Column(String(100), nullable=False)
    function_name = Column(String(100), nullable=False)
    
    # Payload
    payload = Column(JSON, nullable=False)
    response = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, confirmed, failed
    confirmation_time = Column(DateTime(timezone=True), nullable=True)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f"<BlockchainReceipt(tx_id={self.tx_id}, type={self.tx_type}, status={self.status})>"