"""
Singleton AI Model Manager

This module provides a thread-safe singleton that loads AI models ONCE
and shares them across all camera detection threads, preventing memory
overload and system crashes.

Key Features:
- Thread-safe singleton pattern
- Lazy loading with individual locks per model
- Memory-efficient model sharing
- Centralized model lifecycle management
"""
import threading
import time
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
from loguru import logger
import psutil
import os


class AIModelManager:
    """
    Singleton manager for all AI models.
    Ensures each model is loaded only once and shared across all cameras.
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
        
        # Model instances (lazy loaded)
        self._face_detector = None
        self._face_recognizer = None
        self._emotion_detector = None
        self._pose_estimator = None
        self._weapon_detector = None
        self._anti_spoof = None
        self._age_estimator = None
        self._deepfake_detector = None
        self._object_detector = None
        
        # Shared detection pipeline (singleton across all consumers)
        self._detection_pipeline = None
        
        # Individual locks for each model (prevents blocking)
        self._face_detector_lock = threading.Lock()
        self._face_recognizer_lock = threading.Lock()
        self._emotion_detector_lock = threading.Lock()
        self._pose_estimator_lock = threading.Lock()
        self._weapon_detector_lock = threading.Lock()
        self._anti_spoof_lock = threading.Lock()
        self._age_estimator_lock = threading.Lock()
        self._deepfake_detector_lock = threading.Lock()
        self._object_detector_lock = threading.Lock()
        self._detection_pipeline_lock = threading.Lock()
        
        # Model loading status
        self._models_loaded = {
            'face_detector': False,
            'face_recognizer': False,
            'emotion_detector': False,
            'pose_estimator': False,
            'weapon_detector': False,
            'anti_spoof': False,
            'age_estimator': False,
            'deepfake_detector': False,
            'object_detector': False
        }
        
        # Performance monitoring
        self._load_times = {}
        self._inference_counts = {}
        
        self._initialized = True
        logger.info("AIModelManager singleton initialized")
    
    def get_face_detector(self):
        """
        Get face detector - USE InsightFace's built-in detector (FAST!)
        
        CRITICAL OPTIMIZATION: Don't load MTCNN (takes 78 seconds!)
        InsightFace already has a detector built-in that's much faster.
        """
        # Return InsightFace's detector (already loaded with face_recognizer)
        # This is instant and avoids the 78-second MTCNN load
        return self.get_face_recognizer()  # InsightFace has built-in detector
    
    
    def get_face_recognizer(self):
        """Get face recognizer (InsightFace) - lazy loaded with thread safety"""
        if self._face_recognizer is None:
            with self._face_recognizer_lock:
                if self._face_recognizer is None:
                    logger.info("Loading Face Recognizer (InsightFace)...")
                    start_time = time.time()
                    
                    from ai_engine.models.face_recognizer import FaceRecognizer
                    self._face_recognizer = FaceRecognizer(model_name="buffalo_l")
                    
                    load_time = time.time() - start_time
                    self._load_times['face_recognizer'] = load_time
                    self._models_loaded['face_recognizer'] = True
                    self._inference_counts['face_recognizer'] = 0
                    
                    logger.info(f"Face Recognizer loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._face_recognizer
    
    def get_emotion_detector(self):
        """Get emotion detector (FER) - lazy loaded with thread safety"""
        if self._emotion_detector is None:
            with self._emotion_detector_lock:
                if self._emotion_detector is None:
                    logger.info("Loading Emotion Detector (FER)...")
                    start_time = time.time()
                    
                    from ai_engine.models.emotion_detector import EmotionDetector
                    self._emotion_detector = EmotionDetector()
                    
                    load_time = time.time() - start_time
                    self._load_times['emotion_detector'] = load_time
                    self._models_loaded['emotion_detector'] = True
                    self._inference_counts['emotion_detector'] = 0
                    
                    logger.info(f"Emotion Detector loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._emotion_detector
    
    def get_pose_estimator(self):
        """Get pose estimator (MediaPipe) - lazy loaded with thread safety"""
        if self._pose_estimator is None:
            with self._pose_estimator_lock:
                if self._pose_estimator is None:
                    logger.info("Loading Pose Estimator (MediaPipe)...")
                    start_time = time.time()
                    
                    from ai_engine.models.pose_estimator import PoseEstimator
                    self._pose_estimator = PoseEstimator(min_detection_confidence=0.5)
                    
                    load_time = time.time() - start_time
                    self._load_times['pose_estimator'] = load_time
                    self._models_loaded['pose_estimator'] = True
                    self._inference_counts['pose_estimator'] = 0
                    
                    logger.info(f"Pose Estimator loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._pose_estimator
    
    def get_weapon_detector(self):
        """Get weapon detector (YOLO26-N ONNX / onnxruntime) - lazy loaded with thread safety"""
        if self._weapon_detector is None:
            with self._weapon_detector_lock:
                if self._weapon_detector is None:
                    logger.info("Loading Weapon Detector (YOLO11n ONNX via onnxruntime)...")
                    start_time = time.time()
                    
                    from ai_engine.models.weapon_detector import WeaponDetector
                    self._weapon_detector = WeaponDetector()
                    
                    load_time = time.time() - start_time
                    self._load_times['weapon_detector'] = load_time
                    self._models_loaded['weapon_detector'] = True
                    self._inference_counts['weapon_detector'] = 0
                    
                    logger.info(f"Weapon Detector loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._weapon_detector
    
    def get_anti_spoof(self):
        """Get anti-spoof detector - lazy loaded with thread safety"""
        if self._anti_spoof is None:
            with self._anti_spoof_lock:
                if self._anti_spoof is None:
                    logger.info("Loading Anti-Spoof Detector...")
                    start_time = time.time()
                    
                    from ai_engine.models.anti_spoof import AntiSpoofDetector
                    self._anti_spoof = AntiSpoofDetector()
                    
                    load_time = time.time() - start_time
                    self._load_times['anti_spoof'] = load_time
                    self._models_loaded['anti_spoof'] = True
                    self._inference_counts['anti_spoof'] = 0
                    
                    logger.info(f"Anti-Spoof Detector loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._anti_spoof
    
    def get_age_estimator(self):
        """Get age estimator - lazy loaded with thread safety"""
        if self._age_estimator is None:
            with self._age_estimator_lock:
                if self._age_estimator is None:
                    logger.info("Loading Age Estimator...")
                    start_time = time.time()
                    
                    from ai_engine.models.age_estimator import AgeEstimator
                    self._age_estimator = AgeEstimator()
                    
                    load_time = time.time() - start_time
                    self._load_times['age_estimator'] = load_time
                    self._models_loaded['age_estimator'] = True
                    self._inference_counts['age_estimator'] = 0
                    
                    logger.info(f"Age Estimator loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._age_estimator
    
    def get_deepfake_detector(self):
        """Get deepfake detector - lazy loaded with thread safety"""
        if self._deepfake_detector is None:
            with self._deepfake_detector_lock:
                if self._deepfake_detector is None:
                    logger.info("Loading Deepfake Detector...")
                    start_time = time.time()
                    
                    from ai_engine.models.deepfake_detector import DeepfakeDetector
                    self._deepfake_detector = DeepfakeDetector()
                    
                    load_time = time.time() - start_time
                    self._load_times['deepfake_detector'] = load_time
                    self._models_loaded['deepfake_detector'] = True
                    self._inference_counts['deepfake_detector'] = 0
                    
                    logger.info(f"Deepfake Detector loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._deepfake_detector
    
    def get_object_detector(self):
        """Get object detector (YOLOv8) - lazy loaded with thread safety"""
        if self._object_detector is None:
            with self._object_detector_lock:
                if self._object_detector is None:
                    logger.info("Loading Object Detector (YOLOv8)...")
                    start_time = time.time()
                    
                    from ai_engine.models.object_detector import ObjectDetector
                    self._object_detector = ObjectDetector()
                    
                    load_time = time.time() - start_time
                    self._load_times['object_detector'] = load_time
                    self._models_loaded['object_detector'] = True
                    self._inference_counts['object_detector'] = 0
                    
                    logger.info(f"Object Detector loaded in {load_time:.2f}s")
                    self._log_memory_usage()
        
        return self._object_detector
    
    def _log_memory_usage(self):
        """Log current memory usage"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Current memory usage: {memory_mb:.1f} MB")
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return [name for name, loaded in self._models_loaded.items() if loaded]
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about model usage"""
        return {
            'loaded_models': self.get_loaded_models(),
            'load_times': self._load_times,
            'inference_counts': self._inference_counts,
            'memory_mb': psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        }
    
    def increment_inference_count(self, model_name: str):
        """Increment inference counter for a model"""
        if model_name in self._inference_counts:
            self._inference_counts[model_name] += 1
    
    def get_detection_pipeline(self, config: Dict[str, Any] = None):
        """Get shared detection pipeline singleton (thread-safe).
        
        Both detection_processor and camera_stream_annotated use this
        to avoid creating duplicate pipelines (and loading models twice).
        """
        if self._detection_pipeline is None:
            with self._detection_pipeline_lock:
                if self._detection_pipeline is None:
                    if config is None:
                        config = {
                            'enable_face_detection': True,
                            'enable_weapon_detection': True,
                            'enable_emotion_detection': True,
                            'enable_age_estimation': True,
                            'enable_pose_estimation': True,
                            'enable_anti_spoof': False,
                        }
                    from ai_engine.pipelines.detection_pipeline import DetectionPipeline
                    self._detection_pipeline = DetectionPipeline(config)
                    logger.info("✅ Shared DetectionPipeline created (singleton)")
        return self._detection_pipeline
    
    def cleanup(self):
        """Cleanup models and free memory (use with caution)"""
        logger.warning("Cleaning up AI models...")
        
        # Clear model instances
        self._face_detector = None
        self._face_recognizer = None
        self._emotion_detector = None
        self._pose_estimator = None
        self._weapon_detector = None
        self._anti_spoof = None
        self._age_estimator = None
        self._deepfake_detector = None
        self._object_detector = None
        self._detection_pipeline = None
        
        # Reset status
        for key in self._models_loaded:
            self._models_loaded[key] = False
        
        logger.info("AI models cleaned up")
        self._log_memory_usage()
    
    # Convenience properties for direct access
    @property
    def face_detector(self):
        """Direct access to face detector"""
        return self.get_face_detector()
    
    @property
    def face_recognizer(self):
        """Direct access to face recognizer"""
        return self.get_face_recognizer()
    
    @property
    def emotion_detector(self):
        """Direct access to emotion detector"""
        return self.get_emotion_detector()
    
    @property
    def pose_estimator(self):
        """Direct access to pose estimator"""
        return self.get_pose_estimator()
    
    @property
    def weapon_detector(self):
        """Direct access to weapon detector"""
        return self.get_weapon_detector()
    
    @property
    def anti_spoof(self):
        """Direct access to anti-spoof detector"""
        return self.get_anti_spoof()
    
    @property
    def age_estimator(self):
        """Direct access to age estimator"""
        return self.get_age_estimator()
    
    @property
    def deepfake_detector(self):
        """Direct access to deepfake detector"""
        return self.get_deepfake_detector()
    
    @property
    def object_detector(self):
        """Direct access to object detector"""
        return self.get_object_detector()


# Global singleton instance
ai_model_manager = AIModelManager()
