"""
Multi-camera manager for handling multiple video sources
"""
import cv2
import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import threading
from loguru import logger

@dataclass
class CameraConfig:
    """Camera configuration"""
    id: int
    name: str
    source: str  # "0" for webcam, "rtsp://..." for IP camera, or file path
    fps: int = 10
    resolution: tuple = (1280, 720)
    enabled: bool = True
    buffer_size: int = 1  # Number of frames to buffer

class CameraManager:
    """Manages multiple camera sources"""
    
    def __init__(self):
        self.cameras: Dict[int, cv2.VideoCapture] = {}
        self.configs: Dict[int, CameraConfig] = {}
        self.is_running: Dict[int, bool] = {}
        self.frame_callbacks: Dict[int, List[Callable]] = {}
        self.lock = threading.Lock()
        
    def add_camera(self, config: CameraConfig) -> bool:
        """
        Add new camera source
        
        Args:
            config: Camera configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse source - handle webcam indices properly
            if config.source.strip().isdigit():
                source = int(config.source)
            else:
                source = config.source
            
            # Open camera
            cap = cv2.VideoCapture(source)
            
            if not cap.isOpened():
                logger.error(f"Failed to open camera {config.id}: {config.source}")
                return False
            
            # Set properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.resolution[1])
            cap.set(cv2.CAP_PROP_FPS, config.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, config.buffer_size)
            
            # Store camera
            with self.lock:
                self.cameras[config.id] = cap
                self.configs[config.id] = config
                self.is_running[config.id] = False
                self.frame_callbacks[config.id] = []
            
            logger.info(f"Camera {config.id} ({config.name}) added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding camera {config.id}: {e}")
            return False
    
    def remove_camera(self, camera_id: int) -> bool:
        """
        Remove camera and release resources
        
        Args:
            camera_id: Camera ID to remove
            
        Returns:
            True if successful
        """
        with self.lock:
            if camera_id in self.cameras:
                # Stop if running
                if self.is_running.get(camera_id):
                    self.stop_camera(camera_id)
                
                # Release camera
                self.cameras[camera_id].release()
                
                # Remove from dictionaries
                del self.cameras[camera_id]
                del self.configs[camera_id]
                del self.is_running[camera_id]
                if camera_id in self.frame_callbacks:
                    del self.frame_callbacks[camera_id]
                
                logger.info(f"Camera {camera_id} removed")
                return True
        
        return False
    
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """
        Get single frame from camera
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Frame as numpy array or None
        """
        if camera_id not in self.cameras:
            return None
        
        try:
            cap = self.cameras[camera_id]
            ret, frame = cap.read()
            
            if ret:
                return frame
            else:
                logger.warning(f"Failed to read frame from camera {camera_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading frame from camera {camera_id}: {e}")
            return None
    
    def register_callback(self, camera_id: int, callback: Callable):
        """
        Register callback for frame processing
        
        Args:
            camera_id: Camera ID
            callback: Async function(camera_id, frame) to call for each frame
        """
        if camera_id in self.frame_callbacks:
            self.frame_callbacks[camera_id].append(callback)
    
    async def stream_frames(self, camera_id: int):
        """
        Stream frames continuously from camera
        
        Args:
            camera_id: Camera ID to stream from
        """
        if camera_id not in self.cameras:
            logger.error(f"Camera {camera_id} not found")
            return
        
        config = self.configs[camera_id]
        frame_delay = 1.0 / config.fps
        frame_counter = 0
        
        logger.info(f"Starting stream for camera {camera_id}")
        
        with self.lock:
            self.is_running[camera_id] = True
        
        while self.is_running.get(camera_id, False):
            try:
                frame = self.get_frame(camera_id)
                
                if frame is not None:
                    frame_counter += 1
                    
                    # Call all registered callbacks
                    callbacks = self.frame_callbacks.get(camera_id, [])
                    for callback in callbacks:
                        try:
                            await callback(camera_id, frame, frame_counter)
                        except Exception as e:
                            logger.error(f"Callback error for camera {camera_id}: {e}")
                
                # Control frame rate
                await asyncio.sleep(frame_delay)
                
            except Exception as e:
                logger.error(f"Error streaming camera {camera_id}: {e}")
                await asyncio.sleep(1)  # Wait before retry
        
        logger.info(f"Stopped streaming camera {camera_id}")
    
    def start_camera(self, camera_id: int):
        """
        Start streaming from specific camera
        
        Args:
            camera_id: Camera ID to start
        """
        if camera_id not in self.cameras:
            logger.error(f"Camera {camera_id} not found")
            return False
        
        if not self.is_running.get(camera_id, False):
            # Start streaming task
            asyncio.create_task(self.stream_frames(camera_id))
            logger.info(f"Camera {camera_id} started")
            return True
        
        return False
    
    def stop_camera(self, camera_id: int):
        """
        Stop streaming from specific camera
        
        Args:
            camera_id: Camera ID to stop
        """
        if camera_id in self.is_running:
            self.is_running[camera_id] = False
            logger.info(f"Camera {camera_id} stop signal sent")
    
    def start_all(self):
        """Start streaming from all cameras"""
        for camera_id in self.cameras.keys():
            self.start_camera(camera_id)
    
    def stop_all(self):
        """Stop all camera streams"""
        for camera_id in list(self.is_running.keys()):
            self.stop_camera(camera_id)
    
    def get_camera_info(self, camera_id: int) -> Optional[dict]:
        """
        Get camera information
        
        Args:
            camera_id: Camera ID
            
        Returns:
            Dict with camera info or None
        """
        if camera_id not in self.cameras:
            return None
        
        cap = self.cameras[camera_id]
        config = self.configs[camera_id]
        
        return {
            "id": camera_id,
            "name": config.name,
            "source": config.source,
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "resolution": (
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ),
            "is_opened": cap.isOpened(),
            "is_running": self.is_running.get(camera_id, False),
            "enabled": config.enabled
        }
    
    def get_all_camera_info(self) -> List[dict]:
        """Get info for all cameras"""
        return [
            self.get_camera_info(camera_id)
            for camera_id in self.cameras.keys()
        ]
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop_all()
        for cap in self.cameras.values():
            cap.release()