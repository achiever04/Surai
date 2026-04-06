"""
Evidence management endpoints
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.evidence import Evidence
from app.models.user import User
from app.api.deps import get_current_user, require_role
from app.services.evidence_service import EvidenceService
from app.core.timezone import utc_now

router = APIRouter()

@router.get("/{evidence_id}")
async def get_evidence(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get evidence by ID"""
    result = await db.execute(
        select(Evidence).where(Evidence.id == evidence_id)
    )
    evidence = result.scalar_one_or_none()
    
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found"
        )
    
    return evidence

@router.post("/{evidence_id}/verify")
async def verify_evidence_integrity(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "auditor"))
):
    """Verify evidence integrity"""
    service = EvidenceService(db)
    is_valid = await service.verify_integrity(evidence_id)
    
    return {
        "evidence_id": evidence_id,
        "is_valid": is_valid,
        "verified_by": current_user.username,
        "verified_at": utc_now().isoformat()
    }