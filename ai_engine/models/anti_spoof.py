"""
Anti-spoofing detection using DeepFace (MiniFASNet)
"""
import cv2
import numpy as np
from typing import Tuple
from loguru import logger

# Try to import DeepFace - may fail with newer TensorFlow/Keras versions
DEEPFACE_AVAILABLE = False
DeepFace = None
try:
    from deepface import DeepFace as _DeepFace
    DeepFace = _DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"DeepFace not available for anti-spoofing: {e}")

class AntiSpoofDetector:
    def __init__(self):
        """Initialize anti-spoofing detector"""
        self.available = DEEPFACE_AVAILABLE
        if not self.available:
            logger.warning("AntiSpoofDetector in fallback mode (DeepFace not available)")
    
    def predict(
        self,
        image: np.ndarray,
        face_bbox: Tuple[int, int, int, int]
    ) -> Tuple[bool, float]:
        """
        Predict if face is real or spoofed
        
        Args:
            image: Full BGR image
            face_bbox: (x1, y1, x2, y2)
            
        Returns:
            (is_real, confidence_score)
        """
        # Fallback when DeepFace is not available
        if not self.available or DeepFace is None:
            return True, 0.5  # Assume real by default
        
        try:
            x1, y1, x2, y2 = face_bbox
            # Ensure bbox is within image bounds
            h, w = image.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            # Crop the face
            face_crop = image[y1:y2, x1:x2]
            
            if face_crop.size == 0:
                return True, 0.0
                
            # Use DeepFace's built-in anti-spoofing (MiniFASNet)
            results = DeepFace.extract_faces(
                img_path=face_crop,
                enforce_detection=False,
                anti_spoofing=True,
                align=False
            )
            
            if results:
                result = results[0]
                is_real = result.get("is_real", True)
                confidence = result.get("antispoof_score", 0.95 if is_real else 0.05)
                return is_real, confidence
                
            return True, 0.5
            
        except Exception as e:
            return True, 0.5
    
    def predict_from_crop(self, face_crop: np.ndarray) -> bool:
        """Predict from cropped face image"""
        if not self.available or DeepFace is None:
            return True
        
        try:
            results = DeepFace.extract_faces(
                img_path=face_crop,
                enforce_detection=False,
                anti_spoofing=True,
                align=False
            )
            if results:
                return results[0].get("is_real", True)
            return True
        except:
            return True