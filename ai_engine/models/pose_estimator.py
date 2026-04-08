import numpy as np
from collections import deque
import torch
import torch.nn as nn
from typing import Optional, Dict

class Action1DCNN(nn.Module):
    """
    Lightweight 1D-CNN to process sequences of 34 pose keypoints over 30 frames.
    Detects Aggressive vs Neutral behavior based on spatial-temporal momentum.
    """
    def __init__(self, num_keypoints=34*2, num_classes=3):
        super().__init__()
        # Input shape: (Batch, Features, SeqLength) -> (1, 68, 30)
        self.conv1 = nn.Conv1d(in_channels=num_keypoints, out_channels=64, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.conv2 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Linear(128, num_classes)
        
    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.pool(x).squeeze(-1)
        return self.fc(x)

class PoseEstimator:
    """
    Analyzes temporal pose keypoints via 1D-CNN instead of frame-by-frame heuristics.
    """
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.track_buffers = {}
        
        # Load temporal Action model
        self.action_model = Action1DCNN()
        self.action_model.eval()
        
        # We classify temporal windows into semantic states
        self.classes = ['neutral', 'aggressive', 'defensive']

    def update_and_predict(self, track_id: int, keypoints_arr: np.ndarray, bbox: list) -> str:
        """
        Takes raw keypoints from the Unified Perception Engine (YOLO-Pose) per frame.
        Aggregates them up to window_size, normalizes them, and runs the CNN.
        """
        if track_id not in self.track_buffers:
            self.track_buffers[track_id] = deque(maxlen=self.window_size)
            
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        
        # YOLO-Pose outputs e.g., 17 keypoints (34 coordinates)
        # We normalize by subtracting bounding box center to make it distance-invariant.
        flat_kpts = []
        # Flatten keypoints [(x,y),(x,y)...]
        # In this implementation, assuming keypoints_arr is numpy array of shape (17, 2/3)
        if hasattr(keypoints_arr, 'shape') and len(keypoints_arr.shape) > 1:
            for pt in keypoints_arr:
                flat_kpts.extend([pt[0] - cx, pt[1] - cy])
                
        # Zero pad if missing 
        while len(flat_kpts) < 68: # 34 * 2
            flat_kpts.append(0.0)
            
        self.track_buffers[track_id].append(flat_kpts[:68])
        
        # Only predict if we have sufficient sequence velocity data
        if len(self.track_buffers[track_id]) == self.window_size:
            # Shape transition for Conv1D: (Sequence, Features) -> (Features, Sequence)
            seq = np.array(self.track_buffers[track_id]).T 
            tensor_seq = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)
            
            with torch.no_grad():
                out = self.action_model(tensor_seq)
                idx = torch.argmax(out, dim=1).item()
                return self.classes[idx]
                
        return "gathering_data"
        
    def cleanup_track(self, track_id: int):
        if track_id in self.track_buffers:
            del self.track_buffers[track_id]