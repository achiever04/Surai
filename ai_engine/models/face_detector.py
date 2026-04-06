"""
Face detection using MTCNN (lightweight for CPU)
"""
from mtcnn import MTCNN
import cv2
import numpy as np
from typing import List, Tuple, Optional

class FaceDetector:
    def __init__(self, min_confidence: float = 0.9):
        """
        Initialize MTCNN face detector
        
        Args:
            min_confidence: Minimum confidence threshold for detection
        """
        self.detector = MTCNN(min_face_size=20)
        self.min_confidence = min_confidence
    
    def detect(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in image
        
        Args:
            image: BGR image (OpenCV format)
            
        Returns:
            List of bounding boxes [(x1, y1, x2, y2), ...]
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        detections = self.detector.detect_faces(rgb_image)
        
        # Extract bounding boxes
        faces = []
        for detection in detections:
            if detection['confidence'] >= self.min_confidence:
                x, y, w, h = detection['box']
                # Convert to (x1, y1, x2, y2) format
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = x + w
                y2 = y + h
                faces.append((x1, y1, x2, y2))
        
        return faces
    
    def detect_with_landmarks(self, image: np.ndarray) -> List[dict]:
        """
        Detect faces with facial landmarks
        
        Returns:
            List of dicts with 'bbox', 'confidence', 'keypoints'
        """
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        detections = self.detector.detect_faces(rgb_image)
        
        results = []
        for detection in detections:
            if detection['confidence'] >= self.min_confidence:
                x, y, w, h = detection['box']
                results.append({
                    'bbox': (x, y, x + w, y + h),
                    'confidence': detection['confidence'],
                    'keypoints': detection['keypoints']
                })
        
        return results
    
    def get_largest_face(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the largest face in the image
        """
        faces = self.detect(image)
        
        if not faces:
            return None
        
        # Find largest face by area
        largest = max(faces, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]))
        return largest
    
    def crop_face(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        padding: float = 0.2
    ) -> np.ndarray:
        """
        Crop face from image with padding
        
        Args:
            image: Input image
            bbox: Bounding box (x1, y1, x2, y2)
            padding: Padding ratio (0.2 = 20% on each side)
            
        Returns:
            Cropped face image
        """
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        
        # Calculate padding
        face_w = x2 - x1
        face_h = y2 - y1
        pad_w = int(face_w * padding)
        pad_h = int(face_h * padding)
        
        # Apply padding with boundary checks
        x1_pad = max(0, x1 - pad_w)
        y1_pad = max(0, y1 - pad_h)
        x2_pad = min(w, x2 + pad_w)
        y2_pad = min(h, y2 + pad_h)
        
        return image[y1_pad:y2_pad, x1_pad:x2_pad]