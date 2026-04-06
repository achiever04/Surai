"""
Multi-camera person tracking pipeline
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrackedPerson:
    """Tracked person across cameras"""
    track_id: int
    embeddings: List[np.ndarray]
    camera_sightings: List[Dict]
    first_seen: datetime
    last_seen: datetime
    confidence: float


class MultiCameraTracker:
    """Track persons across multiple cameras"""
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self.active_tracks: Dict[int, TrackedPerson] = {}
        self.next_track_id = 1
    
    def update_tracks(
        self,
        camera_id: int,
        embeddings: List[np.ndarray],
        detections: List[Dict]
    ) -> List[Tuple[int, int]]:
        """
        Update tracks with new detections
        
        Args:
            camera_id: Camera identifier
            embeddings: List of face embeddings
            detections: List of detection metadata
            
        Returns:
            List of (track_id, detection_idx) pairs
        """
        assignments = []
        
        for idx, embedding in enumerate(embeddings):
            # Try to match with existing tracks
            matched_track_id = self._match_to_existing_track(embedding)
            
            if matched_track_id is not None:
                # Update existing track
                track = self.active_tracks[matched_track_id]
                track.embeddings.append(embedding)
                track.camera_sightings.append({
                    'camera_id': camera_id,
                    'timestamp': datetime.utcnow(),
                    'detection': detections[idx]
                })
                track.last_seen = datetime.utcnow()
                
                assignments.append((matched_track_id, idx))
            else:
                # Create new track
                new_track_id = self.next_track_id
                self.next_track_id += 1
                
                self.active_tracks[new_track_id] = TrackedPerson(
                    track_id=new_track_id,
                    embeddings=[embedding],
                    camera_sightings=[{
                        'camera_id': camera_id,
                        'timestamp': datetime.utcnow(),
                        'detection': detections[idx]
                    }],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    confidence=0.9
                )
                
                assignments.append((new_track_id, idx))
        
        # Clean up old tracks
        self._cleanup_old_tracks()
        
        return assignments
    
    def _match_to_existing_track(
        self,
        embedding: np.ndarray
    ) -> Optional[int]:
        """Match embedding to existing track"""
        best_match_id = None
        best_similarity = self.similarity_threshold
        
        for track_id, track in self.active_tracks.items():
            # Compare with recent embeddings
            recent_embeddings = track.embeddings[-5:]  # Last 5 embeddings
            
            for track_embedding in recent_embeddings:
                similarity = np.dot(embedding, track_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_id = track_id
        
        return best_match_id
    
    def _cleanup_old_tracks(self, max_age_seconds: int = 300):
        """Remove tracks not seen recently"""
        now = datetime.utcnow()
        to_remove = []
        
        for track_id, track in self.active_tracks.items():
            age = (now - track.last_seen).total_seconds()
            if age > max_age_seconds:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.active_tracks[track_id]
    
    def get_track(self, track_id: int) -> Optional[TrackedPerson]:
        """Get tracked person by ID"""
        return self.active_tracks.get(track_id)
    
    def get_all_active_tracks(self) -> List[TrackedPerson]:
        """Get all currently active tracks"""
        return list(self.active_tracks.values())
    
    def get_person_trajectory(self, track_id: int) -> List[Dict]:
        """Get movement trajectory for tracked person"""
        track = self.active_tracks.get(track_id)
        if not track:
            return []
        
        return track.camera_sightings