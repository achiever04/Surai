"""
Pose estimation using MediaPipe
"""
import mediapipe as mp
import cv2
import numpy as np
from typing import Optional, Dict, List

class PoseEstimator:
    def __init__(self, min_detection_confidence: float = 0.5):
        """
        Initialize MediaPipe Pose
        
        Args:
            min_detection_confidence: Minimum confidence for detection
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,  # CRITICAL FIX: Thread-safe mode (prevents timestamp crashes)
            model_complexity=0,  # 0 = Lite, faster on CPU
            min_detection_confidence=min_detection_confidence,
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect pose keypoints in image
        
        Args:
            image: BGR image
            
        Returns:
            Dict with keypoints or None
        """
        # Convert to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Process
        results = self.pose.process(rgb_image)
        
        if not results.pose_landmarks:
            return None
        
        # Extract keypoints
        h, w = image.shape[:2]
        keypoints = {}
        
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            keypoints[idx] = {
                'x': landmark.x * w,
                'y': landmark.y * h,
                'z': landmark.z,
                'visibility': landmark.visibility
            }
        
        return {
            'keypoints': keypoints,
            'raw_landmarks': results.pose_landmarks
        }
    
    def draw_pose(
        self,
        image: np.ndarray,
        pose_data: Dict
    ) -> np.ndarray:
        """
        Draw pose skeleton on image
        
        Args:
            image: BGR image
            pose_data: Pose data from detect()
            
        Returns:
            Image with pose drawn
        """
        if not pose_data or 'raw_landmarks' not in pose_data:
            return image
        
        annotated_image = image.copy()
        self.mp_drawing.draw_landmarks(
            annotated_image,
            pose_data['raw_landmarks'],
            self.mp_pose.POSE_CONNECTIONS
        )
        
        return annotated_image
    
    def get_body_orientation(self, pose_data: Dict) -> Optional[str]:
        """
        Estimate body orientation (front, back, left, right)
        
        Returns:
            Orientation string or None
        """
        if not pose_data:
            return None
        
        keypoints = pose_data['keypoints']
        
        # Use shoulder and hip positions to estimate orientation
        # Simplified heuristic
        left_shoulder = keypoints.get(11)
        right_shoulder = keypoints.get(12)
        
        if not left_shoulder or not right_shoulder:
            return None
        
        # Check visibility
        if left_shoulder['visibility'] > right_shoulder['visibility']:
            return "left"
        elif right_shoulder['visibility'] > left_shoulder['visibility']:
            return "right"
        else:
            return "front"
    
    def detect_action(self, pose_data: Dict) -> Optional[str]:
        """
        Detect simple actions (standing, sitting, lying)
        Simplified implementation
        """
        if not pose_data:
            return None
        
        keypoints = pose_data['keypoints']
        
        # Get key landmarks
        nose = keypoints.get(0)
        left_hip = keypoints.get(23)
        left_knee = keypoints.get(25)
        left_ankle = keypoints.get(27)
        
        if not all([nose, left_hip, left_knee, left_ankle]):
            return "unknown"
        
        # Simple heuristic based on vertical alignment
        hip_knee_dist = abs(left_hip['y'] - left_knee['y'])
        knee_ankle_dist = abs(left_knee['y'] - left_ankle['y'])
        
        if hip_knee_dist < 50 and knee_ankle_dist < 50:
            return "sitting"
        elif nose['y'] > left_hip['y']:
            return "lying"
        else:
            return "standing"
    
    def __del__(self):
        """Cleanup"""
        self.pose.close()