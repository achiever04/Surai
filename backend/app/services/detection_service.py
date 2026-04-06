"""
Detection service for managing detection events
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import cv2
import numpy as np
from loguru import logger
from app.models.detection import Detection
from app.models.camera import Camera
from app.services.evidence_service import EvidenceService
from app.utils.ipfs_client import IPFSClient

class DetectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evidence_service = EvidenceService(db)
        self.ipfs_client = IPFSClient()
        self.storage_path = Path("storage/local/evidence")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def create_detection(
        self,
        camera_id: int,
        detection_type: str,
        confidence: float,
        frame_data: bytes,
        metadata: Dict[str, Any]
    ) -> Detection:
        """
        Create new detection event with evidence storage
        """
        # Generate event ID
        timestamp = datetime.utcnow()
        event_id = f"evt_{timestamp.strftime('%Y%m%d_%H%M%S')}_{camera_id}"
        
        # Compute clip hash
        clip_hash = hashlib.sha256(frame_data).hexdigest()
        
        # Save evidence locally
        camera_folder = self.storage_path / f"camera_{camera_id}"
        camera_folder.mkdir(exist_ok=True)
        
        date_folder = camera_folder / timestamp.strftime("%Y%m%d")
        date_folder.mkdir(exist_ok=True)
        
        clip_filename = f"{event_id}.jpg"
        local_path = date_folder / clip_filename
        
        with open(local_path, "wb") as f:
            f.write(frame_data)
        
        # Upload to IPFS (optional)
        ipfs_cid = None
        try:
            ipfs_cid = await self.ipfs_client.add_file(frame_data)
        except Exception as e:
            print(f"IPFS upload failed: {e}")
        
        # Create thumbnail
        thumbnail_path = await self._create_thumbnail(frame_data, date_folder, event_id)
        
        # Create detection record
        detection = Detection(
            event_id=event_id,
            camera_id=camera_id,
            timestamp=timestamp,
            detection_type=detection_type,
            confidence=confidence,
            clip_hash=clip_hash,
            clip_size_bytes=len(frame_data),
            ipfs_cid=ipfs_cid,
            local_path=str(local_path),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            face_bbox=metadata.get("face_bbox"),
            face_embedding=metadata.get("face_embedding"),
            face_quality_score=metadata.get("face_quality_score"),
            is_real_face=metadata.get("is_real_face", True),
            behavior_tags=metadata.get("behavior_tags"),
            pose_data=metadata.get("pose_data"),
            emotion=metadata.get("emotion"),
            matched_person_id=metadata.get("matched_person_id")
        )
        
        self.db.add(detection)
        await self.db.commit()
        await self.db.refresh(detection)
        
        # Anchor to blockchain (async task)
        # await self._anchor_to_blockchain(detection)
        
        return detection
    
    async def _create_thumbnail(
        self,
        frame_data: bytes,
        folder: Path,
        event_id: str
    ) -> Optional[Path]:
        """Create thumbnail from frame"""
        try:
            # Decode image
            nparr = np.frombuffer(frame_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Resize to thumbnail
            h, w = img.shape[:2]
            max_dim = 320
            
            if max(h, w) > max_dim:
                if h > w:
                    new_h = max_dim
                    new_w = int(w * (max_dim / h))
                else:
                    new_w = max_dim
                    new_h = int(h * (max_dim / w))
                
                thumb = cv2.resize(img, (new_w, new_h))
            else:
                thumb = img
            
            # Save thumbnail
            thumb_path = folder / f"{event_id}_thumb.jpg"
            cv2.imwrite(str(thumb_path), thumb)
            
            return thumb_path
        except Exception as e:
            print(f"Thumbnail creation failed: {e}")
            return None
    
    async def _anchor_to_blockchain(self, detection: Detection):
        """
        Anchor detection to blockchain (placeholder)
        """
        # TODO: Implement blockchain integration
        pass
    
    async def get_detection_by_event_id(self, event_id: str) -> Optional[Detection]:
        """Get detection by event ID"""
        result = await self.db.execute(
            select(Detection).where(Detection.event_id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def mark_as_verified(
        self,
        detection_id: int,
        operator_id: int,
        is_false_positive: bool = False
    ):
        """Mark detection as verified by operator"""
        result = await self.db.execute(
            select(Detection).where(Detection.id == detection_id)
        )
        detection = result.scalar_one_or_none()
        
        if detection:
            detection.is_verified = True
            detection.is_false_positive = is_false_positive
            detection.operator_id = operator_id
            detection.action_timestamp = datetime.utcnow()
            
            await self.db.commit()