"""
Complete detection pipeline integrating all AI models

Now uses singleton AIModelManager to share models across all cameras,
preventing memory overload and system crashes.
"""
import cv2
import numpy as np
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from loguru import logger
from ai_engine.model_manager import ai_model_manager
from ai_engine.utils.performance_optimizer import CPUOptimizer, MotionDetector

@dataclass
class FaceData:
    """Per-face detection data for multi-face support."""
    face_bbox: tuple
    face_embedding: Optional[np.ndarray] = None
    emotion: Optional[str] = None
    age: Optional[int] = None
    matched_person_id: Optional[int] = None
    matched_person_name: Optional[str] = None
    confidence: float = 0.0
    face_quality_score: float = 0.0
    is_real_face: bool = True

@dataclass
class DetectionResult:
    """Detection result container — supports multiple faces."""
    has_face: bool
    face_bbox: Optional[tuple] = None  # Largest face (backward compat)
    face_embedding: Optional[np.ndarray] = None
    face_quality_score: float = 0.0
    is_real_face: bool = True
    emotion: Optional[str] = None
    age: Optional[int] = None
    pose_keypoints: Optional[dict] = None
    body_orientation: Optional[str] = None
    action: Optional[str] = None
    matched_person_id: Optional[int] = None
    matched_person_name: Optional[str] = None
    confidence: float = 0.0
    # Multi-face: ALL detected faces with per-face metadata
    all_faces: List['FaceData'] = field(default_factory=list)
    # Weapon detection
    weapons_detected: List[Dict[str, Any]] = field(default_factory=list)
    has_weapon: bool = False
    # Pose alerts
    pose_alert: bool = False
    pose_type: Optional[str] = None
    pose_confidence: float = 0.0
    pose_indicators: List[str] = field(default_factory=list)
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

