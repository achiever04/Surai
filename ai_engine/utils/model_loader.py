"""
Lazy model loading utilities
"""
from typing import Dict, Any, Optional
from pathlib import Path
import torch
from loguru import logger


class ModelLoader:
    """Lazy load AI models to save memory"""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def load_face_detector(cls) -> 'FaceDetector':
        """Load face detector (singleton)"""
        if 'face_detector' not in cls._instances:
            from ai_engine.models.face_detector import FaceDetector
            logger.info("Loading face detector...")
            cls._instances['face_detector'] = FaceDetector(min_confidence=0.9)
        
        return cls._instances['face_detector']
    
    @classmethod
    def load_face_recognizer(cls) -> 'FaceRecognizer':
        """Load face recognizer (singleton)"""
        if 'face_recognizer' not in cls._instances:
            from ai_engine.models.face_recognizer import FaceRecognizer
            logger.info("Loading face recognizer...")
            cls._instances['face_recognizer'] = FaceRecognizer(model_name="buffalo_l")
        
        return cls._instances['face_recognizer']
    
    @classmethod
    def load_emotion_detector(cls) -> 'EmotionDetector':
        """Load emotion detector (singleton)"""
        if 'emotion_detector' not in cls._instances:
            from ai_engine.models.emotion_detector import EmotionDetector
            logger.info("Loading emotion detector...")
            cls._instances['emotion_detector'] = EmotionDetector()
        
        return cls._instances['emotion_detector']
    
    @classmethod
    def load_pose_estimator(cls) -> 'PoseEstimator':
        """Load pose estimator (singleton)"""
        if 'pose_estimator' not in cls._instances:
            from ai_engine.models.pose_estimator import PoseEstimator
            logger.info("Loading pose estimator...")
            cls._instances['pose_estimator'] = PoseEstimator(min_detection_confidence=0.5)
        
        return cls._instances['pose_estimator']
    
    @classmethod
    def load_anti_spoof(cls) -> 'AntiSpoofDetector':
        """Load anti-spoofing detector (singleton)"""
        if 'anti_spoof' not in cls._instances:
            from ai_engine.models.anti_spoof import AntiSpoofDetector
            logger.info("Loading anti-spoof detector...")
            cls._instances['anti_spoof'] = AntiSpoofDetector()
        
        return cls._instances['anti_spoof']
    
    @classmethod
    def load_age_estimator(cls) -> 'AgeEstimator':
        """Load age estimator (singleton)"""
        if 'age_estimator' not in cls._instances:
            from ai_engine.models.age_estimator import AgeEstimator
            logger.info("Loading age estimator...")
            cls._instances['age_estimator'] = AgeEstimator()
        
        return cls._instances['age_estimator']
    
    @classmethod
    def unload_model(cls, model_name: str):
        """Unload specific model to free memory"""
        if model_name in cls._instances:
            logger.info(f"Unloading model: {model_name}")
            del cls._instances[model_name]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    @classmethod
    def unload_all(cls):
        """Unload all models"""
        logger.info("Unloading all models...")
        cls._instances.clear()
        
        import gc
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    @classmethod
    def get_loaded_models(cls) -> list:
        """Get list of currently loaded models"""
        return list(cls._instances.keys())