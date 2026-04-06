"""
RTSP client for IP camera streams
"""
import cv2
import numpy as np
from typing import Optional
from loguru import logger
import time

class RTSPClient:
    """Client for RTSP IP camera streams"""
    
    def __init__(self, rtsp_url: str, reconnect_delay: int = 5):
        """
        Initialize RTSP client
        
        Args:
            rtsp_url: RTSP stream URL (e.g., rtsp://username:password@ip:port/stream)
            reconnect_delay: Seconds to wait before reconnection attempt
        """
        self.rtsp_url = rtsp_url
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.is_connected = False
        self.last_frame_time = 0
        self.frame_timeout = 10  # seconds
    
    def connect(self) -> bool:
        """
        Connect to RTSP stream
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Connecting to RTSP stream: {self._mask_url()}")
            
            # Use FFMPEG backend for better RTSP support
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self.cap.isOpened():
                logger.error("Failed to open RTSP stream")
                return False
            
            # Test read
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to read test frame from RTSP stream")
                self.cap.release()
                return False
            
            self.is_connected = True
            self.last_frame_time = time.time()
            logger.info(f"RTSP stream connected: {frame.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream: {e}")
            return False
    
    def _mask_url(self) -> str:
        """Mask credentials in URL for logging"""
        try:
            if '@' in self.rtsp_url:
                parts = self.rtsp_url.split('@')
                protocol_part = parts[0].split('//')[0]
                return f"{protocol_part}//***:***@{parts[1]}"
            return self.rtsp_url
        except:
            return "rtsp://***"
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read frame from RTSP stream
        
        Returns:
            Frame as numpy array (BGR) or None if failed
        """
        if not self.cap or not self.is_connected:
            logger.warning("RTSP stream not connected")
            return None
        
        try:
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("Failed to read frame from RTSP stream")
                
                # Check for timeout
                if time.time() - self.last_frame_time > self.frame_timeout:
                    logger.error("Frame timeout - attempting reconnection")
                    self.reconnect()
                
                return None
            
            self.last_frame_time = time.time()
            return frame
            
        except Exception as e:
            logger.error(f"Error reading RTSP frame: {e}")
            return None
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to RTSP stream"""
        logger.info("Attempting RTSP reconnection...")
        
        self.disconnect()
        time.sleep(self.reconnect_delay)
        
        return self.connect()
    
    def get_properties(self) -> dict:
        """Get current stream properties"""
        if not self.cap:
            return {}
        
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "codec": int(self.cap.get(cv2.CAP_PROP_FOURCC)),
            "is_connected": self.is_connected,
        }
    
    def set_resolution(self, width: int, height: int):
        """Set stream resolution (may not work with all RTSP streams)"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    def disconnect(self):
        """Release RTSP stream resources"""
        if self.cap:
            self.cap.release()
            self.is_connected = False
            logger.info("RTSP stream disconnected")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect()


class RTSPStreamReader:
    """Advanced RTSP reader with threading for better performance"""
    
    def __init__(self, rtsp_url: str):
        import threading
        
        self.client = RTSPClient(rtsp_url)
        self.latest_frame = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()
    
    def start(self) -> bool:
        """Start reading frames in background thread"""
        if not self.client.connect():
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        return True
    
    def _read_loop(self):
        """Background thread that continuously reads frames"""
        while self.is_running:
            frame = self.client.read_frame()
            
            if frame is not None:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.1)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame (non-blocking)"""
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def stop(self):
        """Stop background reading"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.client.disconnect()