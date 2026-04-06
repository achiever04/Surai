"""
Federated Learning endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.fl_model import FLModel
from app.api.deps import get_current_user, require_role

router = APIRouter()

@router.get("/models")
async def get_fl_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all FL model versions"""
    result = await db.execute(
        select(FLModel).order_by(FLModel.created_at.desc())
    )
    models = result.scalars().all()
    return models

@router.get("/models/{version}")
async def get_fl_model(
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific FL model version"""
    result = await db.execute(
        select(FLModel).where(FLModel.version == version)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found"
        )
    
    return model

@router.get("/active")
async def get_active_model(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get currently active FL model"""
    result = await db.execute(
        select(FLModel)
        .where(FLModel.is_active == True)
        .order_by(FLModel.created_at.desc())
    )
    model = result.scalars().first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active model found"
        )
    
    return model

@router.post("/start-training")
async def start_fl_training(
    num_rounds: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Start federated learning training round"""
    # TODO: Implement FL training initiation
    return {
        "message": "FL training started",
        "num_rounds": num_rounds,
        "started_by": current_user.username
    }