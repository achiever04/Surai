"""
General Object Detection Model

Detects common objects in surveillance footage:
- Bags (backpack, handbag, suitcase)
- Vehicles (car, motorcycle, bicycle, truck)
- Electronics (laptop, cell phone)
- Other items of interest

Uses YOLOv8-nano for real-time performance.
"""
import cv2
import numpy as np
from typing import List, Dict, Any
from loguru import logger

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed - object detection disabled")


class ObjectDetector:
    """
    General object detection using YOLOv8
    
    Detects objects of interest in surveillance scenarios
    """
    
    # COCO dataset classes of interest for surveillance
    TARGET_CLASSES = [
        'person', 'backpack', 'handbag', 'suitcase',
        'car', 'motorcycle', 'bicycle', 'truck', 'bus',
        'laptop', 'cell phone', 'bottle', 'knife'
    ]
    
    def __init__(self, model_name: str = 'yolov8n.pt', confidence_threshold: float = 0.5):
        """
        Initialize object detector
        
        Args:
            model_name: YOLOv8 model name (n=nano, s=small, m=medium)
            confidence_threshold: Minimum confidence for detection
        """
        self.model = None
        self.confidence_threshold = confidence_threshold
        self.enabled = False
        
        if not YOLO_AVAILABLE:
            logger.warning("Object detector disabled - ultralytics not installed")
            return
        
        try:
            self.model = YOLO(model_name)
            self.enabled = True
            logger.info(f"Object detector loaded: {model_name}")
        
        except Exception as e:
            logger.error(f"Failed to load object detector: {e}")
            self.enabled = False
    
    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect objects in frame
        
        Args:
            frame: BGR image
        
        Returns:
            List of {
                'class': str,
                'confidence': float,
                'bbox': [x1, y1, x2, y2]
            }
        """
        if not self.enabled or self.model is None:
            return []
        
        try:
            # Run detection
            results = self.model(frame, verbose=False, conf=self.confidence_threshold)
            
            detections = []
            
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    # Only return objects of interest
                    if class_name in self.TARGET_CLASSES:
                        confidence = float(box.conf[0])
                        bbox = box.xyxy[0].cpu().numpy().tolist()
                        
                        detections.append({
                            'class': class_name,
                            'confidence': confidence,
                            'bbox': bbox
                        })
            
            if detections:
                logger.debug(f"Detected {len(detections)} objects")
            
            return detections
        
        except Exception as e:
            logger.error(f"Object detection error: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if detector is available"""
        return self.enabled and self.model is not None


# PERFORMANCE FIX: Lazy-loading proxy instead of eager module-level instantiation
# Previously: object_detector = ObjectDetector()  ← loaded YOLOv8 (~200MB, ~3-5s) at IMPORT TIME
# Now: only loads when first accessed, preventing unnecessary memory + startup cost
class _LazyObjectDetector:
    """Proxy that defers ObjectDetector creation until first use"""
    def __init__(self):
        self._instance = None
    
    def _get_instance(self):
        if self._instance is None:
            self._instance = ObjectDetector()
        return self._instance
    
    def __getattr__(self, name):
        return getattr(self._get_instance(), name)

object_detector = _LazyObjectDetector()
