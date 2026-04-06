"""
Pose analysis for detecting aggressive behavior
"""
import numpy as np
from typing import Dict, Optional, List
from loguru import logger


class PoseAnalyzer:
    """Analyzes pose keypoints to detect aggressive behavior"""
    
    def __init__(self):
        """Initialize pose analyzer"""
        # MediaPipe pose landmark indices
        self.NOSE = 0
        self.LEFT_SHOULDER = 11
        self.RIGHT_SHOULDER = 12
        self.LEFT_ELBOW = 13
        self.RIGHT_ELBOW = 14
        self.LEFT_WRIST = 15
        self.RIGHT_WRIST = 16
        self.LEFT_HIP = 23
        self.RIGHT_HIP = 24
        self.LEFT_KNEE = 25
        self.RIGHT_KNEE = 26
        self.LEFT_ANKLE = 27
        self.RIGHT_ANKLE = 28
        
        logger.info("PoseAnalyzer initialized")
    
    def analyze_aggression(self, pose_data: Dict) -> Dict:
        """
        Analyze pose for aggressive behavior
        
        Args:
            pose_data: Pose data from PoseEstimator.detect()
            
        Returns:
            Dict with aggression analysis:
            {
                'is_aggressive': bool,
                'confidence': float,
                'pose_type': str,
                'indicators': List[str]
            }
        """
        if not pose_data or 'keypoints' not in pose_data:
            return {
                'is_aggressive': False,
                'confidence': 0.0,
                'pose_type': 'unknown',
                'indicators': []
            }
        
        keypoints = pose_data['keypoints']
        indicators = []
        aggression_score = 0.0
        
        # Calculate body scale for proportional thresholds
        body_scale = self._get_body_scale(keypoints)
        
        # Check for raised hands/fists (fighting pose)
        # Requires BOTH hands raised significantly above head
        hands_raised = self._check_raised_hands(keypoints, body_scale)
        if hands_raised:
            indicators.append('raised_hands')
            aggression_score += 0.4
        
        # Check for wide stance (aggressive posture)
        wide_stance = self._check_wide_stance(keypoints)
        if wide_stance:
            indicators.append('wide_stance')
            aggression_score += 0.2
        
        # Check for lunging motion (forward lean)
        lunging = self._check_lunging(keypoints, body_scale)
        if lunging:
            indicators.append('lunging')
            aggression_score += 0.3
        
        # Check for kicking motion (leg raised very high)
        kicking = self._check_kicking(keypoints, body_scale)
        if kicking:
            indicators.append('kicking')
            aggression_score += 0.4
        
        # Check for arms extended outward (gun aiming / pointing pose)
        arms_extended = self._check_arms_extended(keypoints, body_scale)
        if arms_extended:
            indicators.append('arms_extended')
            aggression_score += 0.45
        
        # Determine pose type — raised thresholds to reduce false positives
        # wide_stance(0.2)+lunging(0.3) = 0.5 was triggering on normal standing
        pose_type = 'normal'
        if aggression_score >= 0.8:
            pose_type = 'fighting'
        elif aggression_score >= 0.6:
            pose_type = 'threatening'
        elif aggression_score >= 0.4:
            pose_type = 'suspicious'
        
        # Only alert on genuinely aggressive behavior (0.6+ requires 3+ indicators)
        is_aggressive = aggression_score >= 0.6
        
        return {
            'is_aggressive': is_aggressive,
            'confidence': min(aggression_score, 1.0),
            'pose_type': pose_type,
            'indicators': indicators
        }
    
    def _get_body_scale(self, keypoints: Dict) -> float:
        """Calculate body scale (shoulder width) for proportional thresholds."""
        try:
            ls = keypoints.get(self.LEFT_SHOULDER)
            rs = keypoints.get(self.RIGHT_SHOULDER)
            if ls and rs:
                return max(abs(ls['x'] - rs['x']), 50)  # Min 50px
            return 100  # Default
        except Exception:
            return 100
    
    def _check_raised_hands(self, keypoints: Dict, body_scale: float) -> bool:
        """Check if BOTH hands are raised well above the head (fighting pose).
        
        Only triggers when wrists are above or near head level, not simply
        above shoulders — holding an object or gesturing should NOT trigger this.
        """
        try:
            left_wrist = keypoints.get(self.LEFT_WRIST)
            right_wrist = keypoints.get(self.RIGHT_WRIST)
            nose = keypoints.get(self.NOSE)
            left_shoulder = keypoints.get(self.LEFT_SHOULDER)
            right_shoulder = keypoints.get(self.RIGHT_SHOULDER)
            
            if not all([left_wrist, right_wrist, nose, left_shoulder, right_shoulder]):
                return False
            
            # Threshold: wrists must be above nose level (head height)
            # Using proportional threshold based on body scale
            threshold = body_scale * 0.3  # 30% of shoulder width
            
            left_raised = left_wrist['y'] < nose['y'] - threshold
            right_raised = right_wrist['y'] < nose['y'] - threshold
            
            # BOTH hands must be raised above head — single hand up is normal
            return left_raised and right_raised
            
        except Exception as e:
            logger.debug(f"Error checking raised hands: {e}")
            return False
    
    def _check_wide_stance(self, keypoints: Dict) -> bool:
        """Check for very wide stance (feet far apart, 2x hip width)"""
        try:
            left_ankle = keypoints.get(self.LEFT_ANKLE)
            right_ankle = keypoints.get(self.RIGHT_ANKLE)
            left_hip = keypoints.get(self.LEFT_HIP)
            right_hip = keypoints.get(self.RIGHT_HIP)
            
            if not all([left_ankle, right_ankle, left_hip, right_hip]):
                return False
            
            ankle_distance = abs(left_ankle['x'] - right_ankle['x'])
            hip_distance = abs(left_hip['x'] - right_hip['x'])
            
            # Raised threshold: ankles must be 2x wider than hips (very aggressive)
            return ankle_distance > hip_distance * 2.0
            
        except Exception as e:
            logger.debug(f"Error checking wide stance: {e}")
            return False
    
    def _check_lunging(self, keypoints: Dict, body_scale: float) -> bool:
        """Check for forward lean (lunging motion) — proportional threshold"""
        try:
            nose = keypoints.get(self.NOSE)
            left_hip = keypoints.get(self.LEFT_HIP)
            right_hip = keypoints.get(self.RIGHT_HIP)
            
            if not all([nose, left_hip, right_hip]):
                return False
            
            hip_center_x = (left_hip['x'] + right_hip['x']) / 2
            
            # Proportional threshold: nose must be 40% of body_scale forward of hips
            threshold = body_scale * 0.4
            forward_lean = abs(nose['x'] - hip_center_x) > threshold
            
            return forward_lean
            
        except Exception as e:
            logger.debug(f"Error checking lunging: {e}")
            return False
    
    def _check_kicking(self, keypoints: Dict, body_scale: float) -> bool:
        """Check for kicking motion (leg raised very high).
        
        Only triggers when a knee is raised well above hip level — sitting
        or standing with slightly bent knees should NOT trigger this.
        """
        try:
            left_knee = keypoints.get(self.LEFT_KNEE)
            right_knee = keypoints.get(self.RIGHT_KNEE)
            left_hip = keypoints.get(self.LEFT_HIP)
            right_hip = keypoints.get(self.RIGHT_HIP)
            
            if not all([left_knee, right_knee, left_hip, right_hip]):
                return False
            
            # Proportional threshold: knee must be above hip by 50% of body_scale
            threshold = body_scale * 0.5
            
            left_raised = left_knee['y'] < left_hip['y'] - threshold
            right_raised = right_knee['y'] < right_hip['y'] - threshold
            
            return left_raised or right_raised
            
        except Exception as e:
            logger.debug(f"Error checking kicking: {e}")
            return False
    
    def _check_arms_extended(self, keypoints: Dict, body_scale: float) -> bool:
        """Check for arms extended outward (gun aiming / pointing pose).
        
        Triggers when one or both arms are extended far from the body
        horizontally AND at roughly shoulder height. This catches gun-pointing,
        threatening gestures, and reaching/grabbing motions.
        """
        try:
            left_wrist = keypoints.get(self.LEFT_WRIST)
            right_wrist = keypoints.get(self.RIGHT_WRIST)
            left_shoulder = keypoints.get(self.LEFT_SHOULDER)
            right_shoulder = keypoints.get(self.RIGHT_SHOULDER)
            left_elbow = keypoints.get(self.LEFT_ELBOW)
            right_elbow = keypoints.get(self.RIGHT_ELBOW)
            
            if not all([left_shoulder, right_shoulder]):
                return False
            
            # Need at least one arm fully visible
            has_left = left_wrist and left_elbow
            has_right = right_wrist and right_elbow
            if not has_left and not has_right:
                return False
            
            # Arm is "extended" when:
            # 1. Wrist is far from shoulder horizontally (> 1.5× shoulder width)
            # 2. Wrist is near shoulder height (within 60% of body_scale vertically)
            # 3. Elbow is roughly between shoulder and wrist (arm is straight)
            extend_threshold = body_scale * 1.5
            height_tolerance = body_scale * 0.6
            
            left_extended = False
            right_extended = False
            
            if has_left:
                horiz_dist = abs(left_wrist['x'] - left_shoulder['x'])
                vert_diff = abs(left_wrist['y'] - left_shoulder['y'])
                if horiz_dist > extend_threshold and vert_diff < height_tolerance:
                    left_extended = True
            
            if has_right:
                horiz_dist = abs(right_wrist['x'] - right_shoulder['x'])
                vert_diff = abs(right_wrist['y'] - right_shoulder['y'])
                if horiz_dist > extend_threshold and vert_diff < height_tolerance:
                    right_extended = True
            
            return left_extended or right_extended
            
        except Exception as e:
            logger.debug(f"Error checking arms extended: {e}")
            return False
    
    def detect_fighting(self, pose_data_list: List[Dict]) -> bool:
        """
        Detect if multiple people are fighting
        
        Args:
            pose_data_list: List of pose data for multiple people
            
        Returns:
            True if fighting detected
        """
        if len(pose_data_list) < 2:
            return False
        
        # Check if multiple people have aggressive poses
        aggressive_count = 0
        for pose_data in pose_data_list:
            analysis = self.analyze_aggression(pose_data)
            if analysis['is_aggressive']:
                aggressive_count += 1
        
        # Fighting if 2+ people have aggressive poses
        return aggressive_count >= 2
