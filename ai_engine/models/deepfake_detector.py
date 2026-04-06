"""
Deepfake Detection Model

Detects if a face image is a deepfake/synthetic using deep learning.
Uses MesoNet architecture for lightweight, real-time detection.

References:
- MesoNet: https://github.com/DariusAf/MesoNet
- Deepfake Detection Challenge: https://www.kaggle.com/c/deepfake-detection-challenge
"""
import cv2
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger
import tensorflow as tf


class DeepfakeDetector:
    """
    Deepfake detection using MesoNet architecture
    
    Note: This is a placeholder implementation. For production:
    1. Download pre-trained MesoNet weights
    2. Or train custom model on deepfake dataset
    3. Or use commercial API (e.g., Microsoft Video Authenticator)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize deepfake detector
        
        Args:
            model_path: Path to pre-trained model weights
        """
        self.model = None
        self.enabled = False
        
        try:
            if model_path:
                self.model = tf.keras.models.load_model(model_path)
                self.enabled = True
                logger.info("Deepfake detector loaded successfully")
            else:
                logger.warning("Deepfake detector disabled - no model path provided")
        
        except Exception as e:
            logger.error(f"Failed to load deepfake detector: {e}")
            self.enabled = False
    
    def detect_deepfake(self, face_image: np.ndarray) -> Dict[str, Any]:
        """
        Detect if face is deepfake
        
        Args:
            face_image: Face ROI image (BGR)
        
        Returns:
            {
                'is_deepfake': bool,
                'confidence': float (0-1),
                'method': str
            }
        """
        if not self.enabled or self.model is None:
            # Return default (assume real) if detector not available
            return {
                'is_deepfake': False,
                'confidence': 0.0,
                'method': 'disabled'
            }
        
        try:
            # Preprocess image
            face_resized = cv2.resize(face_image, (256, 256))
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            face_normalized = face_rgb / 255.0
            face_batch = np.expand_dims(face_normalized, axis=0)
            
            # Predict
            prediction = self.model.predict(face_batch, verbose=0)[0][0]
            
            # Threshold: >0.5 = deepfake
            is_deepfake = prediction > 0.5
            confidence = float(prediction) if is_deepfake else float(1 - prediction)
            
            return {
                'is_deepfake': bool(is_deepfake),
                'confidence': confidence,
                'method': 'mesonet'
            }
        
        except Exception as e:
            logger.error(f"Deepfake detection error: {e}")
            return {
                'is_deepfake': False,
                'confidence': 0.0,
                'method': 'error'
            }
    
    def is_available(self) -> bool:
        """Check if detector is available"""
        return self.enabled and self.model is not None


# PERFORMANCE FIX: Lazy-loading proxy instead of eager module-level instantiation
# Previously: deepfake_detector = DeepfakeDetector()  ← imported TensorFlow (~500MB, ~5-10s) at IMPORT TIME
# Now: only loads when first accessed
class _LazyDeepfakeDetector:
    """Proxy that defers DeepfakeDetector creation until first use"""
    def __init__(self):
        self._instance = None
    
    def _get_instance(self):
        if self._instance is None:
            self._instance = DeepfakeDetector()
        return self._instance
    
    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

deepfake_detector = _LazyDeepfakeDetector()
