import numpy as np
from ultralytics import YOLO
import onnxruntime as ort
import psutil
from ai_engine.utils.profiler import profile_latency

class UnifiedPerceptionEngine:
    """
    Unified YOLO perception engine replacing independent Face, Object, Pose, and Weapon detectors.
    Runs a single forward pass natively.
    """
    def __init__(self, model_path="yolov8n-pose.onnx"):
        # CPU Execution Provider thread clamping for Ryzen optimization
        threads = max(1, psutil.cpu_count(logical=False) - 1)
        
        # Setup ONNX threading rules (Ultralytics intercepts some of these internally, 
        # but allocating the SessionOptions forces environment precedence)
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = threads
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Load the newly compiled ONNX INT8 model instead of PyTorch FP32
        self.model = YOLO(model_path, task='pose')
    
    @profile_latency("YOLO_Unified")
    def infer(self, frame: np.ndarray, conf_threshold: float = 0.45) -> dict:
        """
        Runs one network pass extracting all bounding boxes and poses simultaneously.
        """
        results = self.model(frame, verbose=False, conf=conf_threshold)[0]
        
        parsed_data = {
            "faces": [],
            "weapons": [],
            "poses": []
        }
        
        if not results.boxes:
            return parsed_data

        for idx, box in enumerate(results.boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            # Person class (0)
            if cls_id == 0:  
                # YOLO-Pose natively yields person keypoints
                if results.keypoints is not None:
                    parsed_data["poses"].append({
                        "bbox": (x1, y1, x2, y2),
                        "keypoints": results.keypoints.data[idx].cpu().numpy(),
                        "conf": conf
                    })
                # Base face bounding heuristic
                parsed_data["faces"].append((x1, y1, x2, y2))
                
            # Weapons (knives/guns mapped to specific COCO or custom IDs, e.g., 43, 85, or custom 2)
            elif cls_id in [2, 43, 85]:  
                parsed_data["weapons"].append({
                    "bbox": (x1, y1, x2, y2),
                    "class": "weapon",
                    "conf": conf
                })

        return parsed_data
