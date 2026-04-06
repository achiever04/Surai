"""
Frame annotation utilities for real-time detection visualization

This module provides functions to annotate video frames with detection results:
- Bounding boxes (faces, weapons, objects)
- Watchlist person IDs and names
- Confidence scores
- Emotion labels
- Age estimates
- Pose skeletons
- Anti-spoofing indicators

COORDINATE FORMAT:
- face_bbox: (x1, y1, x2, y2) — from InsightFace, already scaled to original frame
- weapon bbox: [x1, y1, x2, y2] — from YOLOv8, already scaled to original frame
- pose keypoints: {idx: {x, y, z, visibility}} — pixel coords, already scaled
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from ai_engine.pipelines.detection_pipeline import DetectionResult


class FrameAnnotator:
    """Annotate frames with detection results"""
    
    # Colors (BGR format)
    COLOR_FACE = (0, 255, 0)          # Green
    COLOR_WATCHLIST = (0, 255, 255)   # Yellow/Cyan
    COLOR_WEAPON = (0, 0, 255)        # Red
    COLOR_OBJECT = (255, 165, 0)      # Orange
    COLOR_EMOTION = (255, 255, 0)     # Yellow
    COLOR_AGE = (255, 0, 255)         # Magenta
    COLOR_POSE = (0, 255, 255)        # Cyan
    COLOR_POSE_JOINT = (0, 200, 200)  # Darker cyan for joints
    COLOR_SPOOFING = (0, 0, 255)      # Red
    
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 2
        self.box_thickness = 2
    
    def annotate_frame(
        self,
        frame: np.ndarray,
        detection: Optional[DetectionResult],
        show_watchlist_ids: bool = True,
        show_confidence: bool = True,
        show_emotion: bool = True,
        show_age: bool = True,
        show_pose: bool = True
    ) -> np.ndarray:
        """
        Annotate frame with all detection results
        
        Args:
            frame: Original frame (BGR)
            detection: Detection result from pipeline
            show_watchlist_ids: Show watchlist person ID and name
            show_confidence: Show confidence scores
            show_emotion: Show emotion labels
            show_age: Show age estimates
            show_pose: Show pose skeleton
        
        Returns:
            Annotated frame
        """
        if detection is None:
            return frame
        
        # Make a copy to avoid modifying original
        annotated = frame.copy()
        
        # 1. Anti-spoofing warning (highest priority)
        if not detection.is_real_face:
            annotated = self._draw_spoofing_warning(annotated)
        
        # 2. Weapon detections (CRITICAL - draw first for visibility)
        if detection.has_weapon and detection.weapons_detected:
            annotated = self._draw_weapons(
                annotated, 
                detection.weapons_detected,
                show_confidence
            )
        
        # 3. MULTI-FACE: Draw bboxes + emotion + age for ALL faces
        faces_to_draw = detection.all_faces if detection.all_faces else []
        
        # Backward compat: if all_faces is empty but single face_bbox exists
        if not faces_to_draw and detection.has_face and detection.face_bbox:
            from ai_engine.pipelines.detection_pipeline import FaceData
            faces_to_draw = [FaceData(
                face_bbox=detection.face_bbox,
                emotion=detection.emotion,
                age=detection.age,
                matched_person_id=detection.matched_person_id,
                matched_person_name=detection.matched_person_name,
                confidence=detection.confidence
            )]
        
        for face in faces_to_draw:
            if face.face_bbox:
                annotated = self._draw_face(
                    annotated,
                    face.face_bbox,
                    face.matched_person_id,
                    face.matched_person_name,
                    face.confidence,
                    detection.metadata,
                    show_watchlist_ids,
                    show_confidence
                )
                
                # Emotion label per face
                if show_emotion and face.emotion:
                    annotated = self._draw_emotion(
                        annotated,
                        face.face_bbox,
                        face.emotion
                    )
                
                # Age estimate per face
                if show_age and face.age:
                    annotated = self._draw_age(
                        annotated,
                        face.face_bbox,
                        face.age
                    )
        
        # 4. Pose skeleton
        if show_pose and detection.pose_keypoints:
            annotated = self._draw_pose(
                annotated,
                detection.pose_keypoints
            )
        
        # 5. General objects (if any)
        if detection.metadata.get('objects'):
            annotated = self._draw_objects(
                annotated,
                detection.metadata['objects'],
                show_confidence
            )
        
        return annotated
    
    def _draw_face(
        self,
        frame: np.ndarray,
        face_bbox: Tuple[int, int, int, int],
        matched_person_id: Optional[int],
        matched_person_name: Optional[str],
        confidence: float,
        metadata: Dict[str, Any],
        show_watchlist_ids: bool,
        show_confidence: bool
    ) -> np.ndarray:
        """Draw face bounding box with labels.
        
        BBOX FORMAT FIX: face_bbox is (x1, y1, x2, y2) from InsightFace,
        NOT (x, y, w, h). Previously this was wrong, causing bounding boxes
        to extend far beyond the face.
        """
        x1, y1, x2, y2 = face_bbox
        
        # Clamp to frame bounds
        h, w = frame.shape[:2]
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))
        
        # Color: Yellow if watchlist match, green otherwise
        color = self.COLOR_WATCHLIST if matched_person_id else self.COLOR_FACE
        thickness = 3 if matched_person_id else self.box_thickness
        
        # Draw bounding box with rounded corners for a modern look
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        
        # Watchlist ID and name
        if show_watchlist_ids and matched_person_id:
            if matched_person_name:
                label = f"{matched_person_name}"
            else:
                label = f"Person {matched_person_id}"
            
            if show_confidence:
                label += f" ({confidence*100:.1f}%)"
            
            # Background for text
            (text_w, text_h), baseline = cv2.getTextSize(
                label, self.font, self.font_scale, self.font_thickness
            )
            
            # Draw background rectangle above bounding box
            cv2.rectangle(
                frame, 
                (x1, y1 - text_h - baseline - 10), 
                (x1 + text_w + 10, y1), 
                color, 
                -1
            )
            
            # Draw text
            cv2.putText(
                frame, label, (x1 + 5, y1 - baseline - 5), 
                self.font, self.font_scale, (0, 0, 0), self.font_thickness
            )
        
        # Confidence score (top-right of box)
        if show_confidence:
            conf_label = f"{confidence:.2f}"
            (conf_w, conf_h), _ = cv2.getTextSize(
                conf_label, self.font, 0.5, 1
            )
            
            cv2.rectangle(
                frame,
                (x2 - conf_w - 10, y1 - conf_h - 10),
                (x2, y1),
                color,
                -1
            )
            
            cv2.putText(
                frame, conf_label, (x2 - conf_w - 5, y1 - 5), 
                self.font, 0.5, (0, 0, 0), 1
            )
        
        return frame
    
    def _draw_weapons(
        self,
        frame: np.ndarray,
        weapons: List[Dict[str, Any]],
        show_confidence: bool
    ) -> np.ndarray:
        """Draw weapon bounding boxes with labels"""
        for weapon in weapons:
            bbox = weapon.get('bbox')
            # Staleness Drop sentinel: bbox stripped by _gun_model_bg when inference
            # latency exceeded MAX_SPATIAL_LATENCY. Detection is real (alert fired),
            # but spatial coordinates are too old to draw — skip box rendering only.
            if not bbox or len(bbox) < 4:
                continue
            x1, y1, x2, y2 = map(int, bbox)
            
            # Clamp to frame bounds
            h, w = frame.shape[:2]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w - 1))
            y2 = max(0, min(y2, h - 1))
            
            # RED for weapons (CRITICAL)
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_WEAPON, 3)
            
            # Label
            weapon_class = weapon['class'].upper()
            label = f"! {weapon_class}"
            if show_confidence:
                label += f" {weapon['confidence']:.2f}"
            
            # Background
            (text_w, text_h), baseline = cv2.getTextSize(
                label, self.font, 0.7, 2
            )
            
            cv2.rectangle(
                frame, 
                (x1, y1 - text_h - baseline - 10), 
                (x1 + text_w + 10, y1), 
                self.COLOR_WEAPON, 
                -1
            )
            
            # Text
            cv2.putText(
                frame, label, (x1 + 5, y1 - baseline - 5), 
                self.font, 0.7, (255, 255, 255), 2
            )
        
        return frame
    
    def _draw_emotion(
        self,
        frame: np.ndarray,
        face_bbox: Tuple[int, int, int, int],
        emotion: str
    ) -> np.ndarray:
        """Draw emotion label below face.
        
        BBOX FORMAT FIX: face_bbox is (x1, y1, x2, y2).
        """
        x1, y1, x2, y2 = face_bbox
        
        label = f"Emotion: {emotion.capitalize()}"
        
        cv2.putText(
            frame, label, (x1, y2 + 25), 
            self.font, self.font_scale, self.COLOR_EMOTION, self.font_thickness
        )
        
        return frame
    
    def _draw_age(
        self,
        frame: np.ndarray,
        face_bbox: Tuple[int, int, int, int],
        age: int
    ) -> np.ndarray:
        """Draw age estimate below emotion.
        
        BBOX FORMAT FIX: face_bbox is (x1, y1, x2, y2).
        """
        x1, y1, x2, y2 = face_bbox
        
        label = f"Age: {age}"
        
        cv2.putText(
            frame, label, (x1, y2 + 50), 
            self.font, self.font_scale, self.COLOR_AGE, self.font_thickness
        )
        
        return frame
    
    def _draw_pose(
        self,
        frame: np.ndarray,
        pose_data: Dict[str, Any]
    ) -> np.ndarray:
        """Draw pose skeleton with cyan dotted lines.
        
        Uses dashed lines for better visual appearance and draws
        filled circles at keypoint joints for clarity.
        """
        if not pose_data or 'keypoints' not in pose_data:
            return frame
        
        keypoints = pose_data['keypoints']
        h, w = frame.shape[:2]
        
        # MediaPipe Pose landmark connections (body skeleton)
        POSE_CONNECTIONS = [
            # Face
            (0, 1), (1, 2), (2, 3), (3, 7),   # Left eye to left ear
            (0, 4), (4, 5), (5, 6), (6, 8),   # Right eye to right ear
            # Shoulders and arms
            (9, 10),                            # Mouth
            (11, 12),                           # Shoulders
            (11, 13), (13, 15),                # Left arm
            (12, 14), (14, 16),                # Right arm
            # Torso
            (11, 23), (12, 24),                # Shoulders to hips
            (23, 24),                           # Hips
            # Legs
            (23, 25), (25, 27), (27, 29), (29, 31),  # Left leg
            (24, 26), (26, 28), (28, 30), (30, 32),  # Right leg
        ]
        
        # Draw connections (cyan dashed lines)
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in keypoints and end_idx in keypoints:
                start_kp = keypoints[start_idx]
                end_kp = keypoints[end_idx]
                
                # Check visibility threshold
                if start_kp.get('visibility', 0) > 0.5 and end_kp.get('visibility', 0) > 0.5:
                    start_x = int(start_kp['x'])
                    start_y = int(start_kp['y'])
                    end_x = int(end_kp['x'])
                    end_y = int(end_kp['y'])
                    
                    # Validate coords are within frame
                    if not (0 <= start_x < w and 0 <= start_y < h):
                        continue
                    if not (0 <= end_x < w and 0 <= end_y < h):
                        continue
                    
                    # Draw dashed/dotted line
                    self._draw_dashed_line(
                        frame,
                        (start_x, start_y),
                        (end_x, end_y),
                        self.COLOR_POSE,
                        thickness=2,
                        dash_length=8,
                        gap_length=5
                    )
        
        # Draw keypoints (cyan filled circles with dark outline)
        for idx, kp in keypoints.items():
            if kp.get('visibility', 0) > 0.5:
                x = int(kp['x'])
                y = int(kp['y'])
                
                # Validate within frame
                if 0 <= x < w and 0 <= y < h:
                    # Outer circle (dark border)
                    cv2.circle(frame, (x, y), 5, (0, 0, 0), -1)
                    # Inner circle (cyan fill)
                    cv2.circle(frame, (x, y), 4, self.COLOR_POSE, -1)
        
        return frame
    
    def _draw_dashed_line(
        self,
        frame: np.ndarray,
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        color: Tuple[int, int, int],
        thickness: int = 2,
        dash_length: int = 8,
        gap_length: int = 5
    ):
        """Draw a dashed line between two points."""
        x1, y1 = pt1
        x2, y2 = pt2
        
        dx = x2 - x1
        dy = y2 - y1
        dist = np.sqrt(dx * dx + dy * dy)
        
        if dist < 1:
            return
        
        # Normalize direction
        dx_norm = dx / dist
        dy_norm = dy / dist
        
        total_segment = dash_length + gap_length
        num_segments = int(dist / total_segment)
        
        for i in range(num_segments + 1):
            start_dist = i * total_segment
            end_dist = min(start_dist + dash_length, dist)
            
            sx = int(x1 + dx_norm * start_dist)
            sy = int(y1 + dy_norm * start_dist)
            ex = int(x1 + dx_norm * end_dist)
            ey = int(y1 + dy_norm * end_dist)
            
            cv2.line(frame, (sx, sy), (ex, ey), color, thickness)
    
    def _draw_objects(
        self,
        frame: np.ndarray,
        objects: List[Dict[str, Any]],
        show_confidence: bool
    ) -> np.ndarray:
        """Draw general object detections"""
        for obj in objects:
            bbox = obj['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Orange for general objects
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_OBJECT, 2)
            
            # Label
            obj_class = obj['class'].capitalize()
            label = obj_class
            if show_confidence:
                label += f" {obj['confidence']:.2f}"
            
            cv2.putText(
                frame, label, (x1, y1-10), 
                self.font, 0.5, self.COLOR_OBJECT, 1
            )
        
        return frame
    
    def _draw_spoofing_warning(self, frame: np.ndarray) -> np.ndarray:
        """Draw spoofing detection warning"""
        h, w = frame.shape[:2]
        
        label = "! SPOOFING DETECTED"
        
        # Background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, self.font, 1.0, 3
        )
        
        cv2.rectangle(
            frame, 
            (10, 10), 
            (text_w+30, text_h+baseline+20), 
            self.COLOR_SPOOFING, 
            -1
        )
        
        # Text
        cv2.putText(
            frame, label, (20, text_h+15), 
            self.font, 1.0, (255, 255, 255), 3
        )
        
        return frame


# Global instance
frame_annotator = FrameAnnotator()
