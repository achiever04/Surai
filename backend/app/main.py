# ===== MODEL LOADING OPTIMIZATION =====
# These environment variables MUST be set before any TF/ONNX imports.
# They disable slow hardware probing, JIT compilation, and telemetry.
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')           # Suppress TF warnings
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')          # Disable oneDNN JIT (slow first-run)
os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '2')         # Limit TF per-op threads (prevents contention)
os.environ.setdefault('TF_NUM_INTEROP_THREADS', '1')         # Limit TF inter-op parallelism
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')          # Skip GPU probing (CPU-only system)
os.environ.setdefault('ONNXRUNTIME_DISABLE_TELEMETRY', '1')   # Disable ONNX telemetry
os.environ.setdefault('OMP_NUM_THREADS', str(max(1, os.cpu_count() - 1)))  # OpenMP threads
os.environ.setdefault('OPENBLAS_NUM_THREADS', str(max(1, os.cpu_count() - 1)))

# Enable ONNX graph optimization caching (must import before InsightFace)
try:
    import ai_engine.utils.onnx_optimize  # noqa: F401
except Exception:
    pass

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.core.exceptions import create_exception_handlers
from config.settings import settings
from app.db.session import engine
from app.db.base import Base
from app.services.notification_service import notification_service
from app.models import (user, camera, detection, watchlist, evidence, blockchain_receipt, fl_model, alert)

# Setup logging
logger = setup_logging()


def _background_preload():
    """Preload AI models in background so they're ready when user starts a camera."""
    import time
    try:
        logger.info("🚀 Background model preloading started...")
        start = time.time()
        from ai_engine.model_manager import ai_model_manager
        # Preload face recognizer (the blocking one — 69s → ~15s with cache)
        ai_model_manager.get_face_recognizer()
        # Preload detection pipeline (triggers face recognizer singleton)
        pipeline = ai_model_manager.get_detection_pipeline()
        # Trigger parallel loading of weapon/emotion/age/pose models
        if pipeline:
            pipeline.preload_models_background()
        elapsed = time.time() - start
        logger.info(f"✅ Background preloading completed in {elapsed:.1f}s")
    except Exception as e:
        logger.warning(f"Background preload failed (non-critical): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Surveillance Platform...")
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    
    # WEBSOCKET FIX: Register main event loop with detection_processor
    # This allows the detection thread (which runs on its own event loop)
    # to schedule WebSocket broadcasts on the main loop where connections live.
    try:
        import asyncio
        from app.services.detection_processor import detection_processor
        detection_processor.set_main_loop(asyncio.get_running_loop())
    except Exception as e:
        logger.warning(f"Could not register main loop with detection_processor: {e}")
    
    # Start background model preloading (non-blocking)
    import threading
    preload_thread = threading.Thread(target=_background_preload, daemon=True)
    preload_thread.start()
    
    logger.info("Application ready! AI models loading in background.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Stop any running detection processors
    try:
        from app.services.detection_processor import detection_processor
        # Cancel all active processing tasks
        for camera_id in list(detection_processor.active_cameras):
            try:
                await detection_processor.stop_processing(camera_id)
            except Exception as e:
                logger.debug(f"Error stopping camera {camera_id}: {e}")
    except Exception as e:
        logger.debug(f"Error during detection processor shutdown: {e}")
    
    # Release all camera resources
    from app.utils.shared_camera import shared_camera_manager
    shared_camera_manager.release_all()
    logger.info("All camera resources released")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Register custom exception handlers
for exc_class, handler in create_exception_handlers().items():
    app.add_exception_handler(exc_class, handler)

# CORS middleware — origins configurable via settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files for evidence thumbnails and snapshots
import os
os.makedirs("storage/local/evidence", exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="static_storage")

@app.get("/")
async def root():
    return {
        "message": "AI Surveillance Platform API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint — reports real status of critical services."""
    from app.db.session import get_db
    from sqlalchemy import text
    
    # Check database connectivity
    db_status = "unhealthy"
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            db_status = "healthy"
            break
    except Exception as e:
        db_status = f"unhealthy: {e}"
    
    # Check IPFS connectivity (best-effort)
    ipfs_status = "unknown"
    try:
        from app.utils.ipfs_client import IPFSClient
        client = IPFSClient()
        if client.available:
            ipfs_status = "healthy"
        else:
            ipfs_status = "unavailable"
    except Exception:
        ipfs_status = "unavailable"
    
    # Check blockchain service (mock check)
    blockchain_status = "mock_mode"
    try:
        from app.services.blockchain_service import BlockchainService
        # We can't instantiate without a DB session, so just check import
        blockchain_status = "available"
    except Exception:
        blockchain_status = "unavailable"
    
    overall = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall,
        "services": {
            "database": db_status,
            "ipfs": ipfs_status,
            "blockchain": blockchain_status,
        }
    }

@app.websocket("/ws/detections")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time detection updates"""
    await notification_service.connect_websocket(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Echo back or handle client commands
            if data == "ping":
                await websocket.send_json({"status": "pong"})
            else:
                await websocket.send_json({"status": "connected", "message": "Listening for detections"})
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        notification_service.disconnect_websocket(websocket)

if __name__ == "__main__":
    # IMPORTANT: reload=False is required when using AI detection
    # The heavy TensorFlow/InsightFace model loading causes issues with the reloader
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)