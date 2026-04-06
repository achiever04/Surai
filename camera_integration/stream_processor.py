"""
Real-time stream processor for camera frames
"""
import asyncio
from typing import Optional, Dict, Any
import numpy as np
from datetime import datetime
from loguru import logger

from ai_engine.pipelines.detection_pipeline import DetectionPipeline, DetectionResult
from app.services.detection_service import DetectionService
from app.services.watchlist_service import WatchlistService
from app.services.notification_service import notification_service
from sqlalchemy.ext.asyncio import AsyncSession

class StreamProcessor:
    """Process camera frames for detections"""
    
    def __init__(
        self,
        db_session: AsyncSession,
        config: Dict[str, Any]
    ):
        self.db = db_session
        self.config = config
        
        # Initialize services
        self.detection_service = DetectionService(db_session)
        self.watchlist_service = WatchlistService(db_session)
        self.notification_service = notification_service
        
        # Initialize AI pipeline
        self.pipeline = DetectionPipeline(config)
        
        # Processing settings
        self.process_every_n = config.get('process_every_n', 3)
        self.frame_counters: Dict[int, int] = {}
        
        # Cache watchlist embeddings
        self.watchlist_cache = None
        self.cache_update_interval = 300  # 5 minutes
        self.last_cache_update = None
    
    async def process_frame(
        self,
        camera_id: int,
        frame: np.ndarray,
        frame_number: int
    ):
        """
        Process single frame from camera
        
        Args:
            camera_id: Camera ID
            frame: Frame image
            frame_number: Frame sequence number
        """
        # Initialize counter if needed
        if camera_id not in self.frame_counters:
            self.frame_counters[camera_id] = 0
        
        self.frame_counters[camera_id] += 1
        
        # Skip frames for performance
        if self.frame_counters[camera_id] % self.process_every_n != 0:
            return
        
        try:
            # Update watchlist cache if needed
            await self._update_watchlist_cache()
            
            # Run detection pipeline
            result = await self.pipeline.process_frame(
                frame,
                watchlist_embeddings=self.watchlist_cache,
                skip_motion_check=False
            )
            
            # Handle detection result
            if result and result.has_face:
                await self._handle_detection(camera_id, frame, result)
                
        except Exception as e:
            logger.error(f"Error processing frame from camera {camera_id}: {e}")
    
    async def _update_watchlist_cache(self):
        """Update cached watchlist embeddings"""
        now = datetime.utcnow()
        
        if (self.last_cache_update is None or
            (now - self.last_cache_update).seconds > self.cache_update_interval):
            
            logger.info("Updating watchlist cache")
            self.watchlist_cache = await self.watchlist_service.get_all_active_embeddings()
            self.last_cache_update = now
    
    async def _handle_detection(
        self,
        camera_id: int,
        frame: np.ndarray,
        result: DetectionResult
    ):
        """Handle detection result"""
        
        # Determine detection type
        detection_type = self._determine_detection_type(result)
        
        # Check if significant enough to save
        if not self._should_save_detection(result, detection_type):
            return
        
        # Encode frame as JPEG
        import cv2
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Prepare metadata
        metadata = {
            "face_bbox": list(result.face_bbox) if result.face_bbox else None,
            "face_embedding": result.face_embedding.tolist() if result.face_embedding is not None else None,
            "face_quality_score": result.face_quality_score,
            "is_real_face": result.is_real_face,
            "emotion": result.emotion,
            "age": result.age,
            "body_orientation": result.body_orientation,
            "action": result.action,
            "matched_person_id": result.matched_person_id,
            "behavior_tags": result.metadata.get("behavior_tags"),
            "pose_data": None
        }
        
        try:
            # Save detection
            detection = await self.detection_service.create_detection(
                camera_id=camera_id,
                detection_type=detection_type,
                confidence=result.confidence,
                frame_data=frame_bytes,
                metadata=metadata
            )
            
            logger.info(f"Detection saved: {detection.event_id} - {detection_type}")

            # Broadcast to WebSocket clients
            await notification_service.broadcast_detection({
                  "id": detection.id,
                  "event_id": detection.event_id,
                  "camera_id": detection.camera_id,
                  "detection_type": detection_type,
                  "confidence": result.confidence,
                  "timestamp": detection.timestamp.isoformat(),
                  "matched_person_id": result.matched_person_id
            })
            
            # Send alerts if watchlist match
            if result.matched_person_id:
                await self._send_watchlist_alert(detection, result)
                
        except Exception as e:
            logger.error(f"Failed to save detection: {e}")
    
    def _determine_detection_type(self, result: DetectionResult) -> str:
        """Determine detection type from result"""
        # DETECTION ACCURACY FIX: Weapon detection is highest priority
        if result.has_weapon:
            # Differentiate between actual weapons and suspicious objects
            actual_weapons = [w for w in result.weapons_detected if w.get('is_weapon', False)]
            if actual_weapons:
                return "weapon_detected"
            else:
                return "suspicious_object"
        elif result.matched_person_id:
            return "face_match"
        elif result.emotion in ["angry", "fear"]:
            return "emotion_alert"
        elif not result.is_real_face:
            return "spoof_attempt"
        elif result.has_face:
            return "face_detection"
        else:
            return "unknown"
    
    def _should_save_detection(
        self,
        result: DetectionResult,
        detection_type: str
    ) -> bool:
        """
        Determine if detection should be saved
        
        Args:
            result: Detection result
            detection_type: Type of detection
            
        Returns:
            True if should save
        """
        # DETECTION ACCURACY FIX: Always save weapon detections
        if result.has_weapon:
            return True
        
        # Always save watchlist matches
        if result.matched_person_id:
            return True
        
        # Save spoof attempts
        if not result.is_real_face:
            return True
        
        # Save high-quality faces with certain emotions
        if result.face_quality_score > 0.7 and result.emotion in ["angry", "fear", "surprise"]:
            return True
        
        # Save based on random sampling (1 in 100 frames)
        import random
        return random.random() < 0.01
    
    async def _send_watchlist_alert(
        self,
        detection,
        result: DetectionResult
    ):
        """Send alert for watchlist match"""
        try:
            # Get person details
            from sqlalchemy import select
            from app.models.watchlist import WatchlistPerson
            
            person_result = await self.db.execute(
                select(WatchlistPerson).where(
                    WatchlistPerson.id == result.matched_person_id
                )
            )
            person = person_result.scalar_one_or_none()
            
            if person and person.alert_on_detection:
                # Update last seen
                await self.watchlist_service.update_last_seen(
                    person.id,
                    detection.camera_id,
                    f"Camera {detection.camera_id}"
                )
                
                # Send notification
                await self.notification_service.notify_watchlist_match(
                    person_name=person.name,
                    camera_location=f"Camera {detection.camera_id}",
                    confidence=result.confidence
                )
                
                logger.info(f"Alert sent for watchlist match: {person.name}")
                
        except Exception as e:
            logger.error(f"Error sending watchlist alert: {e}")