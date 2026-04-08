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

    def process_detections(self, yolo_results) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses YOLO output (which natively runs ByteTrack via .track())
        Decides which bounding box crops get emitted to the Deep Analysis Async Queue.
        
        Returns:
            track_outputs: List of dicts strictly for UI drawing (instant real-time display)
            emissions_for_analysis: List of box crops that need heavy face logic
        """
        emissions_for_analysis = []
        track_outputs = []
        
        current_time = time.time()
        
        # Validate track IDs are present in the output
        if yolo_results.boxes is not None and yolo_results.boxes.id is not None:
            # Transfer tensor arrays to CPU numpy iteratively
            boxes = yolo_results.boxes.xyxy.cpu().numpy()
            track_ids = yolo_results.boxes.id.int().cpu().numpy()
            classes = yolo_results.boxes.cls.int().cpu().numpy()
            confs = yolo_results.boxes.conf.cpu().numpy()
            
            for box, track_id, cls, conf in zip(boxes, track_ids, classes, confs):
                track_id = int(track_id)
                self.track_last_seen[track_id] = current_time
                
                # In most standard YOLO datasets (COCO format), 0 is person.
                # Adjust these indices if your Unified custom model has different targets
                # (e.g., 1 for Face, 2 for Weapon, etc.)
                is_target_for_heavy_analysis = (cls == 0 or cls == 1) 
                
                # Logic: Is this an entirely new subject entering the frame?
                if track_id not in self.active_tracks:
                    # Register track
                    self.active_tracks[track_id] = {
                        'identity': 'Unknown',
                        'emotion': 'Analyzing...',
                        'deep_analysis_queued': is_target_for_heavy_analysis,
                        'deep_analysis_complete': not is_target_for_heavy_analysis
                    }
                    
                    if is_target_for_heavy_analysis:
                        emissions_for_analysis.append({
                            'track_id': track_id,
                            'box': box.tolist(), # Export box coordinates for cropper
                            'confidence': float(conf),
                            'class': int(cls)
                        })
                else:
                    # Logic: We already know this track ID. Wait for Async Queue to fill 
                    # the dict state via update_track_identity callback.
                    pass
                
                # Construct return objects for instantaneous Video Drawing
                track_outputs.append({
                    'track_id': track_id,
                    'box': box.tolist(),
                    'class': int(cls),
                    'confidence': float(conf),
                    'identity': self.active_tracks[track_id].get('identity'),
                    'emotion': self.active_tracks[track_id].get('emotion')
                })
                
        self._purge_stale_tracks(current_time)
        return track_outputs, emissions_for_analysis
        
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
