"""
Annotated camera stream endpoint - adds detection overlays to live video

This file provides an additional stream endpoint that runs the detection pipeline
and annotates frames with bounding boxes, labels, and confidence scores.

PERFORMANCE FIX: Uses the shared DetectionPipeline from model_manager
instead of creating its own duplicate pipeline.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.responses import StreamingResponse
from loguru import logger
import cv2
import time

from app.db.session import get_db
from app.models.camera import Camera
from app.utils.shared_camera import shared_camera_manager
from app.utils.frame_annotator import frame_annotator
from app.services.watchlist_service import WatchlistService
from ai_engine.model_manager import ai_model_manager
from app.services.detection_processor import detection_processor

router = APIRouter()


async def verify_stream_token(token: str = Query(...)):
    """Verify stream authentication token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided"
        )
    
    from app.core.security import decode_access_token
    
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return payload


@router.get("/{camera_id}/stream/annotated")
async def stream_camera_annotated(
    camera_id: int,
    show_detections: bool = Query(True, description="Show detection bounding boxes"),
    show_watchlist_ids: bool = Query(True, description="Show watchlist person IDs"),
    show_confidence: bool = Query(True, description="Show confidence scores"),
    show_emotion: bool = Query(True, description="Show emotion labels"),
    show_age: bool = Query(True, description="Show age estimates"),
    show_pose: bool = Query(True, description="Show pose skeleton"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_stream_token)
):
    """
    Stream camera feed with real-time detection annotations
    
    Annotations include:
    - Bounding boxes (green=face, yellow=watchlist match, red=weapon)
    - Person IDs for watchlist matches
    - Confidence scores
    - Emotion labels
    - Age estimates
    - Pose skeletons (optional)
    
    Query Parameters:
        show_detections: Enable/disable all detection overlays
        show_watchlist_ids: Show watchlist person ID and name
        show_confidence: Show confidence scores
        show_emotion: Show emotion labels
        show_age: Show age estimates
        show_pose: Show pose skeleton
    """
    # Get camera
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
    
    # Get watchlist embeddings for matching
    watchlist_service = WatchlistService(db)
    watchlist_persons = await watchlist_service.get_all_active()
    
    # Extract embeddings from watchlist persons
    # Note: face_embeddings is a JSON array, we use the first embedding
    watchlist_embeddings = []
    for p in watchlist_persons:
        if p.face_embeddings and len(p.face_embeddings) > 0:
            # Use first embedding from the array
            watchlist_embeddings.append((p.id, p.face_embeddings[0], p.name))
    
    logger.info(f"Loaded {len(watchlist_embeddings)} watchlist persons for matching")
    
    # PERFORMANCE FIX: Use shared pipeline from model_manager (same instance as detection_processor)
    # Previously: a separate pipeline was created here, causing all AI models to load TWICE.
    detection_pipeline = ai_model_manager.get_detection_pipeline()
    
    def generate_annotated_frames():
        """Generate annotated frames with detection results"""
        logger.info(f"=== ANNOTATED STREAM STARTED for camera {camera_id} ===")
        
        # Register stream
        camera_source = shared_camera_manager.register_stream(source)
        
        if not camera_source.is_opened():
            logger.error(f"Failed to open camera source: {source}")
            shared_camera_manager.unregister_stream(source)
            return
        
        # CRITICAL FIX: Wait for first frame to be available before starting stream
        # This prevents black feed while camera is initializing
        logger.info("Waiting for first frame from camera...")
        max_wait_seconds = 5
        wait_start = time.time()
        first_frame = None
        
        while time.time() - wait_start < max_wait_seconds:
            first_frame = camera_source.get_frame()
            if first_frame is not None:
                logger.info(f"First frame received after {time.time() - wait_start:.1f}s, starting stream")
                break
            time.sleep(0.05)  # 50ms polling interval
        
        if first_frame is None:
            logger.error(f"Timeout waiting for first frame after {max_wait_seconds}s")
            shared_camera_manager.unregister_stream(source)
            return
        
        frame_count = 0
        detection_count = 0
        last_detection_time = time.time()
        last_detection_result = None
        
        try:
            while True:
                frame = camera_source.get_frame()
                
                if frame is not None:
                    # CAMERA INDEPENDENCE: Periodically check if this specific camera
                    # was stopped (even when hardware is still alive for other cameras)
                    if frame_count > 0 and frame_count % 10 == 0:
                        if not detection_processor.is_camera_active(camera_id):
                            logger.info(f"Camera {camera_id} deactivated, ending annotated stream")
                            break
                    
                    # Read the latest detection result (free dict lookup + timestamp check).
                    # get_latest_result() returns None if no detection or if the cached
                    # result is older than RESULT_STALE_SECONDS (person left frame).
                    try:
                        dp_result = detection_processor.get_latest_result(camera_id)
                        if dp_result is not None:
                            # Fresh detection — update local copy for drawing
                            last_detection_result = dp_result
                        elif detection_processor.is_camera_active(camera_id):
                            # BBOX FIX: Camera is active but result is stale (person left).
                            # Clear the last detection result so bbox disappears.
                            last_detection_result = None
                        elif frame_count % 5 == 0:
                            # BBOX FIX: Processor is NOT active — run fallback detection.
                            fallback_result = detection_pipeline.process_frame(
                                frame,
                                watchlist_embeddings=watchlist_embeddings,
                                skip_motion_check=True
                            )
                            if fallback_result and (fallback_result.has_face or fallback_result.has_weapon):
                                last_detection_result = fallback_result
                            else:
                                last_detection_result = None
                        
                        if last_detection_result and frame_count % 50 == 0:
                            detection_count += 1
                            fps = 1 / max(0.001, (time.time() - last_detection_time))
                            logger.debug(f"Annotated stream FPS: {fps:.1f}")
                            last_detection_time = time.time()
                    
                    except Exception as e:
                        import traceback
                        tb_str = traceback.format_exc()
                        logger.error(f"Detection error: {e}\n{tb_str}")
                        last_detection_result = None
                    
                    # Annotate frame if detections enabled (use last detection result)
                    if show_detections and last_detection_result:
                        frame = frame_annotator.annotate_frame(
                            frame,
                            last_detection_result,
                            show_watchlist_ids=show_watchlist_ids,
                            show_confidence=show_confidence,
                            show_emotion=show_emotion,
                            show_age=show_age,
                            show_pose=show_pose
                        )
                    
                    # Encode as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        
                        # Yield in MJPEG format
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                        
                        frame_count += 1
                else:
                    # Exit if camera was stopped/released
                    # Check 1: Camera hardware was force-released (last camera on source)
                    if camera_source.is_stopped():
                        logger.info(f"Camera {camera_id} stopped, ending annotated stream")
                        break
                    # Check 2: Detection processor removed this camera (stop_camera called,
                    # but hardware not force-released because other cameras share the source)
                    if not detection_processor.is_camera_active(camera_id):
                        logger.info(f"Camera {camera_id} deactivated, ending annotated stream")
                        break
                    time.sleep(0.05)
                
                # Control frame rate (~30 FPS output for smooth tracking)
                time.sleep(0.033)
                
        except GeneratorExit:
            logger.info(f"Client disconnected from annotated stream {camera_id}")
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            shared_camera_manager.unregister_stream(source)
            logger.info(f"Annotated stream {camera_id} closed")
    
    return StreamingResponse(
        generate_annotated_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        }
    )
