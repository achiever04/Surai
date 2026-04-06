"""
Camera management service
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate
from loguru import logger


class CameraService:
    """Service for camera management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[Camera]:
        """Get all cameras with optional filtering"""
        query = select(Camera)
        
        if is_active is not None:
            query = query.where(Camera.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(Camera.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_id(self, camera_id: int) -> Optional[Camera]:
        """Get camera by ID"""
        result = await self.db.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, camera_data: CameraCreate) -> Camera:
        """Create new camera"""
        camera = Camera(
            name=camera_data.name,
            source_type=camera_data.source_type,
            source_url=camera_data.source_url,
            location=camera_data.location,
            latitude=camera_data.latitude,
            longitude=camera_data.longitude,
            resolution_width=camera_data.resolution_width,
            resolution_height=camera_data.resolution_height,
            fps=camera_data.fps
        )
        
        self.db.add(camera)
        await self.db.commit()
        await self.db.refresh(camera)
        
        logger.info(f"Camera created: {camera.id} - {camera.name}")
        return camera
    
    async def update(
        self,
        camera_id: int,
        camera_data: CameraUpdate
    ) -> Optional[Camera]:
        """Update camera"""
        camera = await self.get_by_id(camera_id)
        
        if not camera:
            return None
        
        # Update fields
        update_data = camera_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(camera, field, value)
        
        camera.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(camera)
        
        logger.info(f"Camera updated: {camera.id}")
        return camera
    
    async def delete(self, camera_id: int) -> bool:
        """Delete camera"""
        camera = await self.get_by_id(camera_id)
        
        if not camera:
            return False
        
        await self.db.delete(camera)
        await self.db.commit()
        
        logger.info(f"Camera deleted: {camera_id}")
        return True
    
    async def start_camera(self, camera_id: int) -> bool:
        """Mark camera as active"""
        camera = await self.get_by_id(camera_id)
        
        if not camera:
            return False
        
        camera.is_active = True
        camera.is_online = True
        camera.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Camera started: {camera_id}")
        return True
    
    async def stop_camera(self, camera_id: int) -> bool:
        """Mark camera as inactive"""
        camera = await self.get_by_id(camera_id)
        
        if not camera:
            return False
        
        camera.is_active = False
        camera.is_online = False
        camera.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Camera stopped: {camera_id}")
        return True
    
    async def update_health_status(
        self,
        camera_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update camera health status"""
        camera = await self.get_by_id(camera_id)
        
        if not camera:
            return
        
        camera.health_status = status
        camera.last_seen = datetime.utcnow()
        
        if error_message:
            camera.error_count += 1
            camera.last_error = error_message
        else:
            camera.error_count = 0
            camera.last_error = None
        
        await self.db.commit()
    
    async def get_active_cameras(self) -> List[Camera]:
        """Get all active cameras"""
        result = await self.db.execute(
            select(Camera).where(Camera.is_active == True)
        )
        return result.scalars().all()
    
    async def get_online_cameras(self) -> List[Camera]:
        """Get all online cameras"""
        result = await self.db.execute(
            select(Camera).where(Camera.is_online == True)
        )
        return result.scalars().all()