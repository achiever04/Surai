import numpy as np
from ultralytics import YOLO

class UnifiedPerceptionEngine:
    """
    Unified YOLO perception engine replacing independent Face, Object, Pose, and Weapon detectors.
    Runs a single forward pass.
    """
    def __init__(self, model_path="yolov8n-pose.pt"):
        # Load the unified YOLO model. This model should be fine-tuned
        # to detect persons, faces, weapons, and generate pose keypoints.
        self.model = YOLO(model_path)
    
    def infer(self, frame: np.ndarray, conf_threshold: float = 0.25):
        """
        Run inference on a single frame. Returns the first result object containing 
        boxes, masks, and keypoints.
        """
        # Run inference. The single model will return all necessary detections.
        # You can specify classes=[...] if needed to filter specifically.
        results = self.model(frame, conf=conf_threshold, verbose=False)
        return results[0]
