"""
Detection Processor Service

Runs AI detection on camera frames in the background and broadcasts results via WebSocket.
This service operates independently of stream viewers, processing frames continuously
when cameras are active.
"""
import asyncio
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone, timedelta

import cv2
import numpy as np
from loguru import logger
from ai_engine.pipelines.detection_pipeline import DetectionResult, FaceData
from ai_engine.model_manager import ai_model_manager
from app.services.notification_service import notification_service
from app.utils.shared_camera import shared_camera_manager


class DetectionProcessor:
    """
    Background processor that runs AI detection on camera frames.
    Operates as a singleton, processing frames from active cameras.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Pipeline configuration (OPTIMIZED for performance!)
        # Models lazy-load on first use to minimize startup time
        self.pipeline_config = {
            'enable_emotion_detection': True,  # ENABLED - User requested
            'enable_pose_estimation': True,  # RE-ENABLED (thread-safe now with static_image_mode=True)
            'enable_anti_spoof': False,  # Disabled (causes crashes)
            'enable_age_estimation': True,  # ENABLED - User requested
            'enable_weapon_detection': True  # Enabled for crime prevention
        }
        
        # Processing state
        self.active_cameras: Set[int] = set()
        self.processing_tasks: Dict[int, asyncio.Task] = {}
        self.is_running = False
        
        # --- TWO-TIER TRACKING ARCHITECTURE ---
        # Tier 1 (tracking): runs detect_faces_only() every frame (~30ms)
        #   → updates bbox positions continuously for smooth annotated stream
        # Tier 2 (full detection): runs full pipeline + DB save
        #   → only when a NEW person/object appears or on periodic refresh
        
        # Cached detection results for the annotated stream
        self._latest_results: Dict[int, DetectionResult] = {}
        self._latest_results_time: Dict[int, float] = {}  # timestamp of last tracking update
        self._latest_results_lock = threading.Lock()
        
        # Full detection result (with embedding, emotion, etc.) — used to
        # enrich the tracking-only bbox with metadata (watchlist name, emotion label)
        self._full_detection_result: Dict[int, DetectionResult] = {}
        
        # Track whether a full detection has been saved for the current "session".
        # A session = continuous presence of at least one face/weapon in the frame.
        # Once the frame is empty for RESULT_STALE_SECONDS, session resets.
        self._detection_saved: Dict[int, bool] = {}
        
        # PRESENCE-BASED ALERT SUPPRESSION
        # Tracks when each alert entity was last seen. An alert fires only
        # when the entity has been absent for > SESSION_GAP_SECONDS.
        # key = alert_key (str), value = last_seen unix timestamp (float)
        self._alert_presence: Dict[str, float] = {}
        
        # BBOX LIFECYCLE: How long (seconds) a cached tracking result stays valid.
        # After this time with NO face/weapon in frame, bbox disappears.
        self.RESULT_STALE_SECONDS = 2.0
        
        # RE-DETECTION: Track when we last saw any detection per camera.
        # When a person/object leaves for SESSION_GAP_SECONDS and returns,
        # we reset the session so a new detection is saved to DB.
        self._last_seen_time: Dict[int, float] = {}
        self.SESSION_GAP_SECONDS = 10.0  # Gap threshold to reset session (must exceed full-detection time)
        
        # FULL DETECTION INTERVAL: How often (seconds) to run the full pipeline
        # even if a detection has already been saved (refreshes emotion/age/pose).
        self.FULL_DETECTION_INTERVAL = 1.5
        self._last_full_detection_time: Dict[int, float] = {}
        
        # WEBSOCKET FIX: Store reference to main event loop
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Watchlist cache
        self.watchlist_cache = None
        self.cache_update_time = None
        self.cache_ttl = 300  # 5 minutes
        
        # DB save cooldown (prevents spamming DB for same person in frame)
        self.last_detection_time: Dict[int, datetime] = {}
        self.detection_cooldown = 5.0  # Only save to DB every 5s per camera
        
        # Thread pool for offloading DB saves (non-blocking)
        self._db_save_executor = None
        
        # One-at-a-time flag: prevents task queue buildup in executor
        # Without this, tasks queue every 1.5s and 100+ pile up after camera stop
        self._full_det_running: Dict[int, bool] = {}
        
        # ============================================
        # WEAPON BACKGROUND THREAD STATE
        # ============================================
        # Weapon YOLO runs in a separate thread so it doesn't block
        # Tier 1 face tracking (~30ms). YOLO takes 2-5s per frame on CPU.
        self._weapon_thread: Optional[threading.Thread] = None
        self._weapon_stop_event = threading.Event()
        self._weapon_frame_lock = threading.Lock()
        self._weapon_latest_frame: Optional[np.ndarray] = None
        self._weapon_result_lock = threading.Lock()
        self._weapon_cached_result: Optional[list] = None  # List of weapon dicts
        self._weapon_result_time: float = 0.0
        self._weapon_stale_seconds: float = 3.5  # bbox disappears 3.5s after last COCO hit
        # WEAPON TRACKING: OpenCV tracker for smooth bbox updates between YOLO runs
        self._weapon_tracker_lock = threading.Lock()  # Protects _weapon_trackers
        self._weapon_trackers: list = []  # List of (tracker, bbox) tuples
        self._weapon_tracker_initialized: bool = False
        
        self._initialized = True
        logger.info("DetectionProcessor initialized")
    
    @property
    def pipeline(self):
        """Get shared AI pipeline from model manager (thread-safe singleton).
        
        PERFORMANCE FIX: Previously this created its OWN DetectionPipeline,
        causing all AI models to load twice (once here, once in annotated stream).
        Now both consumers share the same pipeline via model_manager.
        """
        return ai_model_manager.get_detection_pipeline(self.pipeline_config)
    
    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        """Store reference to main event loop for cross-thread WebSocket broadcasts."""
        self._main_loop = loop
        logger.info("DetectionProcessor: main event loop reference stored")
    
    def get_latest_result(self, camera_id: int) -> Optional[DetectionResult]:
        """Get the latest tracking result for a camera (thread-safe).
        
        Returns the cached result if fresh (within RESULT_STALE_SECONDS).
        This is updated at ~30 FPS by the tracking tier, so bbox positions
        are always smooth and up-to-date.
        """
        import time as _time
        with self._latest_results_lock:
            result = self._latest_results.get(camera_id)
            if result is None:
                return None
            result_time = self._latest_results_time.get(camera_id, 0)
            age = _time.time() - result_time
            if age > self.RESULT_STALE_SECONDS:
                # Result is stale — person probably left frame
                # Reset session so next appearance triggers new detection save
                self._detection_saved.pop(camera_id, None)
                self._full_detection_result.pop(camera_id, None)
                return None
            return result
    
    async def start_processing(self, camera_id: int, source):
        """
        Start processing frames from a camera for AI detection.
        This method runs the processing loop directly - it blocks until camera stops.
        
        Args:
            camera_id: Database camera ID
            source: Camera source (int for webcam index, string for RTSP URL)
        """
        logger.info(f"🚀 START_PROCESSING CALLED for camera {camera_id}, source: {source}")
        if camera_id in self.active_cameras:
            logger.warning(f"Camera {camera_id} already being processed")
            return
        
        # Register as consumer with shared camera manager to access frames
        logger.info(f"📹 Registering with shared camera manager for camera {camera_id}...")
        camera_source = shared_camera_manager.register_stream(source)
        logger.info(f"✅ Registered! Checking if opened...")
        if not camera_source.is_opened():
            logger.error(f"Failed to open camera source for AI detection: {source}")
            shared_camera_manager.unregister_stream(source)
            return
        
        # Store the source for cleanup
        if not hasattr(self, 'camera_sources'):
            self.camera_sources = {}
        self.camera_sources[camera_id] = source
        
        self.active_cameras.add(camera_id)
        logger.info(f"Starting AI detection for camera {camera_id} (source: {source})")
        
        # Run the processing loop directly - this blocks until camera is stopped
        # This is intentional because we're called from a background thread
        try:
            await self._process_camera_frames(camera_id, source)
        except asyncio.CancelledError:
            logger.info(f"Detection cancelled for camera {camera_id}")
        except Exception as e:
            logger.error(f"Detection error for camera {camera_id}: {e}")
        finally:
            # Cleanup when processing ends
            self.active_cameras.discard(camera_id)
            # Clean up latest result AND timestamp for this camera
            with self._latest_results_lock:
                self._latest_results.pop(camera_id, None)
                self._latest_results_time.pop(camera_id, None)
            if hasattr(self, 'camera_sources') and camera_id in self.camera_sources:
                shared_camera_manager.unregister_stream(source)
                del self.camera_sources[camera_id]
            logger.info(f"AI detection ended for camera {camera_id}")
    
    async def stop_processing(self, camera_id: int):
        """Stop processing frames from a camera.
        
        This removes the camera from active_cameras set AND signals
        background model loading to stop ONLY if no other cameras are active.
        """
        if camera_id in self.active_cameras:
            self.active_cameras.discard(camera_id)
            # Clean up ALL cached state for this camera
            with self._latest_results_lock:
                self._latest_results.pop(camera_id, None)
                self._latest_results_time.pop(camera_id, None)
            self._full_detection_result.pop(camera_id, None)
            self._detection_saved.pop(camera_id, None)
            self._last_full_detection_time.pop(camera_id, None)
            self._last_seen_time.pop(camera_id, None)
            self.last_detection_time.pop(camera_id, None)
            # CRITICAL FIX: Only stop background model loading if NO cameras remain.
            # Since the pipeline is a shared singleton, calling request_stop()
            # while other cameras are still active would kill their model loading too.
            if len(self.active_cameras) == 0:
                try:
                    self.pipeline.request_stop()
                except Exception:
                    pass  # Pipeline may not exist yet
            logger.info(f"Signal sent to stop AI detection for camera {camera_id}")
    
    async def _process_camera_frames(self, camera_id: int, source):
        """
        TWO-TIER detection loop:
        
        Tier 1 (TRACKING — every frame, ~30ms):
          Runs detect_faces_only() to update bbox positions.
          Bboxes appear within 1-2 frames and track smoothly.
        
        Tier 2 (FULL DETECTION — on new person/object):
          Runs full pipeline (embed, match, emotion, pose, DB save).
          Only triggers when a new face/weapon first appears.
          DB save runs in background thread to avoid blocking tracking.
        """
        import time as _time
        import concurrent.futures
        
        frame_counter = 0
        
        try:
            # Initialize pipeline (loads InsightFace face recognizer)
            try:
                logger.info(f"Initializing AI pipeline for camera {camera_id}...")
                pipeline = self.pipeline
                logger.info(f"AI pipeline ready for camera {camera_id} (face detection active)")
                
                # Start loading heavy models in background (non-blocking)
                pipeline.preload_models_background()
                logger.info(f"Heavy models loading in background for camera {camera_id}...")
            except Exception as e:
                logger.error(f"Failed to initialize AI pipeline for camera {camera_id}: {e}")
                return
            
            # Create thread pool for background tasks.
            # Low Memory Mode: cap at 1 worker to minimise RAM pressure.
            if self._db_save_executor is None:
                from config.config_manager import config_manager as _cm
                _max_workers = 1 if _cm.get().low_memory_mode else 2
                if _cm.get().low_memory_mode:
                    logger.info("⚠️  Low Memory Mode active — executor capped at 1 worker")
                self._db_save_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=_max_workers, thread_name_prefix="db-save"
                )
            
            # Preload watchlist cache once at startup
            self._update_watchlist_cache_sync()
            
            logger.info(f"Starting TWO-TIER detection loop for camera {camera_id}")
            
            # Start weapon detection background thread
            self._start_weapon_thread(camera_id, source)
            
            # Frame-skip counter: controlled by live config (0 = process every frame)
            _skip_counter: int = 0

            while camera_id in self.active_cameras:
                # Get frame from shared camera manager
                frame = shared_camera_manager.get_frame(source)

                if frame is None:
                    await asyncio.sleep(0.05)
                    continue

                frame_counter += 1

                # ── Frame Skip (Tier 1 tracking only) ────────────────────
                # Read live config each loop so UI changes take effect without
                # restart. skip=0 means process every frame.
                _frame_skip = __import__(
                    'config.config_manager', fromlist=['config_manager']
                ).config_manager.get().frame_skip
                if _frame_skip > 0:
                    _skip_counter += 1
                    if _skip_counter <= _frame_skip:
                        # Feed weapon thread anyway (it runs independently)
                        with self._weapon_frame_lock:
                            self._weapon_latest_frame = frame
                        await asyncio.sleep(0.01)
                        continue
                    _skip_counter = 0
                
                # Feed latest frame to weapon thread (non-blocking)
                with self._weapon_frame_lock:
                    self._weapon_latest_frame = frame
                
                # Log every 100th frame
                if frame_counter % 100 == 0:
                    logger.debug(f"Camera {camera_id}: Processed {frame_counter} frames")
                
                # ==========================================
                # TIER 1: FAST TRACKING (~30ms per frame)
                # ==========================================
                # Runs InsightFace.detect() ONLY (no weapon YOLO).
                # Weapon bboxes come from the background thread cache.
                try:
                    tracking_result = pipeline.detect_faces_only(frame)
                    
                    # Merge cached weapon results into tracking result
                    tracking_result = self._merge_weapon_cache(tracking_result, frame)
                    
                    if tracking_result and (tracking_result.has_face or tracking_result.has_weapon):
                        # RE-DETECTION: Check if person/weapon returned after a gap.
                        # If they left for > SESSION_GAP_SECONDS and came back,
                        # reset the session so a new detection gets saved.
                        now = _time.time()
                        last_seen = self._last_seen_time.get(camera_id, 0)
                        gap = now - last_seen if last_seen > 0 else 0
                        
                        if last_seen > 0 and gap > self.SESSION_GAP_SECONDS:
                            # Person/weapon returned after a gap → new session
                            self._detection_saved[camera_id] = False
                            self._full_detection_result.pop(camera_id, None)
                            self._last_full_detection_time.pop(camera_id, None)
                            logger.info(f"🔄 Session reset for camera {camera_id} (gap: {gap:.1f}s)")
                        
                        self._last_seen_time[camera_id] = now
                        
                        # Merge tracking bbox with full detection metadata
                        # (so the displayed bbox shows watchlist name, emotion, etc.)
                        enriched = self._merge_tracking_with_full(
                            camera_id, tracking_result
                        )
                        
                        with self._latest_results_lock:
                            self._latest_results[camera_id] = enriched
                            self._latest_results_time[camera_id] = now
                        
                        # ==========================================
                        # TIER 2: FULL DETECTION (NON-BLOCKING)
                        # ==========================================
                        # Runs in a background thread so tracking is NOT frozen.
                        # Previously this blocked the async loop for 3+ seconds,
                        # causing bboxes to disappear and session resets every 3s.
                        needs_full = self._needs_full_detection(camera_id)
                        
                        if needs_full and not self._full_det_running.get(camera_id, False):
                            # Mark as "in progress" immediately to prevent re-triggering
                            self._last_full_detection_time[camera_id] = now
                            self._full_det_running[camera_id] = True
                            frame_snapshot = frame.copy()
                            loop = asyncio.get_event_loop()
                            loop.run_in_executor(
                                self._db_save_executor,
                                self._full_detection_in_background,
                                camera_id, frame_snapshot
                            )
                    else:
                        # No face/weapon in frame — tracking result is None.
                        # Don't clear cache immediately; let RESULT_STALE_SECONDS handle it.
                        pass
                        
                except Exception as e:
                    logger.error(f"Tracking error on camera {camera_id}: {e}", exc_info=True)
                
                # Rate limit: ~30 FPS tracking
                await asyncio.sleep(0.033)
                
        except asyncio.CancelledError:
            logger.info(f"Detection processing cancelled for camera {camera_id}")
        except Exception as e:
            logger.error(f"Detection processor error for camera {camera_id}: {e}")
        finally:
            # Stop weapon background thread when camera stops
            self._stop_weapon_thread()
    
    def _can_save_to_db(self, camera_id: int) -> bool:
        """Check if enough time has passed since last DB save for this camera.
        
        This cooldown prevents spamming the DB with detections of the same
        person/object. Tracking (Tier 1) is NOT affected by this.
        """
        if camera_id not in self.last_detection_time:
            return True
        elapsed = (datetime.utcnow() - self.last_detection_time[camera_id]).total_seconds()
        return elapsed >= self.detection_cooldown

    # ------------------------------------------------------------------
    # Presence-based alert suppression helpers
    # ------------------------------------------------------------------

    def _should_fire_alert(self, alert_key: str) -> bool:
        """Return True only when an entity is new (or returned after absence).

        An alert fires when:
          - alert_key has never been seen (first detection ever), OR
          - entity was absent for longer than SESSION_GAP_SECONDS.

        Called BEFORE _refresh_alert_presence so the check uses the
        previous last-seen timestamp, not the current one.
        """
        import time as _t
        last_seen = self._alert_presence.get(alert_key, 0.0)
        return (_t.time() - last_seen) > self.SESSION_GAP_SECONDS

    def _refresh_alert_presence(self, alert_key: str) -> None:
        """Mark entity as currently visible. Called on EVERY detection cycle
        so the last-seen timestamp stays fresh while entity is in frame.
        """
        import time as _t
        self._alert_presence[alert_key] = _t.time()

    
    # =====================================================================
    # BACKGROUND WEAPON DETECTION THREAD
    # =====================================================================
    # Runs weapon YOLO independently from face tracking so that:
    # - Face bboxes stay at ~30 FPS (InsightFace only, very fast)
    # - Weapon bboxes update at YOLO speed (~0.2-0.5 FPS on CPU)
    # - Cached weapon bboxes are shown on EVERY frame until they go stale
    # =====================================================================
    
    def _start_weapon_thread(self, camera_id: int, source):
        """Start background weapon detection thread."""
        self._weapon_stop_event.clear()
        self._weapon_cached_result = None
        self._weapon_result_time = 0.0
        self._weapon_latest_frame = None
        
        def _weapon_loop():
            import time as _t
            logger.info(f"🔫 Weapon detection thread started for camera {camera_id}")
            
            # Wait for weapon detector to be ready
            pipeline = self.pipeline
            while not self._weapon_stop_event.is_set():
                if pipeline._models_ready.get('weapon_detector', False):
                    break
                _t.sleep(0.5)
            
            if self._weapon_stop_event.is_set():
                return
            
            wd = pipeline.model_manager.get_weapon_detector()
            if not wd or not wd.available:
                logger.warning("Weapon detector not available, weapon thread exiting")
                return
            
            logger.info(f"🔫 Weapon detector ready, starting continuous detection")
            miss_count    = 0    # consecutive COCO runs with no weapon

            # ── Gun model background thread ────────────────────────────────────
            # The 166 MB gun model takes ~20–30 s per run on this CPU.
            # Running it synchronously would BLOCK COCO for 20–30 s, causing
            # the 3.5 s stale timer to expire → bboxes vanish mid-tracking.
            #
            # Solution: fire the gun model in a daemon background thread so
            # COCO continues at full speed (~1–3 s/run) without any gaps.
            # ──────────────────────────────────────────────────────────────────
            import threading as _threading

            _gun_result_lock  = _threading.Lock()
            _cached_gun_dets  = []        # last gun model results
            _gun_running      = [False]   # mutable flag for closure
            _gun_cache_ts     = [0.0]     # wall-clock time of LAST COMPLETED gun-model run
            GUN_RUN_EVERY     = 15        # trigger gun model every 15 COCO runs
            GUN_CACHE_TTL     = 4.0       # seconds: discard gun bbox if not re-confirmed within this window
            MAX_SPATIAL_LATENCY = 2.0     # seconds: if inference took longer, bbox coords are too stale to draw
            fast_iter         = GUN_RUN_EVERY  # fire on first iteration too

            def _gun_model_bg(frame_copy, gun_ts):
                """
                Daemon worker: runs gun model, applies Staleness Drop, and stores results.

                gun_ts  — wall-clock time when frame_copy was grabbed (used to
                          measure inference latency).

                Staleness Drop:
                  If detect_gun() took > MAX_SPATIAL_LATENCY seconds, the
                  bounding-box coordinates belong to an ancient frame that no
                  longer matches the live feed.  We still cache the detection so
                  DB/IPFS/alarms fire, but we zero out the bbox so no ghost box
                  is drawn on screen.
                """
                try:
                    result = wd.detect_gun(frame_copy)
                    latency = _t.time() - gun_ts

                    if latency > MAX_SPATIAL_LATENCY:
                        # Spatial data is too old — strip bbox to prevent ghost boxes
                        logger.warning(
                            f"Gun model inference latency {latency:.1f}s > "
                            f"{MAX_SPATIAL_LATENCY}s — stripping stale bboxes "
                            f"({len(result)} detection(s) still cached for alerting)"
                        )
                        result = [dict(d, bbox=[]) for d in result]

                    with _gun_result_lock:
                        _cached_gun_dets.clear()
                        _cached_gun_dets.extend(result)
                        # Stamp with COMPLETION time so TTL counts from NOW,
                        # not from when the ancient frame was grabbed.
                        _gun_cache_ts[0] = _t.time()

                    logger.debug(
                        f"Gun model (bg): {len(result)} detection(s), "
                        f"latency={latency:.1f}s"
                    )
                except Exception as _e:
                    logger.debug(f"Gun model bg error: {_e}")
                finally:
                    _gun_running[0] = False

            while not self._weapon_stop_event.is_set():
                # Grab latest frame
                with self._weapon_frame_lock:
                    frame = self._weapon_latest_frame

                if frame is None:
                    _t.sleep(0.1)
                    continue

                try:
                    # Resize for YOLO inference
                    from ai_engine.utils.performance_optimizer import CPUOptimizer
                    optimized = CPUOptimizer.optimize_image_size(frame, max_dimension=640)
                    orig_h, orig_w = frame.shape[:2]
                    opt_h, opt_w = optimized.shape[:2]
                    scale_x = orig_w / opt_w
                    scale_y = orig_h / opt_h

                    # ── FAST: COCO detection (every loop, ~1–3 s) ──────────────
                    coco_dets = wd.detect_fast(optimized)

                    # ── SLOW: gun model in background thread ───────────────────
                    # Triggered every GUN_RUN_EVERY COCO runs, but only if the
                    # previous gun model run has finished (non-blocking check).
                    fast_iter += 1
                    if fast_iter >= GUN_RUN_EVERY and not _gun_running[0] and wd.gun_detection_enabled:
                        fast_iter = 0
                        _gun_running[0] = True
                        frame_copy = optimized.copy()   # snapshot for bg thread
                        gun_ts = _t.time()              # capture frame-grab time for latency calc
                        _gt = _threading.Thread(
                            target=_gun_model_bg, args=(frame_copy, gun_ts),
                            daemon=True, name="gun-model-bg"
                        )
                        _gt.start()

                    # ── Merge: resolve COCO + cached gun results ──────────────
                    # Read cached gun results and check TTL before merging.
                    # GUN_CACHE_TTL (4 s) is measured from the COMPLETION of the
                    # last gun-model run, so bboxes are shown for exactly 4 s
                    # regardless of how long the 166 MB model took to run.
                    with _gun_result_lock:
                        gun_snapshot = list(_cached_gun_dets)
                        gun_age      = _t.time() - _gun_cache_ts[0]

                    if gun_age > GUN_CACHE_TTL and gun_snapshot:
                        logger.debug(
                            f"Gun cache expired (age={gun_age:.1f}s > TTL={GUN_CACHE_TTL}s) "
                            f"— dropping ghost bbox"
                        )
                        gun_snapshot = []

                    # Frame-level suppression fires here: if COCO sees any weapon,
                    # gun phantoms (conf <0.70) are dropped automatically (YOLO26 threshold).
                    all_dets    = wd.resolve_and_merge(coco_dets, gun_snapshot)
                    raw_weapons = all_dets

                    # Filter to only actual weapons (not suspicious bags etc.)
                    weapon_only = [w for w in raw_weapons if w.get('is_weapon', False)]

                    # Backstop: below 0.35 is noise
                    MIN_WEAPON_CONFIDENCE = 0.35
                    weapon_only = [w for w in weapon_only if w.get('confidence', 0) >= MIN_WEAPON_CONFIDENCE]

                    # Scale bboxes to original resolution.
                    # Staleness Drop guard: bbox=[] means the gun model confirmed
                    # a detection but spatial data was too old to trust — preserve
                    # the dict (so DB/IPFS alerting still fires) but keep bbox empty.
                    scaled_weapons = []
                    for w in weapon_only:
                        wb = w.get('bbox', [])
                        sw = dict(w)
                        if wb and len(wb) >= 4:
                            sw['bbox'] = [
                                int(wb[0] * scale_x), int(wb[1] * scale_y),
                                int(wb[2] * scale_x), int(wb[3] * scale_y)
                            ]
                        else:
                            sw['bbox'] = []  # Preserve empty bbox — no ghost box drawn
                        scaled_weapons.append(sw)
                    
                    # ===================================================
                    # IMMEDIATE DISPLAY — mirror face detection architecture
                    # ===================================================
                    # Face detection shows bbox on EVERY frame the face is
                    # detected, with no confirmation delay. We do the same:
                    #
                    #   ✅ Weapon seen  → cache immediately → red bbox shown
                    #   ❌ Miss run 1   → cache cleared immediately → bbox gone
                    #
                    # False positives are controlled by:
                    #   • _resolve_model_conflicts_v2() in weapon_detector.py
                    #     (spatial + frame-level gun phantom suppression)
                    #   • min_bbox_area_ratio + max_bbox_area_ratio filters
                    #   • 1-miss clear (bboxes vanish on first empty COCO run)
                    # ===================================================
                    if scaled_weapons:
                        miss_count = 0
                        
                        # Cache immediately — bbox displayed on this YOLO run
                        with self._weapon_result_lock:
                            self._weapon_cached_result = scaled_weapons
                            self._weapon_result_time   = _t.time()
                        
                        # (Re-)initialize CSRT trackers on detected bboxes.
                        # CSRT tracks the weapon between YOLO runs at Tier-1
                        # frame rate — same pattern as face bbox tracking.
                        try:
                            new_trackers = []
                            for w in scaled_weapons:
                                wb = w.get('bbox', [])
                                # Staleness Drop guard: cannot initialize a spatial
                                # tracker with no coordinates — skip silently.
                                if not wb or len(wb) < 4:
                                    continue
                                try:
                                    tracker = cv2.TrackerCSRT_create()
                                except AttributeError:
                                    try:
                                        tracker = cv2.TrackerKCF_create()
                                    except AttributeError:
                                        tracker = None
                                if tracker is not None:
                                    tracker.init(
                                        frame,
                                        (wb[0], wb[1], wb[2]-wb[0], wb[3]-wb[1])
                                    )
                                    new_trackers.append((tracker, w))
                            with self._weapon_tracker_lock:
                                self._weapon_trackers           = new_trackers
                                self._weapon_tracker_initialized = len(new_trackers) > 0
                        except Exception as tracker_err:
                            logger.debug(f"Weapon tracker init failed: {tracker_err}")
                            with self._weapon_tracker_lock:
                                self._weapon_tracker_initialized = False
                        
                        logger.warning(
                            f"🔫 WEAPON DETECTED: {[w['class'] for w in scaled_weapons]} "
                            f"(conf: {max(w.get('confidence', 0) for w in scaled_weapons):.2f})"
                        )
                    else:
                        # COCO found NO weapons — one miss clears the COCO display cache
                        # immediately AND invalidates the gun cache so a stale gun bbox
                        # can't silently overrule the current COCO miss on the next iteration.
                        miss_count += 1
                        if miss_count >= 1:
                            miss_count = 0
                            with self._weapon_result_lock:
                                self._weapon_cached_result = None
                                self._weapon_result_time   = 0.0
                            # ← Invalidate gun cache: COCO says frame is clean;
                            #   a ghost bbox must not override that verdict.
                            with _gun_result_lock:
                                _cached_gun_dets.clear()
                                _gun_cache_ts[0] = 0.0
                            with self._weapon_tracker_lock:
                                self._weapon_trackers            = []
                                self._weapon_tracker_initialized = False
                
                except Exception as e:
                    logger.error(f"Weapon thread detection error: {e}", exc_info=True)
                
                # Minimal idle sleep — YOLO inference already takes several seconds on CPU.
                _t.sleep(0.05)
            
            logger.info(f"🔫 Weapon detection thread stopped for camera {camera_id}")

        
        self._weapon_thread = threading.Thread(
            target=_weapon_loop, daemon=True, name=f"weapon-detect-cam{camera_id}"
        )
        self._weapon_thread.start()
    
    def _stop_weapon_thread(self):
        """Stop background weapon detection thread."""
        self._weapon_stop_event.set()
        if self._weapon_thread and self._weapon_thread.is_alive():
            self._weapon_thread.join(timeout=3.0)
        self._weapon_thread = None
        self._weapon_cached_result = None
        self._weapon_result_time = 0.0  # Bug #2 fix: reset so stale time can't serve old bboxes on restart
        with self._weapon_tracker_lock:
            self._weapon_trackers = []
            self._weapon_tracker_initialized = False
    
    def _merge_weapon_cache(
        self,
        tracking_result: Optional[DetectionResult],
        current_frame: Optional[np.ndarray] = None
    ) -> Optional[DetectionResult]:
        """Merge cached weapon bboxes from background thread into tracking result.
        
        If the weapon cache is fresh (< _weapon_stale_seconds old), weapon bboxes
        are added to the tracking result.
        
        Uses OpenCV CSRT trackers to update weapon bbox positions at 30 FPS
        between YOLO runs — exactly like face bboxes are tracked between
        InsightFace runs in Tier 1.  `current_frame` is the same frame that
        Tier 1 face detection just processed, ensuring weapon and face coordinates
        are in the same spatial reference.
        """
        import time as _t
        
        with self._weapon_result_lock:
            weapons = self._weapon_cached_result
            weapon_time = self._weapon_result_time
        
        # No cached weapons or cache is stale
        if not weapons or (_t.time() - weapon_time > self._weapon_stale_seconds):
            return tracking_result
        
        # WEAPON TRACKING: Update bboxes using CSRT tracker for smooth 30 FPS movement
        tracked_weapons = weapons  # fallback to cached bboxes
        with self._weapon_tracker_lock:
            tracker_ready = self._weapon_tracker_initialized
            trackers_copy = list(self._weapon_trackers) if tracker_ready else []
        
        if tracker_ready and trackers_copy and current_frame is not None:
            try:
                updated_weapons = []
                for tracker, weapon_data in trackers_copy:
                    success, bbox = tracker.update(current_frame)
                    if success:
                        x, y, w, h = [int(v) for v in bbox]
                        updated_w = dict(weapon_data)
                        updated_w['bbox'] = [x, y, x + w, y + h]
                        updated_weapons.append(updated_w)
                    else:
                        # Tracker lost the target — use cached bbox
                        updated_weapons.append(weapon_data)
                if updated_weapons:
                    tracked_weapons = updated_weapons
            except Exception:
                tracked_weapons = weapons  # fallback to cached on any error
        
        # If tracking_result is None (no faces), create a weapon-only result
        if tracking_result is None:
            return DetectionResult(
                has_face=False,
                has_weapon=True,
                weapons_detected=tracked_weapons,
                metadata={"tracking_only": True, "weapon_from_cache": True}
            )
        
        # Merge weapons into existing tracking result
        return DetectionResult(
            has_face=tracking_result.has_face,
            face_bbox=tracking_result.face_bbox,
            face_embedding=tracking_result.face_embedding,
            face_quality_score=tracking_result.face_quality_score,
            is_real_face=tracking_result.is_real_face,
            emotion=tracking_result.emotion,
            age=tracking_result.age,
            pose_keypoints=tracking_result.pose_keypoints,
            body_orientation=tracking_result.body_orientation,
            action=tracking_result.action,
            matched_person_id=tracking_result.matched_person_id,
            matched_person_name=tracking_result.matched_person_name,
            confidence=tracking_result.confidence,
            all_faces=tracking_result.all_faces,
            has_weapon=True,
            weapons_detected=tracked_weapons,
            pose_alert=tracking_result.pose_alert,
            pose_type=tracking_result.pose_type,
            pose_confidence=tracking_result.pose_confidence,
            pose_indicators=tracking_result.pose_indicators,
            metadata={**(tracking_result.metadata or {}), "weapon_from_cache": True}
        )
    
    def _needs_full_detection(self, camera_id: int) -> bool:
        """Decide if a full detection (Tier 2) is needed.
        
        Returns True when:
        - No detection has been saved yet for this session
        - Or periodic refresh interval has elapsed (to update emotion/age/pose)
        """
        import time as _time
        
        # First detection in this session
        if not self._detection_saved.get(camera_id, False):
            return True
        
        # Periodic refresh (update emotion, age, pose labels)
        last_full = self._last_full_detection_time.get(camera_id, 0)
        if _time.time() - last_full > self.FULL_DETECTION_INTERVAL:
            return True
        
        return False
    
    def _merge_tracking_with_full(
        self, camera_id: int, tracking: DetectionResult
    ) -> DetectionResult:
        """Merge fast tracking bbox positions with full detection metadata.
        
        MULTI-FACE: Matches tracking faces to full-detection faces by IoU
        (bounding box overlap). Each tracking face inherits metadata from
        its closest full-detection match (emotion, watchlist name, etc.).
        Unmatched tracking faces appear as plain boxes.
        """
        full = self._full_detection_result.get(camera_id)
        if full is None:
            return tracking  # No full result yet, use tracking as-is
        
        # Merge all_faces: tracking's fresh bboxes + full's metadata
        merged_faces = []
        used_full_indices = set()
        
        for t_face in tracking.all_faces:
            best_iou = 0.0
            best_idx = -1
            
            for i, f_face in enumerate(full.all_faces):
                if i in used_full_indices:
                    continue
                iou = self._compute_iou(t_face.face_bbox, f_face.face_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i
            
            if best_idx >= 0 and best_iou > 0.2:
                # Matched: tracking bbox + full metadata
                f_face = full.all_faces[best_idx]
                used_full_indices.add(best_idx)
                merged_faces.append(FaceData(
                    face_bbox=t_face.face_bbox,  # FRESH from tracking
                    face_embedding=f_face.face_embedding,
                    emotion=f_face.emotion,
                    age=f_face.age,
                    matched_person_id=f_face.matched_person_id,
                    matched_person_name=f_face.matched_person_name,
                    confidence=f_face.confidence,
                    face_quality_score=f_face.face_quality_score,
                    is_real_face=f_face.is_real_face
                ))
            else:
                # Unmatched tracking face: no metadata yet
                merged_faces.append(t_face)
        
        # Use largest merged face for backward-compat scalar fields
        primary = None
        if merged_faces:
            primary = max(merged_faces, key=lambda f: (
                (f.face_bbox[2] - f.face_bbox[0]) * (f.face_bbox[3] - f.face_bbox[1])
            ))
        
        # WEAPON MERGE FIX: Use weapon data from tracking (weapon thread cache) if
        # available, otherwise fall back to full detection's weapon data. This ensures
        # weapon bboxes persist even if the weapon thread cache is between refresh cycles.
        merged_has_weapon = tracking.has_weapon or full.has_weapon
        merged_weapons = tracking.weapons_detected if tracking.weapons_detected else full.weapons_detected
        
        # POSE OFFSET TRANSLATION: Pose keypoints come from Tier 2 (1.5s old).
        # Face bboxes from Tier 1 update at 30 FPS. When the person moves,
        # the face bbox follows but pose stays at old position. Fix: compute
        # the offset between current face center and the Tier 2 face center,
        # then shift all pose keypoints by that delta.
        translated_pose = full.pose_keypoints
        if full.pose_keypoints and primary and full.face_bbox:
            try:
                # Current face center (from tracking)
                t_cx = (primary.face_bbox[0] + primary.face_bbox[2]) / 2
                t_cy = (primary.face_bbox[1] + primary.face_bbox[3]) / 2
                # Tier 2 face center (when pose was captured)
                f_cx = (full.face_bbox[0] + full.face_bbox[2]) / 2
                f_cy = (full.face_bbox[1] + full.face_bbox[3]) / 2
                dx = t_cx - f_cx
                dy = t_cy - f_cy
                
                if abs(dx) > 2 or abs(dy) > 2:  # Only translate if moved > 2px
                    kps = full.pose_keypoints.get('keypoints', {})
                    shifted_kps = {}
                    for idx, kp in kps.items():
                        shifted_kps[idx] = {
                            'x': kp['x'] + dx,
                            'y': kp['y'] + dy,
                            'z': kp.get('z', 0),
                            'visibility': kp.get('visibility', 0)
                        }
                    translated_pose = {'keypoints': shifted_kps}
                    if 'raw_landmarks' in full.pose_keypoints:
                        translated_pose['raw_landmarks'] = full.pose_keypoints['raw_landmarks']
            except Exception:
                translated_pose = full.pose_keypoints
        
        return DetectionResult(
            has_face=tracking.has_face,
            face_bbox=primary.face_bbox if primary else tracking.face_bbox,
            face_embedding=primary.face_embedding if primary else (full.face_embedding if full else None),
            face_quality_score=primary.face_quality_score if primary else full.face_quality_score,
            is_real_face=primary.is_real_face if primary else full.is_real_face,
            emotion=primary.emotion if primary else full.emotion,
            age=primary.age if primary else full.age,
            pose_keypoints=translated_pose,
            body_orientation=full.body_orientation,
            action=full.action,
            matched_person_id=primary.matched_person_id if primary else full.matched_person_id,
            matched_person_name=primary.matched_person_name if primary else full.matched_person_name,
            confidence=primary.confidence if primary else full.confidence,
            all_faces=merged_faces,
            has_weapon=merged_has_weapon,
            weapons_detected=merged_weapons,
            pose_alert=full.pose_alert,
            pose_type=full.pose_type,
            pose_confidence=full.pose_confidence,
            pose_indicators=full.pose_indicators,
            metadata={
                **full.metadata,
                "tracking_only": False,
                "face_count": len(merged_faces)
            }
        )

    
    @staticmethod
    def _compute_iou(bbox1: tuple, bbox2: tuple) -> float:
        """Compute Intersection over Union between two (x1,y1,x2,y2) bboxes."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - inter
        
        return inter / union if union > 0 else 0.0
    
    def _sync_process_frame(self, frame: np.ndarray, confirmed_weapons: Optional[list] = None) -> Optional[DetectionResult]:
        """Run FULL detection pipeline (Tier 2) — heavy processing.
        
        Args:
            frame: BGR image from camera
            confirmed_weapons: Weapons from weapon thread cache.
                Passed to process_frame so it uses these instead of
                running YOLO again.
        """
        try:
            # Refresh watchlist cache if stale
            self._update_watchlist_cache_sync()
            
            # Build watchlist embeddings in the format expected by pipeline
            watchlist_for_pipeline = []
            if self.watchlist_cache:
                for entry in self.watchlist_cache:
                    watchlist_for_pipeline.append((
                        entry['person_id'], 
                        entry['embedding'],
                        entry['name']
                    ))
            
            # SKIP MOTION CHECK for full detection — tracking already confirmed
            # something is in the frame, so motion check is redundant here.
            result = self.pipeline.process_frame(
                frame,
                watchlist_embeddings=watchlist_for_pipeline,
                skip_motion_check=True,
                confirmed_weapons=confirmed_weapons
            )
            return result
        except Exception as e:
            logger.error(f"Frame processing error: {e}", exc_info=True)
            return None
    
    def _full_detection_in_background(self, camera_id: int, frame: np.ndarray):
        """Run full detection pipeline in a background thread (NON-BLOCKING).
        
        Guards:
        - Checks active_cameras before each expensive step (aborts if camera stopped)
        - Sets _full_det_running flag to prevent task queue buildup
        """
        import time as _t
        try:
            # STOP GUARD: Abort immediately if camera was stopped
            if camera_id not in self.active_cameras:
                return
            
            # Read weapon cache from weapon thread (instantly cached on detect)
            confirmed_weapons = None
            with self._weapon_result_lock:
                if self._weapon_cached_result:
                    confirmed_weapons = list(self._weapon_cached_result)  # copy
            
            full_result = self._sync_process_frame(frame, confirmed_weapons=confirmed_weapons)
            
            # STOP GUARD: Check again after expensive processing
            if camera_id not in self.active_cameras:
                return
            
            if full_result and (full_result.has_face or full_result.has_weapon):
                # Update cached full result for enrichment merging.
                # DO NOT overwrite _latest_results — the tracking loop's
                # _merge_tracking_with_full() will merge pose/emotion/names
                # from _full_detection_result into the live tracking result.
                # Overwriting _latest_results here would replace the live
                # multi-face tracking bboxes with a stale snapshot.
                self._full_detection_result[camera_id] = full_result
                
                # DB save: only if cooldown elapsed and camera still active
                if self._can_save_to_db(camera_id) and camera_id in self.active_cameras:
                    self._handle_detection_sync(camera_id, frame, full_result)
                    self._detection_saved[camera_id] = True
                    self.last_detection_time[camera_id] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Background full detection error on camera {camera_id}: {e}", exc_info=True)
        finally:
            # Release one-at-a-time flag so next detection can run
            self._full_det_running[camera_id] = False
    
    def _handle_detection_sync(
        self,
        camera_id: int,
        frame: np.ndarray,
        result: DetectionResult
    ):
        """Handle a detection result — SYNC version for background thread.
        
        Saves to DB, anchors to blockchain, creates alerts, and broadcasts
        via WebSocket. Runs in ThreadPoolExecutor to avoid blocking tracking.
        """
        import hashlib  # Must be at function-level scope (not inside conditionals)
        
        # Determine detection type and severity (priority order)
        is_verified = False  # Default to unverified
        
        # MULTI-FACE FIX: Check ALL faces for watchlist match, not just the largest
        # Previously only result.matched_person_id (from largest face) was checked,
        # causing watchlist matches on smaller faces to be saved as face_detection
        best_match_face = None
        if result.all_faces:
            matched_faces = [f for f in result.all_faces if f.matched_person_id is not None]
            if matched_faces:
                best_match_face = max(matched_faces, key=lambda f: f.confidence)
        
        # CONFIDENCE FIX: Compute effective confidence for the detection type
        # (result.confidence = watchlist similarity, which is 0 for non-matches)
        effective_confidence = result.confidence
        
        if result.has_weapon:
            actual_weapons = [w for w in result.weapons_detected if w.get('is_weapon', False)]
            if actual_weapons:
                detection_type = "weapon_detected"
                severity = "critical"
                # Use max weapon confidence instead of face confidence
                effective_confidence = max(w.get('confidence', 0) for w in actual_weapons)
            else:
                detection_type = "suspicious_object"
                severity = "high"
                effective_confidence = max((w.get('confidence', 0) for w in result.weapons_detected), default=0.0)
        elif best_match_face is not None:
            # Use the BEST watchlist match across ALL faces
            detection_type = "watchlist_match"
            severity = "critical"
            effective_confidence = best_match_face.confidence
            # Override result fields to use the best match (not just largest face)
            result.matched_person_id = best_match_face.matched_person_id
            result.matched_person_name = best_match_face.matched_person_name
            logger.info(f"🎯 WATCHLIST MATCH DETECTED: person_id={result.matched_person_id}, confidence={effective_confidence:.3f}")
        elif not result.is_real_face and result.has_face:
            detection_type = "spoof_attempt"
            severity = "high"
            if result.all_faces:
                effective_confidence = max(f.confidence for f in result.all_faces)
        elif hasattr(result, 'pose_alert') and result.pose_alert:
            pose_type = getattr(result, 'pose_type', 'aggressive') or 'aggressive'
            detection_type = "aggressive_pose"
            severity = "critical" if pose_type == 'fighting' else "high"
            effective_confidence = getattr(result, 'pose_confidence', 0)
            logger.info(f"🥊 AGGRESSIVE POSE: {pose_type} (conf: {effective_confidence:.2f})")
        elif result.emotion in ["angry", "fear"]:
            detection_type = "emotion_alert"
            severity = "medium"
            if result.all_faces:
                effective_confidence = max(f.confidence for f in result.all_faces)
        elif result.has_face:
            detection_type = "face_detection"
            severity = "low"
            # Use InsightFace det_score for face detection confidence
            if result.all_faces:
                effective_confidence = max(f.confidence for f in result.all_faces)
        else:
            detection_type = "unknown"
            severity = "low"

        # ============================================
        # PRESENCE-BASED ALERT GATE
        # ============================================
        # Compute a stable key that uniquely identifies the detected entity.
        # _should_fire_alert returns True only when the entity is NEW (first
        # detection or returned after SESSION_GAP_SECONDS of absence).
        # _refresh_alert_presence is always called so the timestamp stays
        # fresh while the entity remains visible.
        # ============================================
        if result.matched_person_id is not None:
            # Watchlist match: one key per person per camera
            alert_key = f"alert_{camera_id}_watchlist_{result.matched_person_id}"
        elif detection_type in ("weapon_detected", "suspicious_object") and result.weapons_detected:
            wclasses = ','.join(sorted(set(
                w.get('class', 'weapon')
                for w in result.weapons_detected
                if w.get('is_weapon', False)
            ))) or 'weapon'
            alert_key = f"alert_{camera_id}_weapon_{wclasses}"
        elif detection_type == "aggressive_pose":
            alert_key = f"alert_{camera_id}_pose"
        elif detection_type in ("face_detection", "spoof_attempt", "emotion_alert"):
            # Per-unique-face key; face_hash computed below — use placeholder
            # for now and update after face_hash is available (same check order)
            _fh = None
            if result.face_embedding is not None:
                try:
                    import hashlib as _hl
                    _emb = result.face_embedding.flatten()
                    _q   = (_emb * 127).astype('int8').tobytes()
                    _fh  = _hl.sha256(_q).hexdigest()[:16]
                except Exception:
                    pass
            alert_key = f"alert_{camera_id}_face_{_fh or 'unknown'}"
        else:
            alert_key = f"alert_{camera_id}_{detection_type}"

        # Check BEFORE refreshing (gives correct answer using old timestamp)
        is_new_appearance = self._should_fire_alert(alert_key)
        # Always refresh so presence stays live while entity is visible
        self._refresh_alert_presence(alert_key)

        # ============================================
        # PRE-DEDUP: Create Alert DB record for critical events
        # ============================================
        # Uses presence gate (replaces the old 60s cooldown).
        try:
            from app.db.session import SyncSessionLocal
            from app.models.alert import Alert

            # Aggressive pose alert
            if hasattr(result, 'pose_alert') and result.pose_alert:
                if is_new_appearance:
                    try:
                        alert_session = SyncSessionLocal()
                        try:
                            pose_type = result.pose_type or 'aggressive'
                            indicators = ', '.join(result.pose_indicators) if result.pose_indicators else 'unknown'
                            
                            alert = Alert(
                                alert_type="aggressive_pose",
                                severity="critical" if pose_type == 'fighting' else "high",
                                title=f"Aggressive Pose Detected: {pose_type.title()}",
                                message=f"Aggressive behavior detected: {pose_type}. Indicators: {indicators}. Immediate attention required.",
                                camera_id=camera_id,
                                timestamp=datetime.utcnow(),
                                is_acknowledged=False,
                                alert_metadata={
                                    'pose_type': pose_type,
                                    'confidence': result.pose_confidence,
                                    'indicators': result.pose_indicators,
                                    'detection_type': 'aggressive_pose'
                                }
                            )
                            alert_session.add(alert)
                            alert_session.commit()
                            logger.info(f"🚨 POSE ALERT CREATED: {pose_type} (confidence: {result.pose_confidence:.2f})")

                            # Broadcast pose alert via WebSocket
                            try:
                                notification_data = {
                                    "type": "detection_alert",
                                    "camera_id": camera_id,
                                    "detection_type": "aggressive_pose",
                                    "severity": "critical" if pose_type == 'fighting' else "high",
                                    "pose_type": pose_type,
                                    "confidence": result.pose_confidence,
                                    "indicators": result.pose_indicators,
                                    "message": f"Aggressive pose ({pose_type}) detected on camera {camera_id}"
                                }
                                if self._main_loop:
                                    import asyncio
                                    asyncio.run_coroutine_threadsafe(
                                        notification_service.broadcast(notification_data),
                                        self._main_loop
                                    )
                            except Exception:
                                pass
                        finally:
                            alert_session.close()
                    except Exception as alert_err:
                        logger.error(f"Failed to create pose alert: {alert_err}")
        except Exception:
            pass  # Non-critical — don't block detection flow
        
        # ============================================
        # 12-HOUR DEDUP CHECK: Prevent duplicate evidence saves
        # Uses per-person face hashing to differentiate different people
        # ============================================
        try:
            from app.db.session import SyncSessionLocal
            from app.models.detection import Detection as DetModel
            
            # Compute face embedding hash for per-person dedup
            face_hash = None
            if result.face_embedding is not None:
                try:
                    import hashlib
                    # Quantize embedding to 8-bit to create stable hash
                    emb = result.face_embedding.flatten()
                    quantized = (emb * 127).astype('int8').tobytes()
                    face_hash = hashlib.sha256(quantized).hexdigest()[:16]
                except Exception:
                    face_hash = None
            
            dedup_session = SyncSessionLocal()
            try:
                # Use shorter window for non-face events; live config for face/weapon.
                # This is the main dedup knob controlled from the Settings UI.
                if detection_type in ("aggressive_pose", "emotion_alert"):
                    dedup_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
                else:
                    from config.config_manager import config_manager as _cfg_mgr
                    _dedup_secs = _cfg_mgr.get().db_dedup_seconds
                    dedup_cutoff = datetime.now(timezone.utc) - timedelta(seconds=_dedup_secs)
                    logger.debug(f"Dedup window: {_dedup_secs}s (from live config)")
                
                dedup_query = dedup_session.query(DetModel).filter(
                    DetModel.camera_id == camera_id,
                    DetModel.timestamp >= dedup_cutoff
                )
                
                if result.matched_person_id is not None:
                    # Same watchlist person on same camera within 12h
                    dedup_query = dedup_query.filter(
                        DetModel.matched_person_id == result.matched_person_id
                    )
                elif detection_type in ("weapon_detected", "suspicious_object"):
                    # Same weapon-type detection on same camera within 12h
                    dedup_query = dedup_query.filter(
                        DetModel.detection_type == detection_type
                    )
                elif face_hash and detection_type == "face_detection":
                    # Per-person dedup using face embedding hash
                    # Different people → different hashes → saved separately
                    from sqlalchemy import cast, String
                    dedup_query = dedup_query.filter(
                        DetModel.detection_type == detection_type,
                        DetModel.detection_metadata['face_hash'].astext == face_hash
                    )
                else:
                    # Generic dedup for unknown/no-embedding detections
                    dedup_query = dedup_query.filter(
                        DetModel.detection_type == detection_type,
                        DetModel.matched_person_id == None
                    )
                
                existing = dedup_query.first()
                if existing:
                    age_delta = datetime.now(timezone.utc) - existing.timestamp.replace(tzinfo=timezone.utc) if existing.timestamp.tzinfo is None else datetime.now(timezone.utc) - existing.timestamp
                    logger.info(
                        f"⏩ 12h dedup: skipping {detection_type} on camera {camera_id} "
                        f"(existing: id={existing.id}, age={age_delta})"
                    )
                    # Presence gate: only broadcast when entity has (re-)appeared.
                    # Suppresses repeated notifications while entity stays in frame.
                    if is_new_appearance:
                        self._broadcast_detection_sync(
                            camera_id, detection_type, effective_confidence,
                            result, severity
                        )
                    return  # Skip DB save — still within dedup window
            finally:
                dedup_session.close()
        except Exception as dedup_err:
            logger.debug(f"Dedup check failed (proceeding with save): {dedup_err}")
        
        # Save detection to database using SYNC session
        detection_id = None
        try:
            from app.db.session import SyncSessionLocal
            from app.models.detection import Detection
            import uuid
            
            session = SyncSessionLocal()
            try:
                # --- Evidence storage (single-frame image) ---
                success, buffer = cv2.imencode(".jpg", frame)
                if not success:
                    raise RuntimeError("Failed to encode frame for evidence image")

                frame_bytes = buffer.tobytes()

                timestamp = datetime.now(timezone.utc)
                event_id = f"DET-{uuid.uuid4().hex[:8].upper()}"
                
                watchlist_size = len(self.watchlist_cache) if self.watchlist_cache else 0
                is_watchlist_match = result.matched_person_id is not None

                storage_root = Path("storage/local/evidence")
                camera_folder = storage_root / f"camera_{camera_id}"
                date_folder = camera_folder / timestamp.strftime("%Y%m%d")
                date_folder.mkdir(parents=True, exist_ok=True)

                clip_filename = f"{event_id}.jpg"
                local_path = date_folder / clip_filename
                with open(local_path, "wb") as f:
                    f.write(frame_bytes)

                # Simple thumbnail (optional, best-effort)
                thumbnail_path: Optional[Path] = None
                try:
                    img = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
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

                        thumbnail_path = date_folder / f"{event_id}_thumb.jpg"
                        cv2.imwrite(str(thumbnail_path), thumb)
                except Exception:
                    thumbnail_path = None

                clip_hash = hashlib.sha256(frame_bytes).hexdigest()

                # Upload evidence frame to IPFS (best-effort, non-blocking)
                ipfs_cid = None
                try:
                    from app.utils.ipfs_client import ipfs_client
                    ipfs_cid = ipfs_client.upload_bytes_sync(frame_bytes)
                    if ipfs_cid:
                        logger.info(f"Evidence uploaded to IPFS: {ipfs_cid}")
                except Exception as ipfs_err:
                    logger.debug(f"IPFS upload skipped: {ipfs_err}")

                detection = Detection(
                    event_id=event_id,
                    camera_id=camera_id,
                    detection_type=detection_type,
                    confidence=effective_confidence,
                    timestamp=timestamp,
                    face_bbox=list(result.face_bbox) if result.face_bbox else None,
                    matched_person_id=result.matched_person_id,
                    clip_hash=clip_hash,
                    clip_size_bytes=len(frame_bytes),
                    ipfs_cid=ipfs_cid,
                    local_path=local_path.as_posix(),
                    thumbnail_path=thumbnail_path.as_posix() if thumbnail_path else None,
                    detection_metadata={
                        "emotion": result.emotion,
                        "is_real_face": result.is_real_face,
                        "severity": severity,
                        "has_weapon": result.has_weapon,
                        "weapons_detected": result.weapons_detected if result.has_weapon else [],
                        "weapon_count": len(result.weapons_detected) if result.has_weapon else 0,
                        "watchlist_size": watchlist_size,
                        "is_watchlist_match": is_watchlist_match,
                        "face_hash": face_hash,
                        "pose_type": getattr(result, 'pose_type', None),
                        "pose_confidence": getattr(result, 'pose_confidence', None),
                        "pose_indicators": getattr(result, 'pose_indicators', None),
                        # AGE PROGRESSION: Store detected age and compute age gap
                        "detected_age": result.age if hasattr(result, 'age') and result.age else None,
                        **self._compute_age_gap(session, result, is_watchlist_match),
                    },
                    is_verified=is_verified
                )
                session.add(detection)
                session.commit()
                session.refresh(detection)
                detection_id = detection.id
                logger.info(f"Detection saved: {detection_type} (severity: {severity}, id: {detection_id})")
                
                # Anchor evidence to blockchain
                try:
                    from app.services.blockchain_service import BlockchainService
                    
                    evidence_receipt = {
                        "event_id": event_id,
                        "clip_hash": clip_hash,
                        "timestamp": timestamp.isoformat(),
                        "camera_id": camera_id,
                        "detection_type": detection_type,
                        "confidence": effective_confidence,
                        "matched_person_id": result.matched_person_id,
                        "severity": severity
                    }
                    
                    blockchain_service = BlockchainService(session)
                    tx_id = blockchain_service.register_evidence_sync(
                        event_id=event_id,
                        evidence_receipt=evidence_receipt
                    )
                    
                    detection.blockchain_tx_id = tx_id
                    detection.anchored_at = datetime.now(timezone.utc)
                    session.commit()
                    
                    logger.info(f"Evidence anchored to blockchain: {tx_id}")
                    
                except Exception as e:
                    logger.warning(f"Blockchain anchoring failed (non-critical): {e}")
                
                # UPDATE WATCHLIST LAST SEEN: When a watchlist match is detected,
                # update the matched person's last_seen_at, location, and camera_id
                # so the Watchlist page shows accurate "Last Seen" info.
                if detection_type == "watchlist_match" and result.matched_person_id:
                    try:
                        from app.models.watchlist import WatchlistPerson
                        person = session.query(WatchlistPerson).filter(
                            WatchlistPerson.id == result.matched_person_id
                        ).first()
                        if person:
                            person.last_seen_at = datetime.now(timezone.utc)
                            person.last_seen_location = f"Camera {camera_id}"
                            person.last_seen_camera_id = camera_id
                            person.total_detections = (person.total_detections or 0) + 1
                            session.commit()
                            logger.info(f"📍 Watchlist last_seen updated: person_id={result.matched_person_id}, camera={camera_id}")
                    except Exception as ws_err:
                        logger.warning(f"Failed to update watchlist last_seen (non-critical): {ws_err}")
                
                logger.info(f"Detection saved: {detection_type} (severity: {severity}, id: {detection_id})")
                
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to save detection to DB: {e}", exc_info=True)
        
        # Broadcast to WebSocket clients (presence-gated — only on new appearance)
        if is_new_appearance:
            self._broadcast_detection_sync(
                camera_id, detection_type, effective_confidence,
                result, severity, detection_id=detection_id
            )
    
    def _compute_age_gap(self, session, result, is_watchlist_match: bool) -> dict:
        """Compute age gap between detected age and watchlist person's registered age.
        
        Returns dict with 'registered_age' and 'age_gap' keys to merge into
        detection_metadata. Returns empty dict if not applicable.
        """
        if not is_watchlist_match or not result.matched_person_id:
            return {}
        
        detected_age = result.age if hasattr(result, 'age') and result.age else None
        if detected_age is None:
            return {}
        
        try:
            from app.models.watchlist import WatchlistPerson
            person = session.query(WatchlistPerson).filter(
                WatchlistPerson.id == result.matched_person_id
            ).first()
            
            if person and person.age is not None:
                age_gap = abs(int(detected_age) - int(person.age))
                return {
                    "registered_age": person.age,
                    "age_gap": age_gap,
                    "age_gap_label": f"Registered at {person.age}yrs, detected at {int(detected_age)}yrs ({age_gap}yr gap)"
                }
        except Exception as e:
            logger.debug(f"Age gap computation failed: {e}")
        
        return {}
    
    def _broadcast_detection_sync(
        self, camera_id: int, detection_type: str, confidence: float,
        result, severity: str, detection_id: int = None
    ):
        """Broadcast detection to WebSocket clients from a background thread.
        
        Includes a 10-second per-type cooldown to prevent notification spam
        while still ensuring real-time awareness.
        """
        import time as _t
        
        # 10-second notification cooldown per camera+type to prevent spam
        cooldown_key = f"notif_{camera_id}_{detection_type}"
        if not hasattr(self, '_notification_cooldowns'):
            self._notification_cooldowns = {}
        last_notif = self._notification_cooldowns.get(cooldown_key, 0)
        if _t.time() - last_notif < 10:
            return  # Skip — notified recently
        
        broadcast_data = {
            "id": detection_id,
            "camera_id": camera_id,
            "detection_type": detection_type,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "matched_person_id": result.matched_person_id,
            "matched_person_name": getattr(result, 'matched_person_name', None),
            "emotion": result.emotion,
            "is_real_face": result.is_real_face,
            "severity": severity,
            "has_weapon": result.has_weapon,
            "weapons_detected": result.weapons_detected if result.has_weapon else []
        }
        
        if self._main_loop and not self._main_loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    notification_service.broadcast_detection(broadcast_data),
                    self._main_loop
                )
                future.result(timeout=2.0)
                self._notification_cooldowns[cooldown_key] = _t.time()
                logger.info(f"📢 NOTIFICATION SENT: {detection_type} on camera {camera_id} (conf: {confidence:.2f})")
            except Exception as ws_err:
                logger.warning(f"WebSocket broadcast error: {ws_err}")
        else:
            logger.warning(f"Cannot broadcast — main event loop unavailable")
    
    def _update_watchlist_cache_sync(self):
        """Update cached watchlist embeddings (synchronous version for background thread)"""
        now = datetime.utcnow()
        
        if (self.cache_update_time is None or 
            (now - self.cache_update_time).seconds > self.cache_ttl):
            
            try:
                from app.db.session import SyncSessionLocal
                from app.models.watchlist import WatchlistPerson
                import json
                
                session = SyncSessionLocal()
                try:
                    # Load all active watchlist persons with embeddings
                    persons = session.query(WatchlistPerson).filter(
                        WatchlistPerson.is_active == True
                    ).all()
                    
                    self.watchlist_cache = []
                    for person in persons:
                        # Use face_embeddings (plural) - it's a list of embeddings
                        if person.face_embeddings:
                            embeddings = person.face_embeddings
                            # Parse from JSON if stored as string
                            if isinstance(embeddings, str):
                                embeddings = json.loads(embeddings)
                            # Handle as list of embeddings
                            if isinstance(embeddings, list) and len(embeddings) > 0:
                                # Use first embedding for matching
                                self.watchlist_cache.append({
                                    'person_id': person.id,
                                    'name': person.name,
                                    'embedding': embeddings[0] if isinstance(embeddings[0], list) else embeddings
                                })
                    
                    self.cache_update_time = now
                    logger.info(f"Watchlist cache updated: {len(self.watchlist_cache)} persons loaded")
                    if len(self.watchlist_cache) == 0:
                        logger.warning("⚠️  Watchlist is EMPTY - no persons enrolled! All faces will be 'unknown'.")
                finally:
                    session.close()
            except Exception as e:
                logger.warning(f"Failed to update watchlist cache: {e}")
    
    def get_active_camera_count(self) -> int:
        """Get count of cameras currently being processed"""
        return len(self.active_cameras)
    
    def is_camera_active(self, camera_id: int) -> bool:
        """Check if a camera is being processed"""
        return camera_id in self.active_cameras


# Global singleton instance
detection_processor = DetectionProcessor()
