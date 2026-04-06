"""
Pydantic schemas for Blockchain API
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class BlockchainReceiptResponse(BaseModel):
    tx_id: str
    tx_type: str
    entity_type: str
    entity_id: str
    status: str
    created_at: datetime
    confirmation_time: Optional[datetime]
    
    class Config:
        from_attributes = True

class ProvenanceQuery(BaseModel):
    event_id: str

class ProvenanceResponse(BaseModel):
    event_id: str
    clip_hash: str
    blockchain_tx_id: str
    anchored_at: datetime
    chain_of_custody: list
    is_verified: bool

class IntegrityVerification(BaseModel):
    event_id: str
    current_hash: str
    blockchain_hash: str
    is_valid: bool
    verified_at: datetime