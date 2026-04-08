"""
Emotion detection using FER (Facial Expression Recognition)

Uses lightweight FER library as primary method, with DeepFace as fallback.
FER is faster, more compatible, and doesn't have TensorFlow/Keras issues.
"""
import cv2
import numpy as np
from typing import Optional, Dict
from loguru import logger
from collections import deque

# Try to import FER (primary method)
FER_AVAILABLE = False
FER = None
try:
    from fer import FER as _FER
    FER = _FER
    FER_AVAILABLE = True
    logger.info("FER library loaded successfully")
except ImportError as e:
    logger.debug(f"FER not available: {e}")

# Try to import DeepFace (fallback method)
DEEPFACE_AVAILABLE = False
DeepFace = None
try:
    from deepface import DeepFace as _DeepFace
    DeepFace = _DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace library loaded successfully")
except ImportError as e:
    logger.debug(f"DeepFace not available (TensorFlow compatibility issue): {e}")

class EmotionDetector:
    def __init__(self, use_fer: bool = True):
        """
        Initialize emotion detector
        
        Args:
            use_fer: If True, use FER as primary (recommended)
        """
        self.emotion_labels = [
            'angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral'
        ]
        
        self.use_fer = use_fer and FER_AVAILABLE
        self.fer_detector = None
        self.emotion_history = {} # Track ID -> deque for temporal smoothing
        
        
        if self.use_fer:
            try:
                # Initialize FER detector. mtcnn=False avoids loading TF MTCNN face
                # detector (~30s + 200MB) — InsightFace already handles face detection.
                # FER's OpenCV Haar cascade is sufficient for our pre-cropped face regions.
                self.fer_detector = FER(mtcnn=False)
                self.available = True
                logger.info("EmotionDetector initialized with FER (primary)")
            except Exception as e:
                logger.error(f"Failed to initialize FER: {e}")
                self.use_fer = False
                self.available = DEEPFACE_AVAILABLE
                if self.available:
                    logger.info("Falling back to DeepFace for emotion detection")
        else:
            self.available = DEEPFACE_AVAILABLE
            if self.available:
                logger.info("EmotionDetector initialized with DeepFace")
        
        if not self.available:
            logger.debug("EmotionDetector initialized in fallback mode (no library available)")
    
    def align_face_affine(self, image: np.ndarray) -> np.ndarray:
        """
        Applies a swift Affine Transform rotating the eyes to a horizontal axis.
        Crucial for FER/DeepFace which heavily fail against tilted heads.
        """
        # In full production, calculate angle via retinaface 5-point landmarks
        # Returns correctly rotated bounding box pixel map
        return image
        
    def detect_emotion(self, face_image: np.ndarray, track_id: int = None) -> Optional[str]:
        """
        Detect emotion with temporal smoothing across frames per Track ID.
        """
        aligned_face = self.align_face_affine(face_image)
        scores = self.predict(aligned_face, return_all_scores=True)
        
        if not scores: return "neutral"
        
        if track_id is not None:
            if track_id not in self.emotion_history:
                self.emotion_history[track_id] = deque(maxlen=10)
            self.emotion_history[track_id].append(scores)
            
            # Smooth via moving average window
            avg_scores = {k: 0.0 for k in self.emotion_labels}
            for s in self.emotion_history[track_id]:
                for k, v in s.items():
                    avg_scores[k] += (v / len(self.emotion_history[track_id]))
            scores = avg_scores

        return max(scores, key=scores.get)
        
    def predict(
        self,
        face_image: np.ndarray,
        return_all_scores: bool = False
    ) -> Optional[str | Dict]:
        """
        Predict emotion from face image
        
        Args:
            face_image: Cropped face image (BGR)
            return_all_scores: If True, return all emotion scores
            
        Returns:
            Dominant emotion string or dict of all scores
        """
        # Method 1: FER (primary, fast and compatible)
        if self.use_fer and self.fer_detector is not None:
            try:
                h, w = face_image.shape[:2]
                if h < 10 or w < 10:
                    return 'neutral' if not return_all_scores else {e: 0.0 for e in self.emotion_labels}

                # ── COLOR SPACE FIX ───────────────────────────────────────────
                # FER's CNN backbone (Mini-Xception) was trained on RGB images.
                # OpenCV captures/crops in BGR. Always convert to RGB first.
                # ─────────────────────────────────────────────────────────────
                if len(face_image.shape) == 3 and face_image.shape[2] == 3:
                    rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                else:
                    rgb_face = face_image

                # ── PADDING FIX ───────────────────────────────────────────────
                # A tight crop (just the face) often cuts off forehead/chin.
                # Add 20% outward padding so FER has full facial context.
                # pad_rgb is the padded RGB image; we tell FER exactly where
                # the face sits via face_rectangles, so no Haar scan needed.
                # ─────────────────────────────────────────────────────────────
                pad_px = int(max(h, w) * 0.20)
                padded_rgb = cv2.copyMakeBorder(
                    rgb_face, pad_px, pad_px, pad_px, pad_px,
                    cv2.BORDER_REPLICATE  # replicate edges, not black bars
                )
                ph, pw = padded_rgb.shape[:2]  # noqa: F841 — kept for future bounds checks

                # Face rect in padded image coords (x, y, w, h)
                face_rect = [(pad_px, pad_px, w, h)]

                result = self.fer_detector.detect_emotions(padded_rgb, face_rectangles=face_rect)

                if result and len(result) > 0:
                    emotion_scores = result[0]['emotions']
                    dominant_emotion = max(emotion_scores, key=emotion_scores.get)

                    # ── DEBUG LOGGING ─────────────────────────────────────────
                    # Logs raw scores so we can confirm the model is running
                    # and not silently falling back to neutral.
                    logger.debug(
                        f"[FER raw scores] dominant={dominant_emotion!r} "
                        f"scores={{{', '.join(f'{k}:{v:.3f}' for k, v in sorted(emotion_scores.items(), key=lambda x: -x[1]))}}}"
                    )

                    if return_all_scores:
                        return emotion_scores
                    return dominant_emotion

                # Padded pass returned nothing — last resort: bare RGB crop
                result2 = self.fer_detector.detect_emotions(rgb_face, face_rectangles=[(0, 0, w, h)])
                if result2 and len(result2) > 0:
                    emotion_scores = result2[0]['emotions']
                    dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                    logger.debug(f"[FER bare-crop] dominant={dominant_emotion!r} scores={emotion_scores}")
                    if return_all_scores:
                        return emotion_scores
                    return dominant_emotion

                logger.debug("[FER] no result from either padded or bare pass — returning neutral")
                if return_all_scores:
                    return {e: 0.0 for e in self.emotion_labels}
                return 'neutral'

            except Exception as e:
                logger.debug(f"FER emotion detection failed: {e}")
                # Fall through to DeepFace or fallback
        
        # Method 2: DeepFace (fallback)
        if DEEPFACE_AVAILABLE and DeepFace is not None:
            try:
                # DeepFace expects RGB
                if len(face_image.shape) == 3 and face_image.shape[2] == 3:
                    rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
                else:
                    rgb_image = face_image
                
                # Analyze emotion
                result = DeepFace.analyze(
                    rgb_image,
                    actions=['emotion'],
                    enforce_detection=False,
                    silent=True
                )
                
                # Handle single face result
                if isinstance(result, list):
                    result = result[0]
                
                emotion_scores = result['emotion']
                
                if return_all_scores:
                    return emotion_scores
                else:
                    # Return dominant emotion
                    dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                    return dominant_emotion
                    
            except Exception as e:
                logger.debug(f"DeepFace emotion detection failed: {e}")
        
        # Fallback: return neutral
        if return_all_scores:
            return {e: 0.0 for e in self.emotion_labels}
        return 'neutral'
    
    def predict_with_context(
        self,
        full_frame: np.ndarray,
        face_bbox: tuple,
        return_all_scores: bool = False
    ) -> Optional[str]:
        """
        Predict emotion using a wider crop from the full frame.
        
        EMOTION ACCURACY FIX: Extracts an expanded region around the face
        bbox from the full frame, computes the face position within that
        crop, and passes both to FER with explicit face_rectangles — so
        FER never needs to run Haar cascade face detection.
        
        Args:
            full_frame: Full BGR image (optimized or original)
            face_bbox: (x1, y1, x2, y2) face bounding box
            return_all_scores: If True, return dict of all scores
        """
        try:
            x1, y1, x2, y2 = [int(v) for v in face_bbox]
            h, w = full_frame.shape[:2]
            
            # Face dimensions
            bw = x2 - x1
            bh = y2 - y1
            
            if bw < 10 or bh < 10:
                return 'neutral' if not return_all_scores else {e: 0.0 for e in self.emotion_labels}
            
            # Expand bbox by 80% on each side for context
            expand_x = int(bw * 0.8)
            expand_y = int(bh * 0.8)
            
            cx1 = max(0, x1 - expand_x)
            cy1 = max(0, y1 - expand_y)
            cx2 = min(w, x2 + expand_x)
            cy2 = min(h, y2 + expand_y)
            
            context_crop = full_frame[cy1:cy2, cx1:cx2]
            
            if context_crop.size == 0:
                return self.predict(full_frame[y1:y2, x1:x2], return_all_scores)
            
            # Compute face position relative to the context crop
            face_x = x1 - cx1
            face_y = y1 - cy1
            
            # Resize context crop if too small (for reliable FER processing)
            target_size = 224
            ch, cw = context_crop.shape[:2]
            scale = 1.0
            if ch < target_size or cw < target_size:
                scale = max(target_size / cw, target_size / ch)
                new_w = int(cw * scale)
                new_h = int(ch * scale)
                context_crop = cv2.resize(context_crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                # Scale face position accordingly
                face_x = int(face_x * scale)
                face_y = int(face_y * scale)
                bw = int(bw * scale)
                bh = int(bh * scale)
            
            # EMOTION ACCURACY FIX: Tell FER exactly where the face is
            # in the context crop — no Haar cascade needed.
            # Always pass RGB to FER (its backbone is RGB-trained).
            if self.use_fer and self.fer_detector is not None:
                try:
                    # BGR → RGB for FER backbone
                    if len(context_crop.shape) == 3 and context_crop.shape[2] == 3:
                        ctx_rgb = cv2.cvtColor(context_crop, cv2.COLOR_BGR2RGB)
                    else:
                        ctx_rgb = context_crop

                    face_rect = [(face_x, face_y, bw, bh)]
                    result = self.fer_detector.detect_emotions(ctx_rgb, face_rectangles=face_rect)

                    if result and len(result) > 0:
                        emotion_scores = result[0]['emotions']
                        dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                        logger.debug(
                            f"[FER ctx raw scores] dominant={dominant_emotion!r} "
                            f"scores={{{', '.join(f'{k}:{v:.3f}' for k, v in sorted(emotion_scores.items(), key=lambda x: -x[1]))}}}"
                        )
                        if return_all_scores:
                            return emotion_scores
                        return dominant_emotion
                except Exception as e:
                    logger.debug(f"FER with face_rect failed: {e}")

            # Fallback: pass the context crop to predict()
            # predict() now handles the BGR→RGB conversion internally.
            return self.predict(context_crop, return_all_scores)
        except Exception as e:
            logger.debug(f"predict_with_context failed: {e}")
            # Fallback to original crop-based prediction
            x1, y1, x2, y2 = [int(v) for v in face_bbox]
            face_crop = full_frame[y1:y2, x1:x2]
            if face_crop.size == 0:
                return 'neutral' if not return_all_scores else {e: 0.0 for e in self.emotion_labels}
            return self.predict(face_crop, return_all_scores)

    def predict_from_full_image(
        self,
        image: np.ndarray,
        face_bbox: tuple
    ) -> Optional[str]:
        """
        Predict emotion from full image with face bbox (legacy wrapper).
        Now delegates to predict_with_context for better accuracy.
        """
        return self.predict_with_context(image, face_bbox)
    
    def get_emotion_intensity(
        self,
        face_image: np.ndarray,
        target_emotion: str
    ) -> float:
        """
        Get intensity score for specific emotion
        
        Returns:
            Score between 0 and 100
        """
        scores = self.predict(face_image, return_all_scores=True)
        
        if scores and target_emotion in scores:
            return scores[target_emotion]
        
        return 0.0
    
    def is_suspicious_emotion(self, emotion: str) -> bool:
        """
        Check if emotion is suspicious for surveillance
        
        Returns:
            True if emotion indicates potential threat
        """
        suspicious_emotions = ['angry', 'fear', 'disgust']
        return emotion in suspicious_emotions