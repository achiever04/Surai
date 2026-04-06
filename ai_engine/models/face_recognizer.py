"""
Face recognition using InsightFace (CPU-optimized)
"""
import numpy as np
from insightface.app import FaceAnalysis
from typing import List, Optional, Tuple
import cv2

class FaceRecognizer:
    def __init__(self, model_name: str = "buffalo_l", ctx_id: int = -1):
        """
        Initialize InsightFace model
        
        Args:
            model_name: Model name (buffalo_l for best CPU performance)
            ctx_id: Context ID (-1 for CPU, 0+ for GPU)
        """
        self.app = FaceAnalysis(
            name=model_name,
            providers=['CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        
        # PERFORMANCE FIX: Cache app.get() results to avoid running InsightFace
        # detection multiple times on the same frame. detect() and extract_embedding()
        # both call app.get() — caching eliminates the redundant 2nd call.
        self._cached_frame_id = None
        self._cached_faces = None
    
    def _get_faces(self, image: np.ndarray):
        """
        Get faces with frame-level caching.
        Avoids redundant app.get() calls when detect() and extract_embedding()
        are called on the same frame.
        """
        # Use a simple identity check (id of numpy array) for speed
        frame_id = id(image)
        if frame_id == self._cached_frame_id and self._cached_faces is not None:
            return self._cached_faces
        
        faces = self.app.get(image)
        self._cached_frame_id = frame_id
        self._cached_faces = faces
        return faces
    
    def extract_embedding(
        self,
        image: np.ndarray,
        bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """
        Extract face embedding (512-dimensional vector)
        
        Args:
            image: BGR image
            bbox: Optional bounding box to speed up detection
            
        Returns:
            512-dim embedding vector or None if no face found
        """
        # PERFORMANCE FIX: Use cached faces instead of calling app.get() again
        faces = self._get_faces(image)
        
        if len(faces) == 0:
            return None
        
        # If bbox provided, find closest face
        if bbox:
            x1, y1, x2, y2 = bbox
            bbox_center = ((x1 + x2) / 2, (y1 + y2) / 2)
            
            closest_face = min(
                faces,
                key=lambda f: np.linalg.norm(
                    np.array([f.bbox[0] + f.bbox[2], f.bbox[1] + f.bbox[3]]) / 2 - bbox_center
                )
            )
            return closest_face.normed_embedding
        
        # Otherwise use largest face
        largest_face = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )
        
        return largest_face.normed_embedding
    
    def extract_multiple_embeddings(
        self,
        image: np.ndarray
    ) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Extract embeddings for all faces in image
        
        Returns:
            List of (embedding, bbox) tuples
        """
        # PERFORMANCE FIX: Use cached faces
        faces = self._get_faces(image)
        
        results = []
        for face in faces:
            bbox = tuple(map(int, face.bbox))
            results.append((face.normed_embedding, bbox))
        
        return results
    
    def detect(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces and return bounding boxes (compatible with FaceDetector interface)
        
        This method makes FaceRecognizer compatible with the face_detector interface,
        allowing it to be used as both detector and recognizer.
        
        Args:
            image: BGR image
            
        Returns:
            List of bounding boxes in (x1, y1, x2, y2) format
        """
        # PERFORMANCE FIX: Use cached faces instead of calling app.get() again
        faces = self._get_faces(image)
        
        bboxes = []
        for face in faces:
            # InsightFace returns bbox as [x1, y1, x2, y2]
            bbox = tuple(map(int, face.bbox))
            bboxes.append(bbox)
        
        return bboxes
    
    def compare_embeddings(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        threshold: float = 0.4
    ) -> Tuple[bool, float]:
        """
        Compare two face embeddings
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            threshold: Similarity threshold (0.4 is recommended for InsightFace)
            
        Returns:
            (is_match, similarity_score)
        """
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        is_match = similarity >= threshold
        
        return is_match, float(similarity)
    
    def search_in_gallery(
        self,
        query_embedding: np.ndarray,
        gallery_embeddings: List[np.ndarray],
        threshold: float = 0.4
    ) -> Optional[Tuple[int, float]]:
        """
        Search for best match in gallery
        
        Returns:
            (index, similarity) of best match or None
        """
        if not gallery_embeddings:
            return None
        
        similarities = [
            float(np.dot(query_embedding, gallery_emb))
            for gallery_emb in gallery_embeddings
        ]
        
        best_idx = int(np.argmax(similarities))
        best_sim = similarities[best_idx]
        
        if best_sim >= threshold:
            return best_idx, best_sim
        
        return None
    
    def batch_extract_embeddings(
        self,
        images: List[np.ndarray]
    ) -> List[Optional[np.ndarray]]:
        """
        Extract embeddings from multiple images (batch processing)
        """
        embeddings = []
        for image in images:
            embedding = self.extract_embedding(image)
            embeddings.append(embedding)
        
        return embeddings