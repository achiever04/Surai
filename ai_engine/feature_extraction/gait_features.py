"""
Gait feature extraction for person identification
"""
import numpy as np
from typing import List, Optional, Dict, Any


class GaitFeatureExtractor:
    """Extract gait features from pose sequences"""
    
    def __init__(self, sequence_length: int = 30):
        """
        Initialize gait extractor
        
        Args:
            sequence_length: Number of frames to analyze (3 seconds at 10fps)
        """
        self.sequence_length = sequence_length
        self.pose_sequences: Dict[int, List] = {}
    
    def add_pose(self, person_id: int, pose_keypoints: Dict):
        """
        Add pose frame to sequence for person
        
        Args:
            person_id: Person identifier
            pose_keypoints: Pose keypoints from MediaPipe
        """
        if person_id not in self.pose_sequences:
            self.pose_sequences[person_id] = []
        
        sequence = self.pose_sequences[person_id]
        sequence.append(pose_keypoints)
        
        # Keep only recent frames
        if len(sequence) > self.sequence_length:
            sequence.pop(0)
    
    def extract_features(self, person_id: int) -> Optional[np.ndarray]:
        """
        Extract gait features from pose sequence
        
        Args:
            person_id: Person identifier
            
        Returns:
            Feature vector or None if insufficient data
        """
        if person_id not in self.pose_sequences:
            return None
        
        sequence = self.pose_sequences[person_id]
        
        if len(sequence) < 10:  # Need at least 1 second
            return None
        
        features = []
        
        # Extract stride features
        stride_features = self._extract_stride_features(sequence)
        features.extend(stride_features)
        
        # Extract body proportion features
        proportion_features = self._extract_proportion_features(sequence)
        features.extend(proportion_features)
        
        # Extract movement rhythm features
        rhythm_features = self._extract_rhythm_features(sequence)
        features.extend(rhythm_features)
        
        return np.array(features, dtype=np.float32)
    
    def _extract_stride_features(self, sequence: List) -> List[float]:
        """Extract stride length and frequency"""
        features = []
        
        # Calculate stride metrics from hip and ankle movements
        left_ankle_y = []
        right_ankle_y = []
        
        for pose in sequence:
            keypoints = pose.get('keypoints', {})
            
            left_ankle = keypoints.get(27)
            right_ankle = keypoints.get(28)
            
            if left_ankle:
                left_ankle_y.append(left_ankle['y'])
            if right_ankle:
                right_ankle_y.append(right_ankle['y'])
        
        # Stride frequency (steps per frame)
        if len(left_ankle_y) > 5:
            left_variance = np.var(left_ankle_y)
            features.append(left_variance)
        else:
            features.append(0.0)
        
        if len(right_ankle_y) > 5:
            right_variance = np.var(right_ankle_y)
            features.append(right_variance)
        else:
            features.append(0.0)
        
        return features
    
    def _extract_proportion_features(self, sequence: List) -> List[float]:
        """Extract body proportion features"""
        features = []
        
        # Use first valid pose for proportions
        for pose in sequence:
            keypoints = pose.get('keypoints', {})
            
            # Calculate leg length
            left_hip = keypoints.get(23)
            left_ankle = keypoints.get(27)
            
            if left_hip and left_ankle:
                leg_length = abs(left_hip['y'] - left_ankle['y'])
                features.append(leg_length)
                break
        
        if not features:
            features.append(0.0)
        
        return features
    
    def _extract_rhythm_features(self, sequence: List) -> List[float]:
        """Extract walking rhythm features"""
        features = []
        
        # Calculate center of mass movement
        com_y = []
        
        for pose in sequence:
            keypoints = pose.get('keypoints', {})
            
            # Approximate center of mass from hips
            left_hip = keypoints.get(23)
            right_hip = keypoints.get(24)
            
            if left_hip and right_hip:
                com = (left_hip['y'] + right_hip['y']) / 2
                com_y.append(com)
        
        if len(com_y) > 5:
            # Rhythm regularity
            rhythm_variance = np.var(np.diff(com_y))
            features.append(rhythm_variance)
        else:
            features.append(0.0)
        
        return features
    
    def clear_sequence(self, person_id: int):
        """Clear pose sequence for person"""
        if person_id in self.pose_sequences:
            del self.pose_sequences[person_id]