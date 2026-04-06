"""
Camera management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.models.detection import Detection
from datetime import datetime, timezone
from loguru import logger
from app.db.session import get_db
from app.models.camera import Camera
from app.models.user import User
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse, CameraStats
from app.api.deps import get_current_user, require_role
import asyncio

# Import detection processor at module level to prevent lazy import blocking in threads
from app.services.detection_processor import detection_processor

router = APIRouter()

@router.get("/", response_model=List[CameraResponse])
async def get_cameras(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all cameras with optional filters"""
    query = select(Camera)
    
    if is_active is not None:
        query = query.where(Camera.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(Camera.id)
    
    result = await db.execute(query)
    cameras = result.scalars().all()
    
    return cameras

@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get camera by ID"""
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    return camera

@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_in: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """Create new camera"""
    camera = Camera(
        name=camera_in.name,
        source_type=camera_in.source_type,
        source_url=camera_in.source_url,
        location=camera_in.location,
        latitude=camera_in.latitude,
        longitude=camera_in.longitude,
        resolution_width=camera_in.resolution_width,
        resolution_height=camera_in.resolution_height,
        fps=camera_in.fps
    )
    
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    
    return camera

@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """Update camera configuration"""
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    # Update fields
    update_data = camera_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)
    
    camera.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(camera)
    
    return camera

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete camera"""
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    await db.delete(camera)
    await db.commit()

@router.get("/{camera_id}/stats", response_model=CameraStats)
async def get_camera_stats(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get camera statistics"""
    from app.models.detection import Detection
    from datetime import datetime, timedelta
    
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    # Total detections
    total_result = await db.execute(
        select(func.count(Detection.id)).where(Detection.camera_id == camera_id)
    )
    total_detections = total_result.scalar() or 0
    
    # Detections today
    today = datetime.utcnow().date()
    today_result = await db.execute(
        select(func.count(Detection.id))
        .where(Detection.camera_id == camera_id)
        .where(func.date(Detection.timestamp) == today)
    )
    detections_today = today_result.scalar() or 0
    
    return CameraStats(
        camera_id=camera_id,
        total_detections=total_detections,
        detections_today=detections_today,
        uptime_percentage=95.5,  # Calculate from health logs
        avg_fps=camera.fps * 0.9  # Estimate based on processing
    )

@router.post("/{camera_id}/start")
async def start_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """
    Start camera stream processing.
    This endpoint activates the camera in the database.
    AI detection starts in background thread to avoid blocking.
    """
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    try:
        # Update database status to active FIRST (fast operation)
        camera.is_active = True
        camera.is_online = True
        camera.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Camera {camera_id} activated successfully")
        
        # Start AI detection in a completely separate thread
        # This prevents the heavy TensorFlow import from blocking the event loop
        import threading
        
        def start_detection_background(cam_id, source):
            try:
                import asyncio
                # Import happens here in the thread, not blocking main loop
                from app.services.detection_processor import detection_processor
                
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(detection_processor.start_processing(cam_id, source))
                except Exception as e:
                    logger.warning(f"Detection processing error for camera {cam_id}: {e}")
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"Could not start detection for camera {cam_id}: {e}")
        
        source = int(camera.source_url) if camera.source_url.isdigit() else camera.source_url
        detection_thread = threading.Thread(
            target=start_detection_background,
            args=(camera_id, source),
            daemon=True
        )
        detection_thread.start()
        logger.info(f"Detection processor starting in background for camera {camera_id}")
        
        return {
            "message": f"Camera {camera_id} started successfully",
            "camera_id": camera_id,
            "status": "active"
        }
        
    except Exception as e:
        # Rollback database changes on error
        camera.is_active = False
        camera.is_online = False
        await db.commit()
        
        logger.error(f"Failed to start camera {camera_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start camera: {str(e)}"
        )

@router.post("/{camera_id}/stop")
async def stop_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "operator"))
):
    """
    Stop camera stream processing.
    This endpoint deactivates the camera in the database.
    
    NOTE: We do NOT release the shared camera hardware here because:
    1. Multiple cameras may share the same physical source (e.g., webcam 0)
    2. Stopping one camera should not affect other cameras using the same source
    3. Hardware is automatically released when ALL stream consumers disconnect
       (handled by SharedCameraSource.remove_consumer with delayed release)
    """
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    try:
        # Only update database status - do NOT release shared hardware
        # The shared camera source will be released automatically when
        # all stream consumers disconnect (via consumer counting mechanism)
        camera.is_active = False
        camera.is_online = False
        camera.updated_at = datetime.utcnow()
        await db.commit()
        
        # Stop AI detection processor for this specific camera
        try:
            from app.services.detection_processor import detection_processor
            # stop_processing is an async method, await it
            await detection_processor.stop_processing(camera_id)
            logger.info(f"Detection processor stopped for camera {camera_id}")
        except Exception as det_error:
            logger.warning(f"Could not stop detection processor for camera {camera_id}: {det_error}")
        
        # CAMERA INDEPENDENCE FIX: Only force-release hardware if NO other
        # active cameras share the same physical source.
        # Previously, force_release_source() killed ALL consumers (including
        # other cameras' streams), so stopping camera 2 also stopped camera 1.
        try:
            from app.utils.shared_camera import shared_camera_manager
            source = int(camera.source_url) if camera.source_url.isdigit() else camera.source_url
            
            # Check if any OTHER active camera uses the same source
            other_cameras_on_same_source = await db.execute(
                select(Camera).where(
                    Camera.source_url == camera.source_url,
                    Camera.id != camera_id,
                    Camera.is_active == True
                )
            )
            other_active = other_cameras_on_same_source.scalars().first()
            
            if other_active:
                # Other cameras still using this source — just remove THIS camera's
                # consumer. The hardware stays alive for the remaining cameras.
                shared_camera_manager.unregister_stream(source)
                logger.info(f"Camera {camera_id} consumer removed (other cameras still using source)")
            else:
                # This is the LAST camera on this source — force-release hardware
                shared_camera_manager.force_release_source(source)
                logger.info(f"Camera hardware force-released for camera {camera_id} (last user of source)")
        except Exception as hw_error:
            logger.warning(f"Could not release camera hardware for camera {camera_id}: {hw_error}")
        
        logger.info(f"Camera {camera_id} fully stopped (database + detection + hardware)")
        
        return {
            "message": f"Camera {camera_id} stopped successfully",
            "camera_id": camera_id,
            "status": "inactive"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop camera {camera_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop camera: {str(e)}"
        )

from typing import Optional

async def verify_stream_token(token: Optional[str] = Query(None)):
    """Verify token for camera stream (since img tags can't use headers)"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )
    
    from app.core.security import decode_access_token
    from app.models.user import User
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return payload

@router.get("/{camera_id}/stream")
async def stream_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_stream_token)
):
    """Stream camera feed (MJPEG) - supports multiple streams from same source"""
    from starlette.responses import StreamingResponse
    from app.utils.shared_camera import shared_camera_manager
    import cv2
    import time
    
    result = await db.execute(
        select(Camera).where(Camera.id == camera_id)
    )
    camera = result.scalar_one_or_none()
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    # Parse source
    source = int(camera.source_url) if camera.source_url.isdigit() else camera.source_url
    
    def generate_frames():
        """Generate frames for MJPEG stream using shared camera manager"""
        logger.info(f"=== STREAM STARTED for camera {camera_id} (source: {source}) ===")
        
        # Register this stream with the shared manager
        camera_source = shared_camera_manager.register_stream(source)
        
        if not camera_source.is_opened():
            logger.error(f"Failed to open camera source: {source}")
            shared_camera_manager.unregister_stream(source)
            return
        
        frame_count = 0
        last_frame_time = time.time()
        
        try:
            consecutive_none_frames = 0
            while True:
                frame = camera_source.get_frame()
                
                if frame is not None:
                    consecutive_none_frames = 0
                    # Encode as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        
                        # Yield in MJPEG format
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                        
                        frame_count += 1
                        if frame_count % 100 == 0:
                            fps = 100 / (time.time() - last_frame_time)
                            logger.debug(f"Camera {camera_id} streaming at {fps:.1f} FPS")
                            last_frame_time = time.time()
                else:
                    consecutive_none_frames += 1
                    # CAMERA LIFECYCLE FIX: If camera was stopped/released,
                    # get_frame() returns None permanently. Exit the loop.
                    if camera_source.is_stopped() or consecutive_none_frames > 50:
                        logger.info(f"Camera {camera_id} stopped, ending stream")
                        break
                    # Otherwise just a brief gap in frames, wait a bit
                    time.sleep(0.05)
                
                # Control frame rate (~15 FPS output)
                time.sleep(0.066)
                
        except GeneratorExit:
            logger.info(f"Client disconnected from camera {camera_id}")
        finally:
            shared_camera_manager.unregister_stream(source)
            logger.info(f"Camera {camera_id} stream closed")
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        }
    )