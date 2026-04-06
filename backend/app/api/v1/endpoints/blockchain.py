"""
Blockchain query endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.blockchain_service import BlockchainService
from app.schemas.blockchain import ProvenanceQuery, ProvenanceResponse

router = APIRouter()

@router.get("/transactions")
async def get_blockchain_transactions(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent blockchain transactions from verified detections"""
    from sqlalchemy import select
    from app.models.detection import Detection
    
    # Query detections that have blockchain transaction IDs
    result = await db.execute(
        select(Detection)
        .where(Detection.blockchain_tx_id.isnot(None))
        .order_by(Detection.timestamp.desc())
        .limit(limit)
    )
    detections = result.scalars().all()
    
    # Convert detections to audit log format
    transactions = []
    for detection in detections:
        transactions.append({
            "tx_id": detection.blockchain_tx_id,
            "type": f"EVIDENCE_{detection.detection_type.upper()}" if detection.detection_type else "EVIDENCE_LOG",
            "timestamp": detection.timestamp.isoformat(),
            "asset_id": detection.event_id or f"EVT-{detection.id}",
            "status": "COMMITTED"
        })
    
    # If no blockchain transactions found, return empty list (not mock data)
    return transactions

@router.post("/provenance", response_model=ProvenanceResponse)
async def get_evidence_provenance(
    query: ProvenanceQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get evidence provenance from blockchain"""
    service = BlockchainService(db)
    return await service.get_evidence_provenance(query.event_id)

@router.post("/verify/{event_id}")
async def verify_evidence_blockchain(
    event_id: str,
    current_hash: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify evidence integrity using blockchain"""
    service = BlockchainService(db)
    is_valid = await service.verify_evidence_integrity(event_id, current_hash)
    
    return {
        "event_id": event_id,
        "is_valid": is_valid,
        "verified_at": datetime.now(timezone.utc).isoformat()
    }