class DetectionPipeline:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize complete detection pipeline
        
        Args:
            config: Configuration dictionary
        """
        logger.info("🔧 DetectionPipeline.__init__ started")
        self.config = config
        
        logger.info("📦 Getting shared model manager...")
        # Use shared model manager (singleton)
        self.model_manager = ai_model_manager
        logger.info("✅ Model manager obtained")
        
        logger.info("🎬 Initializing motion detector...")
        # Initialize utilities
        self.motion_detector = MotionDetector(threshold=25.0)
        logger.info("✅ Motion detector ready")
        
        logger.info("⚙️ Configuring PyTorch...")
        # Configure CPU optimization
        CPUOptimizer.configure_pytorch()
        logger.info("✅ PyTorch configured")
        
        # Feature flags from config (OPTIMIZED for performance)
        # Disable heavy models by default to speed up startup
        self.enable_emotion = config.get('enable_emotion_detection', False)  # Disabled (8.75s load)
        self.enable_pose = config.get('enable_pose_estimation', False)  # Disabled (9.76s load)
        self.enable_anti_spoof = False  # ALWAYS DISABLED (causes AttributeError + slow)
        self.enable_age = config.get('enable_age_estimation', False)  # Disabled by default
        self.enable_weapon_detection = config.get('enable_weapon_detection', True)  # Enabled
        
        # Use shared face recognizer from model manager (CRITICAL for performance!)
        # This prevents loading InsightFace models multiple times
        logger.info("🔍 Getting shared face recognizer from model manager...")
        # CRITICAL FIX: Use get_face_recognizer() method, not direct property access!
        self.face_recognizer = self.model_manager.get_face_recognizer()
        logger.info("✅ Face recognizer ready (using shared instance)")
        
        # POSE ALERT FIX: Initialize pose analyzer for aggression detection
        if self.enable_pose:
            try:
                from ai_engine.models.pose_analyzer import PoseAnalyzer
                self.pose_analyzer = PoseAnalyzer()
                logger.info("✅ Pose analyzer ready for aggression detection")
            except Exception as e:
                logger.warning(f"Failed to initialize pose analyzer: {e}")
                self.pose_analyzer = None
        else:
            self.pose_analyzer = None
        
        # PERFORMANCE FIX: Track which heavy models are ready
        # Models load in background thread; process_frame gracefully skips unready ones
        self._models_ready = {
            'weapon_detector': False,
            'emotion_detector': False,
            'age_estimator': False,
            'pose_estimator': False,
        }
        self._stop_requested = False
        self._preload_thread = None
        
        logger.info(f"✅ DetectionPipeline initialized (emotion:{self.enable_emotion}, pose:{self.enable_pose}, weapon:{self.enable_weapon_detection})")
    
    def preload_models_background(self):
        """Start loading heavy models (weapon, emotion, pose) in a background thread.
        
        The detection loop can start immediately with face detection only.
        All heavy models load IN PARALLEL using ThreadPoolExecutor.
        As each finishes, it becomes available to process_frame().
        """
        # CRITICAL FIX: Reset stop flag from any previous camera session.
        # Since this pipeline is a shared singleton, a previous camera's stop()
        # would have set _stop_requested=True, blocking all future loading.
        self._stop_requested = False
        
        if self._preload_thread and self._preload_thread.is_alive():
            logger.debug("Background preload already running")
            return
        
        def _preload():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            # Build loader map: model_name → (loader_function, needs_available_check)
            loaders = {}
            
            if self.enable_weapon_detection and not self._stop_requested:
                loaders['weapon_detector'] = (self.model_manager.get_weapon_detector, True)
            if self.enable_emotion and not self._stop_requested:
                loaders['emotion_detector'] = (self.model_manager.get_emotion_detector, False)
            if self.enable_age and not self._stop_requested:
                loaders['age_estimator'] = (self.model_manager.get_age_estimator, False)
            if self.enable_pose and not self._stop_requested:
                loaders['pose_estimator'] = (self.model_manager.get_pose_estimator, False)
            
            if not loaders:
                logger.info("No background models to load")
                return
            
            logger.info(f"📦 Loading {len(loaders)} models in PARALLEL: {list(loaders.keys())}")
            
            def _load_model(name, loader_fn, check_available):
                """Load a single model (runs in its own thread)."""
                if self._stop_requested:
                    return name, False, "cancelled"
                try:
                    logger.info(f"📦 Loading {name}...")
                    result = loader_fn()
                    if check_available and not (result and result.available):
                        return name, False, "not available"
                    return name, True, "ready"
                except Exception as e:
                    return name, False, str(e)
            
            # Launch ALL loaders in parallel — each model_manager.get_*()
            # has its own lock, so concurrent loading is thread-safe
            max_workers = min(len(loaders), 4)
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="model-loader") as executor:
                futures = {
                    executor.submit(_load_model, name, fn, check): name
                    for name, (fn, check) in loaders.items()
                }
                
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        model_name, success, status = future.result()
                        if success:
                            self._models_ready[model_name] = True
                            logger.info(f"✅ Background: {model_name} ready")
                        else:
                            logger.warning(f"⚠️ Background: {model_name} — {status}")
                    except Exception as e:
                        logger.error(f"❌ Background: {name} failed: {e}")
            
            if self._stop_requested:
                logger.info("Background preload cancelled (camera stopped)")
            else:
                logger.info("✅ All background models loaded")
        
        self._preload_thread = threading.Thread(target=_preload, daemon=True, name="model-preloader")
        self._preload_thread.start()
    
    def request_stop(self):
        """Signal background model loading to stop (called when camera stops)."""
        self._stop_requested = True
    
    
    def detect_faces_only(self, frame: np.ndarray) -> 'DetectionResult':
        """
        TIER 1 — Fast tracking: detect face bounding boxes ONLY.
        
        Runs InsightFace.detect() ONLY (~30ms on CPU).
        NO weapon YOLO, NO embedding, NO watchlist match, NO emotion/age/pose.
        
        Weapon detection is handled by a separate background thread in
        DetectionProcessor to avoid blocking face tracking.
        
        Returns a lightweight DetectionResult with face bbox positions only,
        suitable for real-time annotated-stream overlay at ~30 FPS.
        """
        # Resize for inference
        optimized = CPUOptimizer.optimize_image_size(frame, max_dimension=640)
        orig_h, orig_w = frame.shape[:2]
        opt_h, opt_w = optimized.shape[:2]
        scale_x = orig_w / opt_w
        scale_y = orig_h / opt_h
        
        # --- Face detection (InsightFace, ~30ms) ---
        face_detector = self.model_manager.get_face_detector()
        
        # Use _get_faces directly to access det_score (detect() discards scores)
        raw_faces = face_detector._get_faces(optimized)
        
        # Scale face bboxes back to original resolution + extract confidence
        # Filter by live confidence_threshold from settings
        from config.config_manager import config_manager as _cfg
        _conf_thresh = _cfg.get().confidence_threshold

        scaled_faces = []
        face_scores = []
        for face in raw_faces:
            score = float(getattr(face, 'det_score', 0.0))
            if score < _conf_thresh:
                continue  # below live threshold — drop
            x1, y1, x2, y2 = map(int, face.bbox)
            scaled_faces.append((
                int(x1 * scale_x), int(y1 * scale_y),
                int(x2 * scale_x), int(y2 * scale_y)
            ))
            face_scores.append(score)
        
        # Build lightweight result (no weapon, no embedding, no emotion/pose)
        if not scaled_faces:
            return None
        
        # Build per-face data for ALL faces (with confidence)
        all_face_data = [
            FaceData(face_bbox=fb, confidence=sc)
            for fb, sc in zip(scaled_faces, face_scores)
        ]
        
        # Primary face = largest
        best_idx = max(range(len(scaled_faces)),
                       key=lambda i: (scaled_faces[i][2]-scaled_faces[i][0]) * (scaled_faces[i][3]-scaled_faces[i][1]))
        face_bbox = scaled_faces[best_idx]
        primary_confidence = face_scores[best_idx]
        
        return DetectionResult(
            has_face=len(scaled_faces) > 0,
            face_bbox=face_bbox,
            confidence=primary_confidence,
            all_faces=all_face_data,
            has_weapon=False,
            weapons_detected=[],
            metadata={"tracking_only": True, "face_count": len(scaled_faces)}
        )
    
    def process_frame(
        self,
        frame: np.ndarray,
        watchlist_embeddings: Optional[List[tuple]] = None,
        skip_motion_check: bool = False,
        confirmed_weapons: Optional[List[dict]] = None
    ) -> Optional[DetectionResult]:
        """
        Process single frame through complete pipeline
        
        Optimized detection order:
        1. Motion check (fast, skip if no motion)
        2. Weapon detection (from confirmed cache or direct YOLO)
        3. Face detection (medium speed)
        4. Face recognition & watchlist matching
        5. Emotion, pose (only if face detected)
        
        Args:
            frame: BGR image from camera
            watchlist_embeddings: List of (person_id, embedding) tuples
            skip_motion_check: If True, skip motion detection
            confirmed_weapons: Pre-confirmed weapons from weapon thread
                (multi-frame soft-decay verified). If provided, skips
                direct YOLO to prevent single-frame false positives.
            
        Returns:
            DetectionResult or None if no detection
        """
        # Step 0: Check for motion first (optimization)
        if not skip_motion_check and not self.motion_detector.has_motion(frame):
            return None
        
        # Optimize frame size for AI inference
        optimized_frame = CPUOptimizer.optimize_image_size(frame, max_dimension=640)
        
        # COORDINATE FIX: Compute scale factor to map coordinates back to original frame.
        # All AI models run on the resized (640px) frame, but the annotated stream
        # draws on the original resolution frame. We must scale all coordinates back.
        orig_h, orig_w = frame.shape[:2]
        opt_h, opt_w = optimized_frame.shape[:2]
        scale_x = orig_w / opt_w
        scale_y = orig_h / opt_h
        
        # Step 1: WEAPON DETECTION
        # Use confirmed_weapons from weapon thread (multi-frame verified) if available.
        # Only fall back to direct YOLO when no weapon cache is provided.
        # This prevents single-frame false positives from triggering alerts.
        weapons_detected = []
        has_weapon = False
        
        if confirmed_weapons is not None:
            # Use pre-confirmed weapons from weapon thread (already scaled to original coords)
            weapons_detected = confirmed_weapons
            has_weapon = len(weapons_detected) > 0
            if has_weapon:
                logger.warning(f"⚠️ WEAPON DETECTED: {len(weapons_detected)} weapon(s) in frame")
        # FALSE POSITIVE FIX: Removed fallback direct YOLO detection.
        # Weapon detection MUST go through the weapon thread's multi-frame
        # confirmation to prevent single-frame false positives from producing
        # red bboxes and false alerts. If confirmed_weapons is None, no
        # weapons are reported (the weapon thread handles all detection).
        
        # Step 2: Detect faces (ALWAYS run, even if weapon detected)
        # Use _get_faces() to access det_score (detect() discards it)
        face_detector = self.model_manager.get_face_detector()
        raw_faces = face_detector._get_faces(optimized_frame)
        self.model_manager.increment_inference_count('face_detector')
        
        # Extract bboxes and det_scores from InsightFace face objects.
        # Filter by live confidence_threshold and apply IoU NMS.
        from config.config_manager import config_manager as _cfg
        _live_cfg = _cfg.get()
        _conf_thresh = _live_cfg.confidence_threshold
        _iou_thresh  = _live_cfg.iou_threshold

        faces = []
        face_det_scores = []
        for face in raw_faces:
            score = float(getattr(face, 'det_score', 0.0))
            if score < _conf_thresh:
                continue  # below live confidence threshold
            bbox = tuple(map(int, face.bbox))
            faces.append(bbox)
            face_det_scores.append(score)

        # Post-inference IoU NMS — suppress overlapping boxes above iou_threshold
        if len(faces) > 1:
            faces, face_det_scores = self._nms_faces(faces, face_det_scores, _iou_thresh)
        
        # COORDINATE FIX: Scale weapon bboxes to original coordinates
        # ONLY needed when weapons came from direct YOLO (optimized frame coords).
        # confirmed_weapons from weapon thread are ALREADY in original coords.
        if confirmed_weapons is not None:
            scaled_weapons = weapons_detected  # Already scaled by weapon thread
        else:
            scaled_weapons = []
            for w in weapons_detected:
                wb = w['bbox']
                scaled_w = dict(w)
                scaled_w['bbox'] = [
                    int(wb[0] * scale_x), int(wb[1] * scale_y),
                    int(wb[2] * scale_x), int(wb[3] * scale_y)
                ]
                scaled_weapons.append(scaled_w)
        
        if len(faces) == 0:
            # No face — return weapon-only result if weapons found
            return DetectionResult(
                has_face=False,
                has_weapon=has_weapon,
                weapons_detected=scaled_weapons
            )
        
        # ============================================
        # MULTI-FACE: Process ALL detected faces
        # ============================================
        all_face_data = []
        
        # Get emotion/age detectors once (shared across all faces)
        emotion_detector = None
        if self.enable_emotion and self._models_ready.get('emotion_detector', False):
            emotion_detector = self.model_manager.get_emotion_detector()
        
        age_estimator = None
        if self.enable_age and self._models_ready.get('age_estimator', False):
            age_estimator = self.model_manager.get_age_estimator()
        
        for face_idx, face_bbox in enumerate(faces):
            fx1, fy1, fx2, fy2 = face_bbox
            face_crop = optimized_frame[fy1:fy2, fx1:fx2]
            
            if face_crop.size == 0:
                continue
            
            # Scale bbox to original frame coordinates
            scaled_bbox = (
                int(fx1 * scale_x), int(fy1 * scale_y),
                int(fx2 * scale_x), int(fy2 * scale_y)
            )
            
            # Get InsightFace det_score for this face
            det_score = face_det_scores[face_idx] if face_idx < len(face_det_scores) else 0.0
            
            # Extract embedding
            embedding = self.face_recognizer.extract_embedding(optimized_frame, face_bbox)
            
            # Watchlist matching
            matched_id = None
            matched_name = None
            max_confidence = 0.0
            
            if embedding is not None and watchlist_embeddings:
                for person_id, watch_emb, person_name in watchlist_embeddings:
                    is_match, similarity = self.face_recognizer.compare_embeddings(
                        embedding, watch_emb
                    )
                    if is_match and similarity > max_confidence:
                        matched_id = person_id
                        matched_name = person_name
                        max_confidence = similarity
                
                if matched_id:
                    logger.info(f"✅ WATCHLIST MATCH: person_id={matched_id}, name={matched_name}, confidence={max_confidence:.3f}")
            
            # Emotion detection (per face)
            face_emotion = None
            if emotion_detector:
                try:
                    face_emotion = emotion_detector.predict_with_context(optimized_frame, face_bbox)
                    self.model_manager.increment_inference_count('emotion_detector')
                except Exception:
                    pass
            
            # Age estimation (per face)
            face_age = None
            if age_estimator:
                try:
                    face_age = age_estimator.estimate(face_crop)
                    self.model_manager.increment_inference_count('age_estimator')
                except Exception:
                    pass
            
            # Face quality
            face_quality = self._calculate_face_quality(face_bbox, optimized_frame.shape)
            
            # CONFIDENCE FIX: Use the higher of det_score or watchlist similarity
            # - For watchlist matches: max_confidence = similarity (0.4-0.7)
            # - For unmatched faces: max_confidence = 0.0, so det_score (0.7-0.99) is used
            face_confidence = max(det_score, max_confidence)
            
            all_face_data.append(FaceData(
                face_bbox=scaled_bbox,
                face_embedding=embedding,
                emotion=face_emotion,
                age=face_age,
                matched_person_id=matched_id,
                matched_person_name=matched_name,
                confidence=face_confidence,
                face_quality_score=face_quality,
                is_real_face=True
            ))
        
        if not all_face_data and not has_weapon:
            return DetectionResult(has_face=False)
        
        # Use largest face for backward-compat scalar fields
        primary = None
        if all_face_data:
            primary = max(all_face_data, key=lambda f: (
                (f.face_bbox[2] - f.face_bbox[0]) * (f.face_bbox[3] - f.face_bbox[1])
            ))
        
        # Pose estimation (body-level, not per-face)
        pose_data = None
        body_orientation = None
        action = None
        pose_alert = False
        pose_type = None
        pose_confidence_val = 0.0
        pose_indicators = []
        
        if self.enable_pose and self._models_ready.get('pose_estimator', False):
            try:
                pose_estimator = self.model_manager.get_pose_estimator()
                pose_data = pose_estimator.detect(optimized_frame)
                self.model_manager.increment_inference_count('pose_estimator')
                
                if pose_data:
                    body_orientation = pose_estimator.get_body_orientation(pose_data)
                    action = pose_estimator.detect_action(pose_data)
                    
                    if self.pose_analyzer:
                        try:
                            aggression_analysis = self.pose_analyzer.analyze_aggression(pose_data)
                            if aggression_analysis['is_aggressive']:
                                pose_alert = True
                                pose_type = aggression_analysis['pose_type']
                                pose_confidence_val = aggression_analysis['confidence']
                                pose_indicators = aggression_analysis['indicators']
                                logger.warning(
                                    f"⚠️ AGGRESSIVE POSE DETECTED: {pose_type} "
                                    f"(confidence: {pose_confidence_val:.2f}, "
                                    f"indicators: {', '.join(pose_indicators)})"
                                )
                        except Exception as analyzer_error:
                            logger.debug(f"Pose analysis error: {analyzer_error}")
            except Exception as e:
                logger.error(f"Pose detection error (continuing without pose): {e}")
                pose_data = None
        
        # Scale pose keypoints to original frame coordinates
        scaled_pose = None
        if pose_data and 'keypoints' in pose_data:
            scaled_kps = {}
            for idx, kp in pose_data['keypoints'].items():
                scaled_kps[idx] = {
                    'x': kp['x'] * scale_x,
                    'y': kp['y'] * scale_y,
                    'z': kp.get('z', 0),
                    'visibility': kp.get('visibility', 0)
                }
            scaled_pose = {'keypoints': scaled_kps}
            if 'raw_landmarks' in pose_data:
                scaled_pose['raw_landmarks'] = pose_data['raw_landmarks']
        elif pose_data:
            scaled_pose = pose_data
        
        # Determine detection type and priority
        detection_type = "normal_face"
        priority = "LOW"
        any_matched = any(f.matched_person_id is not None for f in all_face_data)
        any_angry = any(f.emotion in ['angry', 'fear', 'disgust'] for f in all_face_data if f.emotion)
        
        if any_matched:
            detection_type = "watchlist_match"
            priority = "CRITICAL"
        elif has_weapon:
            detection_type = "face_with_weapon"
            priority = "CRITICAL"
        elif any_angry:
            detection_type = "suspicious_emotion"
            priority = "MEDIUM"
        elif action and action in ['fighting', 'running']:
            detection_type = "suspicious_behavior"
            priority = "HIGH"
        
        return DetectionResult(
            has_face=len(all_face_data) > 0,
            face_bbox=primary.face_bbox if primary else None,
            face_embedding=primary.face_embedding if primary else None,
            face_quality_score=primary.face_quality_score if primary else 0.0,
            is_real_face=True,
            emotion=primary.emotion if primary else None,
            age=primary.age if primary else None,
            pose_keypoints=scaled_pose,
            body_orientation=body_orientation,
            action=action,
            matched_person_id=primary.matched_person_id if primary else None,
            matched_person_name=primary.matched_person_name if primary else None,
            confidence=primary.confidence if primary else 0.0,
            all_faces=all_face_data,
            has_weapon=has_weapon,
            weapons_detected=scaled_weapons,
            pose_alert=pose_alert,
            pose_type=pose_type,
            pose_confidence=pose_confidence_val,
            pose_indicators=pose_indicators,
            metadata={
                "face_count": len(all_face_data),
                "frame_size": (orig_h, orig_w),
                "detection_type": detection_type,
                "priority": priority
            }
        )
    
    @staticmethod
    def _nms_faces(
        boxes: list,
        scores: list,
        iou_threshold: float
    ):
        """Lightweight IoU-based NMS for face bounding boxes.

        Keeps the highest-scoring box and suppresses any other box whose
        overlap with it exceeds `iou_threshold`. Pure Python — no extra deps.

        Args:
            boxes:         List of (x1, y1, x2, y2) tuples in original-frame coords.
            scores:        Corresponding det_score for each box.
            iou_threshold: Suppress boxes with IoU > this value (from live config).

        Returns:
            (kept_boxes, kept_scores)
        """
        if not boxes:
            return boxes, scores

        # Sort indices by score descending
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        keep_idx = []

        while order:
            best = order.pop(0)
            keep_idx.append(best)
            b = boxes[best]
            surviving = []
            for j in order:
                a = boxes[j]
                # Intersection
                ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
                ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_a = (a[2] - a[0]) * (a[3] - a[1])
                area_b = (b[2] - b[0]) * (b[3] - b[1])
                union = area_a + area_b - inter
                iou = inter / union if union > 0 else 0.0
                if iou <= iou_threshold:
                    surviving.append(j)
            order = surviving

        kept_boxes  = [boxes[i]  for i in keep_idx]
        kept_scores = [scores[i] for i in keep_idx]
        return kept_boxes, kept_scores

    def _calculate_face_quality(
        self,
        face_bbox: tuple,
        frame_shape: tuple
    ) -> float:
        """
        Calculate face quality score based on size and position
        
        Returns:
            Score between 0 and 1
        """
        x1, y1, x2, y2 = face_bbox
        h, w = frame_shape[:2]
        
        face_w = x2 - x1
        face_h = y2 - y1
        face_area = face_w * face_h
        frame_area = h * w
        
        # Size score (faces should be 5-50% of frame)
        size_ratio = face_area / frame_area
        if size_ratio < 0.05:
            size_score = size_ratio / 0.05
        elif size_ratio > 0.5:
            size_score = (1.0 - size_ratio) * 2
        else:
            size_score = 1.0
        
        # Position score (faces should be in center 80% of frame)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        frame_center_x = w / 2
        frame_center_y = h / 2
        
        dist_from_center = np.sqrt(
            ((center_x - frame_center_x) / w) ** 2 +
            ((center_y - frame_center_y) / h) ** 2
        )
        
        position_score = max(0, 1.0 - dist_from_center * 2)
        
        # Combined score
        quality = (size_score + position_score) / 2
        
        return min(1.0, max(0.0, quality))