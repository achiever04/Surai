"""
Video recorder for evidence clip recording
"""
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from loguru import logger
import queue
import threading

class VideoRecorder:
    """Record video clips for evidence"""
    
    def __init__(
        self,
        output_dir: str = "storage/local/evidence",
        fps: int = 10,
        codec: str = "mp4v",
        resolution: tuple = (1280, 720)
    ):
        """
        Initialize video recorder
        
        Args:
            output_dir: Directory to save video clips
            fps: Frames per second
            codec: Video codec (mp4v, h264, etc.)
            resolution: Video resolution (width, height)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.codec = cv2.VideoWriter_fourcc(*codec)
        self.resolution = resolution
        
        self.writer = None
        self.current_clip_path = None
        self.is_recording = False
    
    def start_recording(self, clip_name: Optional[str] = None) -> str:
        """
        Start recording video clip
        
        Args:
            clip_name: Optional custom clip name
            
        Returns:
            Path to clip being recorded
        """
        if self.is_recording:
            logger.warning("Already recording, stopping current clip first")
            self.stop_recording()
        
        # Generate clip name if not provided
        if clip_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clip_name = f"clip_{timestamp}.mp4"
        
        self.current_clip_path = self.output_dir / clip_name
        
        # Create video writer
        self.writer = cv2.VideoWriter(
            str(self.current_clip_path),
            self.codec,
            self.fps,
            self.resolution
        )
        
        if not self.writer.isOpened():
            logger.error("Failed to open video writer")
            return None
        
        self.is_recording = True
        logger.info(f"Started recording: {self.current_clip_path}")
        
        return str(self.current_clip_path)
    
    def write_frame(self, frame: np.ndarray) -> bool:
        """
        Write frame to current clip
        
        Args:
            frame: Frame to write (BGR format)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_recording or self.writer is None:
            logger.warning("Not currently recording")
            return False
        
        try:
            # Resize frame if needed
            if frame.shape[:2][::-1] != self.resolution:
                frame = cv2.resize(frame, self.resolution)
            
            self.writer.write(frame)
            return True
            
        except Exception as e:
            logger.error(f"Error writing frame: {e}")
            return False
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and finalize clip
        
        Returns:
            Path to recorded clip or None
        """
        if not self.is_recording:
            return None
        
        if self.writer:
            self.writer.release()
            self.writer = None
        
        self.is_recording = False
        
        clip_path = str(self.current_clip_path)
        logger.info(f"Stopped recording: {clip_path}")
        
        self.current_clip_path = None
        
        return clip_path
    
    def record_clip(
        self,
        frames: List[np.ndarray],
        clip_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Record a complete clip from list of frames
        
        Args:
            frames: List of frames to record
            clip_name: Optional custom clip name
            
        Returns:
            Path to saved clip
        """
        if not frames:
            logger.warning("No frames to record")
            return None
        
        clip_path = self.start_recording(clip_name)
        
        for frame in frames:
            self.write_frame(frame)
        
        return self.stop_recording()
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.is_recording:
            self.stop_recording()


class BufferedRecorder:
    """
    Buffered recorder that keeps last N seconds in memory
    Useful for recording events after they're detected
    """
    
    def __init__(
        self,
        buffer_seconds: int = 10,
        fps: int = 10,
        output_dir: str = "storage/local/evidence"
    ):
        """
        Initialize buffered recorder
        
        Args:
            buffer_seconds: Seconds of video to keep in buffer
            fps: Frames per second
            output_dir: Directory to save clips
        """
        self.buffer_size = buffer_seconds * fps
        self.fps = fps
        self.recorder = VideoRecorder(output_dir=output_dir, fps=fps)
        
        self.frame_buffer = queue.Queue(maxsize=self.buffer_size)
        self.is_active = False
    
    def add_frame(self, frame: np.ndarray):
        """
        Add frame to buffer
        
        Args:
            frame: Frame to buffer
        """
        # Remove oldest frame if buffer is full
        if self.frame_buffer.full():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                pass
        
        # Add new frame
        try:
            self.frame_buffer.put_nowait(frame.copy())
        except queue.Full:
            pass
    
    def save_buffer(
        self,
        event_id: str,
        post_event_seconds: int = 5
    ) -> Optional[str]:
        """
        Save buffered frames plus additional post-event frames
        
        Args:
            event_id: Event identifier for clip naming
            post_event_seconds: Seconds to record after event
            
        Returns:
            Path to saved clip
        """
        # Get all buffered frames
        frames = []
        while not self.frame_buffer.empty():
            try:
                frames.append(self.frame_buffer.get_nowait())
            except queue.Empty:
                break
        
        if not frames:
            logger.warning("No frames in buffer to save")
            return None
        
        clip_name = f"{event_id}_evidence.mp4"
        
        # Start recording
        clip_path = self.recorder.start_recording(clip_name)
        
        # Write buffered frames
        for frame in frames:
            self.recorder.write_frame(frame)
        
        # Continue recording for post_event_seconds
        # (calling code should continue feeding frames)
        self.is_active = True
        self.post_frames_remaining = post_event_seconds * self.fps
        
        return clip_path
    
    def write_post_frame(self, frame: np.ndarray) -> bool:
        """
        Write frame during post-event recording
        
        Returns:
            True if still recording, False if complete
        """
        if not self.is_active:
            return False
        
        self.recorder.write_frame(frame)
        self.post_frames_remaining -= 1
        
        if self.post_frames_remaining <= 0:
            self.recorder.stop_recording()
            self.is_active = False
            return False
        
        return True