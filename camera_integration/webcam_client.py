"""
USB Webcam client for local camera access
"""
import cv2
import numpy as np
from typing import Optional
from loguru import logger

class WebcamClient:
    """Client for USB webcam access"""
    
    def __init__(self, device_id: int = 0):
        """
        Initialize webcam client
        
        Args:
            device_id: Webcam device index (usually 0 for default webcam)
        """
        self.device_id = device_id
        self.cap = None
        self.is_opened = False
    
    def connect(self) -> bool:
        """
        Connect to webcam
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open webcam {self.device_id}")
                return False
            
            self.is_opened = True
            logger.info(f"Webcam {self.device_id} connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to webcam: {e}")
            return False
    
    def set_resolution(self, width: int, height: int) -> bool:
        """Set webcam resolution"""
        if not self.cap:
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        logger.info(f"Resolution set to {actual_width}x{actual_height}")
        return True
    
    def set_fps(self, fps: int) -> bool:
        """Set webcam FPS"""
        if not self.cap:
            return False
        
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"FPS set to {actual_fps}")
        return True
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read single frame from webcam
        
        Returns:
            Frame as numpy array (BGR) or None if failed
        """
        if not self.cap or not self.is_opened:
            logger.warning("Webcam not connected")
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("Failed to read frame from webcam")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return None
    
    def get_properties(self) -> dict:
        """Get current webcam properties"""
        if not self.cap:
            return {}
        
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "brightness": self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
            "contrast": self.cap.get(cv2.CAP_PROP_CONTRAST),
            "saturation": self.cap.get(cv2.CAP_PROP_SATURATION),
        }
    
    def disconnect(self):
        """Release webcam resources"""
        if self.cap:
            self.cap.release()
            self.is_opened = False
            logger.info(f"Webcam {self.device_id} disconnected")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect()