"""
Age estimation (simplified version using DeepFace)
"""
import cv2
import numpy as np
from typing import Optional
from loguru import logger

# Try to import DeepFace - may fail with newer TensorFlow/Keras versions
DEEPFACE_AVAILABLE = False
DeepFace = None
try:
    from deepface import DeepFace as _DeepFace
    DeepFace = _DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError as e:
    logger.debug(f"DeepFace not available for age estimation: {e}")

class AgeEstimator:
    def __init__(self):
        """Initialize age estimator"""
        self.available = DEEPFACE_AVAILABLE
        if not self.available:
            logger.debug("AgeEstimator in fallback mode (DeepFace not available)")
    
    def estimate(self, face_image: np.ndarray) -> Optional[int]:
        """
        Estimate age from face image
        
        Args:
            face_image: Cropped face image (BGR)
            
        Returns:
            Estimated age or None
        """
        # Fallback when DeepFace is not available
        if not self.available or DeepFace is None:
            return None
        
        try:
            # Convert to RGB
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            
            # Analyze
            result = DeepFace.analyze(
                rgb_image,
                actions=['age'],
                enforce_detection=False,
                silent=True
            )
            
            if isinstance(result, list):
                result = result[0]
            
            return int(result['age'])
            
        except Exception as e:
            logger.debug(f"Age estimation failed: {e}")
            return None
    
    def estimate_age_range(self, face_image: np.ndarray) -> Optional[str]:
        """
        Estimate age range category
        
        Returns:
            Age range string (child, teen, adult, senior) or None
        """
        age = self.estimate(face_image)
        
        if age is None:
            return None
        
        if age < 13:
            return "child"
        elif age < 20:
            return "teen"
        elif age < 60:
            return "adult"
        else:
            return "senior"