"""
Behavior analysis pipeline for detecting suspicious activities
"""
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque
import time


@dataclass
class BehaviorPattern:
    """Detected behavior pattern"""
    pattern_type: str
    confidence: float
    duration: float
    metadata: Dict[str, Any]


class BehaviorAnalyzer:
    """Analyze behavior patterns from pose and detection data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.position_history = deque(maxlen=300)  # 30 seconds at 10fps
        self.loitering_threshold = config.get('loitering_threshold', 20.0)  # seconds
        self.running_speed_threshold = config.get('running_threshold', 5.0)  # pixels/frame
        
    def analyze_behavior(
        self,
        detection_result,
        frame_number: int
    ) -> List[BehaviorPattern]:
        """
        Analyze behavior from detection result
        
        Args:
            detection_result: DetectionResult from pipeline
            frame_number: Current frame number
            
        Returns:
            List of detected behavior patterns
        """
        behaviors = []
        
        if not detection_result or not detection_result.face_bbox:
            return behaviors
        
        # Track position
        bbox = detection_result.face_bbox
        center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        
        self.position_history.append({
            'center': center,
            'timestamp': time.time(),
            'frame': frame_number
        })
        
        # Check for loitering
        loitering = self._detect_loitering()
        if loitering:
            behaviors.append(loitering)
        
        # Check for running
        if len(self.position_history) >= 10:
            running = self._detect_running()
            if running:
                behaviors.append(running)
        
        # Check for aggressive pose
        if detection_result.pose_keypoints:
            aggressive = self._detect_aggressive_pose(detection_result.pose_keypoints)
            if aggressive:
                behaviors.append(aggressive)
        
        return behaviors
    
    def _detect_loitering(self) -> Optional[BehaviorPattern]:
        """Detect if person is loitering"""
        if len(self.position_history) < 50:  # Need 5 seconds of data
            return None
        
        # Calculate movement variance
        positions = [p['center'] for p in self.position_history]
        x_coords = [p[0] for p in positions]
        y_coords = [p[1] for p in positions]
        
        x_variance = np.var(x_coords)
        y_variance = np.var(y_coords)
        
        total_movement = x_variance + y_variance
        
        # Check duration
        duration = self.position_history[-1]['timestamp'] - self.position_history[0]['timestamp']
        
        if total_movement < 1000 and duration > self.loitering_threshold:
            return BehaviorPattern(
                pattern_type='loitering',
                confidence=0.8,
                duration=duration,
                metadata={'movement_variance': float(total_movement)}
            )
        
        return None
    
    def _detect_running(self) -> Optional[BehaviorPattern]:
        """Detect if person is running"""
        # Calculate average speed over last 10 frames
        recent_positions = list(self.position_history)[-10:]
        
        speeds = []
        for i in range(1, len(recent_positions)):
            prev = recent_positions[i-1]['center']
            curr = recent_positions[i]['center']
            
            distance = np.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
            speeds.append(distance)
        
        avg_speed = np.mean(speeds)
        
        if avg_speed > self.running_speed_threshold:
            return BehaviorPattern(
                pattern_type='running',
                confidence=0.75,
                duration=1.0,
                metadata={'avg_speed': float(avg_speed)}
            )
        
        return None
    
    def _detect_aggressive_pose(self, pose_data: Dict) -> Optional[BehaviorPattern]:
        """Detect aggressive body language"""
        if not pose_data or 'keypoints' not in pose_data:
            return None
        
        keypoints = pose_data['keypoints']
        
        # Check if arms are raised (simplified heuristic)
        left_wrist = keypoints.get(15)
        right_wrist = keypoints.get(16)
        left_shoulder = keypoints.get(11)
        right_shoulder = keypoints.get(12)
        
        if not all([left_wrist, right_wrist, left_shoulder, right_shoulder]):
            return None
        
        # Check if wrists are above shoulders
        left_raised = left_wrist['y'] < left_shoulder['y']
        right_raised = right_wrist['y'] < right_shoulder['y']
        
        if left_raised and right_raised:
            return BehaviorPattern(
                pattern_type='aggressive_pose',
                confidence=0.6,
                duration=0.1,
                metadata={'arms_raised': True}
            )
        
        return None
    
    def reset(self):
        """Reset tracking history"""
        self.position_history.clear()