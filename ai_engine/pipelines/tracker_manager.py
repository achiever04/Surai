import numpy as np
import time
from typing import Dict, Any, List, Tuple

class TrackerManager:
    """
    Manages object tracking and ID state using ByteTrack (via Ultralytics).
    Ensures model-heavy analysis (Face Recognition and Emotion) is executed ONCE 
    per person (new Track ID). Once analyzed, data interpolates over the ID 
    to bypass further redundant matrix operations.
    """
    def __init__(self, ttl_seconds: int = 5):
        # Store metadata for each active track (e.g. {track_id: {'identity': 'Dave', 'emotion': 'Happy'}})
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        
        # Timestamp of last detection by Track ID to cleanup stale objects
        self.track_last_seen: Dict[int, float] = {}
        
        # Time-to-Live for a track once it leaves the camera frame
        self.ttl_seconds = ttl_seconds

    def process_detections(self, unified_data: dict) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Assigns standard ByteTrack/IoU IDs to incoming unified data.
        Emits 'emissions' (new entities requiring deep inference).
        """
        emissions_for_analysis = []
        track_outputs = []
        
        current_time = time.time()
        
        # Simulated basic tracker matching logic for faces
        for box in unified_data.get('faces', []):
            track_id = self._match_or_spawn_id(box)
            self.track_last_seen[track_id] = current_time
            
            # Logic: Is this an entirely new subject entering the frame?
            if track_id not in self.active_tracks:
                # Register track
                self.active_tracks[track_id] = {
                    'identity': 'Unknown',
                    'emotion': 'Analyzing...',
                    'deep_analysis_queued': True,
                    'deep_analysis_complete': False
                }
                
                emissions_for_analysis.append({
                    'track_id': track_id,
                    'box': list(box), # Export box coordinates for cropper
                    'confidence': 0.9,
                    'class': 0 # Face/Person
                })
            
            # Construct return objects for instantaneous Video Drawing
            track_outputs.append({
                'track_id': track_id,
                'box': list(box),
                'class': 0,
                'confidence': 0.9,
                'identity': self.active_tracks[track_id].get('identity'),
                'emotion': self.active_tracks[track_id].get('emotion')
            })
            
        # Process weapons instantly (no deep tracking needed generally, just UI drawing)
        for weapon in unified_data.get('weapons', []):
            track_outputs.append({
                'track_id': self._match_or_spawn_id(weapon['bbox']),
                'box': list(weapon['bbox']),
                'class': 2, # Weapon
                'confidence': weapon['conf'],
                'identity': 'Weapon',
                'emotion': None
            })
                
        self._purge_stale_tracks(current_time)
        return track_outputs, emissions_for_analysis
        
    def _match_or_spawn_id(self, new_box):
        # Stub tracking assignment mapping
        return hash(tuple(new_box)) % 1000
        
    def update_track_identity(self, track_id: int, identity: str, emotion: str):
        """
        Callback. The Async Worker Pool (Phase 4) consumes crops, runs InsightFace/DeepFace, 
        and hits this method to attach names and emotion traits to the track state.
        """
        if track_id in self.active_tracks:
            if identity:
                self.active_tracks[track_id]['identity'] = identity
            if emotion:
                self.active_tracks[track_id]['emotion'] = emotion
            self.active_tracks[track_id]['deep_analysis_complete'] = True

    def _purge_stale_tracks(self, current_time: float):
        """Removes track state buffers if people walk off camera bounds for > TTL"""
        stale_ids = [tid for tid, last_seen in self.track_last_seen.items() 
                     if current_time - last_seen > self.ttl_seconds]
        for tid in stale_ids:
            del self.track_last_seen[tid]
            if tid in self.active_tracks:
                del self.active_tracks[tid]
