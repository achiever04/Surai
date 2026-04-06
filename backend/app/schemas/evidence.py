"""
Pydantic schemas for Evidence API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvidenceBase(BaseModel):
    """Base evidence schema"""
    file_type: str = Field(..., pattern="^(video|image|audio)$")
    file_format: str


class EvidenceCreate(EvidenceBase):
    """Create evidence"""
    detection_id: int
    file_data: bytes
    local_path: str
    ipfs_cid: Optional[str] = None


class EvidenceResponse(EvidenceBase):
    """Evidence response"""
    id: int
    evidence_id: str
    detection_id: int
    file_size: int
    file_hash: str
    local_path: str
    ipfs_cid: Optional[str]
    blockchain_tx_id: Optional[str]
    is_sealed: bool
    is_exported: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class EvidenceDetail(EvidenceResponse):
    """Detailed evidence with chain of custody"""
    chain_of_custody: List[Dict[str, Any]]
    blockchain_receipt: Optional[Dict[str, Any]]
    legal_hold: bool
    retention_until: Optional[datetime]
    metadata: Optional[Dict[str, Any]]


class CustodyEvent(BaseModel):
    """Chain of custody event"""
    action: str
    actor: str
    timestamp: str
    location: Optional[str] = None
    notes: Optional[str] = None


class EvidenceVerification(BaseModel):
    """Evidence integrity verification result"""
    evidence_id: str
    is_valid: bool
    current_hash: str
    stored_hash: str
    verified_at: datetime
    verified_by: str


class EvidenceExport(BaseModel):
    """Evidence export request"""
    evidence_ids: List[int]
    format: str = "zip"
    include_metadata: bool = True
    include_blockchain_proof: bool = True