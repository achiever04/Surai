"""
Video preprocessing utilities
"""
import cv2
import numpy as np
from typing import Iterator, Optional, Tuple
from pathlib import Path
from loguru import logger


class VideoPreprocessor:
    """Preprocess video streams and files"""
    
    def __init__(self, video_source):
        """
        Initialize video preprocessor
        
        Args:
            video_source: Video file path or camera index
        """
        self.video_source = video_source
        self.cap = None
        self.fps = None
        self.frame_count = None
        self.width = None
        self.height = None
    
    def open(self) -> bool:
        """Open video source"""
        try:
            if isinstance(self.video_source, (int, str)):
                self.cap = cv2.VideoCapture(self.video_source)
            else:
                self.cap = self.video_source
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {self.video_source}")
                return False
            
            # Get video properties
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"Video opened: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Error opening video: {e}")
            return False
    
    def read_frame(self) -> Optional[np.ndarray]:
        """Read single frame"""
        if not self.cap:
            return None
        
        ret, frame = self.cap.read()
        return frame if ret else None
    
    def frame_generator(
        self,
        skip_frames: int = 0,
        max_frames: Optional[int] = None
    ) -> Iterator[Tuple[int, np.ndarray]]:
        """
        Generate frames from video
        
        Args:
            skip_frames: Number of frames to skip between reads
            max_frames: Maximum number of frames to read
            
        Yields:
            (frame_number, frame)
        """
        frame_num = 0
        frames_read = 0
        
        while True:
            frame = self.read_frame()
            
            if frame is None:
                break
            
            if frame_num % (skip_frames + 1) == 0:
                yield frame_num, frame
                frames_read += 1
                
                if max_frames and frames_read >= max_frames:
                    break
            
            frame_num += 1
    
    def extract_frames_at_intervals(
        self,
        interval_seconds: float,
        output_dir: Optional[Path] = None
    ) -> list:
        """
        Extract frames at regular intervals
        
        Args:
            interval_seconds: Time interval between frames
            output_dir: Directory to save frames (optional)
            
        Returns:
            List of extracted frames
        """
        if not self.cap:
            return []
        
        frames = []
        interval_frames = int(interval_seconds * self.fps)
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        frame_num = 0
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                break
            
            if frame_num % interval_frames == 0:
                frames.append(frame)
                
                if output_dir:
                    filename = output_dir / f"frame_{frame_num:06d}.jpg"
                    cv2.imwrite(str(filename), frame)
            
            frame_num += 1
        
        logger.info(f"Extracted {len(frames)} frames")
        return frames
    
    def stabilize_video(
        self,
        smoothing_radius: int = 30
    ) -> Iterator[np.ndarray]:
        """
        Apply video stabilization
        
        Args:
            smoothing_radius: Radius for smoothing trajectory
            
        Yields:
            Stabilized frames
        """
        # Read all frames and calculate transforms
        transforms = []
        prev_gray = None
        
        for frame_num, frame in self.frame_generator():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_gray is not None:
                # Calculate optical flow
                prev_pts = cv2.goodFeaturesToTrack(
                    prev_gray,
                    maxCorners=200,
                    qualityLevel=0.01,
                    minDistance=30,
                    blockSize=3
                )
                
                if prev_pts is not None:
                    curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, prev_pts, None
                    )
                    
                    # Filter only good points
                    idx = np.where(status == 1)[0]
                    prev_pts = prev_pts[idx]
                    curr_pts = curr_pts[idx]
                    
                    # Find transformation matrix
                    m = cv2.estimateAffinePartial2D(prev_pts, curr_pts)[0]
                    
                    if m is not None:
                        transforms.append(m)
            
            prev_gray = gray
        
        # Calculate smooth trajectory
        # Apply transforms and yield stabilized frames
        # (Simplified implementation - full stabilization requires trajectory smoothing)
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        for frame_num, frame in self.frame_generator():
            if frame_num < len(transforms):
                # Apply stabilization transform
                m = transforms[frame_num]
                stabilized = cv2.warpAffine(
                    frame,
                    m,
                    (self.width, self.height)
                )
                yield stabilized
            else:
                yield frame
    
    def detect_scene_changes(
        self,
        threshold: float = 30.0
    ) -> list:
        """
        Detect scene changes in video
        
        Args:
            threshold: Difference threshold for scene change
            
        Returns:
            List of frame numbers where scenes change
        """
        scene_changes = []
        prev_hist = None
        
        for frame_num, frame in self.frame_generator():
            # Calculate histogram
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            if prev_hist is not None:
                # Calculate histogram difference
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                
                if diff > threshold:
                    scene_changes.append(frame_num)
            
            prev_hist = hist
        
        logger.info(f"Detected {len(scene_changes)} scene changes")
        return scene_changes
    
    def remove_duplicates(
        self,
        similarity_threshold: float = 0.95
    ) -> Iterator[np.ndarray]:
        """
        Remove duplicate/similar consecutive frames
        
        Args:
            similarity_threshold: Similarity threshold (0-1)
            
        Yields:
            Unique frames
        """
        prev_frame = None
        
        for frame_num, frame in self.frame_generator():
            if prev_frame is None:
                yield frame
            else:
                # Calculate similarity
                gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Use structural similarity
                diff = cv2.absdiff(gray1, gray2)
                similarity = 1.0 - (np.mean(diff) / 255.0)
                
                if similarity < similarity_threshold:
                    yield frame
            
            prev_frame = frame
    
    def close(self):
        """Release video resources"""
        if self.cap:
            self.cap.release()
            logger.info("Video closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def __del__(self):
        """Cleanup"""
        self.close()