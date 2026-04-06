"""
Shared Camera Manager for multi-stream webcam sharing

This module provides a singleton manager that opens each camera source ONCE
and allows multiple streams to read frames from the same source without conflicts.
"""
import cv2
import threading
import time
from typing import Dict, Optional, Tuple
from loguru import logger
import numpy as np


class SharedCameraSource:
    """Manages a single camera source with thread-safe frame sharing"""
    
    def __init__(self, source, source_key: str):
        self.source_key = source_key
        self.source = source  # Store original source for potential re-open
        self.cap = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.is_running = False
        self.consumer_count = 0
        self.consumer_lock = threading.Lock()
        self.capture_thread = None
        self.release_timer = None  # Timer for delayed camera release
        
        # CAMERA LIFECYCLE FIX: Stop signal for clean cross-thread shutdown
        # When stop_camera() is called from the API, this event signals ALL
        # active generators (stream, annotated stream, detection processor) to exit.
        self._stopped = threading.Event()
        
        # Open camera
        if isinstance(source, int):
            self.cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera source: {source_key}")
            return
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 15)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        logger.info(f"SharedCameraSource opened: {source_key}")
    
    def start(self):
        """Start the capture thread"""
        if self.is_running or self.cap is None or not self.cap.isOpened():
            return
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info(f"Capture thread started for: {self.source_key}")
    
    def stop(self):
        """Stop the capture thread"""
        self.is_running = False
        self._stopped.set()  # Signal all consumers to stop
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        logger.info(f"Capture thread stopped for: {self.source_key}")
    
    def is_stopped(self) -> bool:
        """Check if this source has been signaled to stop"""
        return self._stopped.is_set()
    
    def _capture_loop(self):
        """Background thread that continuously captures frames"""
        while self.is_running and self.cap and self.cap.isOpened() and not self._stopped.is_set():
            ret, frame = self.cap.read()
            if ret:
                # Resize for consistent output
                frame = cv2.resize(frame, (640, 480))
                with self.frame_lock:
                    self.current_frame = frame
            else:
                logger.warning(f"Failed to read frame from {self.source_key}")
                time.sleep(0.1)
            
            # ~30 FPS capture rate
            time.sleep(0.033)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame (thread-safe). Returns None if source is stopped."""
        # CAMERA LIFECYCLE FIX: Return None when stopped to signal generators to exit
        if self._stopped.is_set():
            return None
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def add_consumer(self):
        """Register a new stream consumer"""
        with self.consumer_lock:
            # Cancel any pending release if a new consumer connects
            if self.release_timer:
                self.release_timer.cancel()
                self.release_timer = None
                logger.info(f"Cancelled pending release for {self.source_key}")
            
            self.consumer_count += 1
            if self.consumer_count == 1:
                self.start()
            logger.info(f"Consumer added to {self.source_key}. Total: {self.consumer_count}")
    
    def _schedule_delayed_stop(self):
        """Schedule camera stop after delay to allow for reconnections"""
        # Cancel any existing timer
        if self.release_timer:
            self.release_timer.cancel()
        
        # Schedule release after 3 seconds
        self.release_timer = threading.Timer(3.0, self._delayed_release)
        self.release_timer.daemon = True
        self.release_timer.start()
        logger.info(f"Scheduled delayed release for {self.source_key} in 3 seconds")
    
    def _delayed_release(self):
        """Execute delayed camera release if still no consumers"""
        with self.consumer_lock:
            if self.consumer_count == 0:
                logger.info(f"Executing delayed release for {self.source_key}")
                self.stop()
                if self.cap:
                    self.cap.release()
                    self.cap = None
                    logger.info(f"Camera {self.source_key} fully released")
            else:
                logger.info(f"Skipping release for {self.source_key} - consumers reconnected")
    
    def remove_consumer(self):
        """Unregister a stream consumer"""
        with self.consumer_lock:
            self.consumer_count = max(0, self.consumer_count - 1)
            logger.info(f"Consumer removed from {self.source_key}. Total: {self.consumer_count}")
            # Schedule delayed stop to allow for reconnections
            if self.consumer_count == 0:
                self._schedule_delayed_stop()
    
    def release(self):
        """Release camera resources"""
        # Cancel any pending release timer
        if self.release_timer:
            self.release_timer.cancel()
            self.release_timer = None
        
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info(f"Camera {self.source_key} hardware fully released (LED should turn off)")
    
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened() and not self._stopped.is_set()


class SharedCameraManager:
    """
    Singleton manager for all camera sources.
    Ensures each physical camera is opened only once.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sources: Dict[str, SharedCameraSource] = {}
        self._sources_lock = threading.Lock()
        self._initialized = True
        logger.info("SharedCameraManager initialized")
    
    def _get_source_key(self, source) -> str:
        """Generate a unique key for the source"""
        if isinstance(source, int):
            return f"webcam_{source}"
        return str(source)
    
    def get_source(self, source) -> SharedCameraSource:
        """Get or create a shared camera source"""
        source_key = self._get_source_key(source)
        
        with self._sources_lock:
            if source_key not in self._sources:
                self._sources[source_key] = SharedCameraSource(source, source_key)
            
            return self._sources[source_key]
    
    def get_frame(self, source) -> Optional[np.ndarray]:
        """Get the latest frame from a source"""
        camera_source = self.get_source(source)
        return camera_source.get_frame()
    
    def register_stream(self, source) -> SharedCameraSource:
        """Register a new stream consumer for a source"""
        camera_source = self.get_source(source)
        camera_source.add_consumer()
        return camera_source
    
    def unregister_stream(self, source):
        """Unregister a stream consumer"""
        source_key = self._get_source_key(source)
        with self._sources_lock:
            if source_key in self._sources:
                self._sources[source_key].remove_consumer()
    
    def release_source(self, source):
        """Release a camera source completely"""
        source_key = self._get_source_key(source)
        with self._sources_lock:
            if source_key in self._sources:
                self._sources[source_key].release()
                del self._sources[source_key]
    
    def force_release_source(self, source):
        """
        CAMERA LIFECYCLE FIX: Force-release a camera source immediately.
        
        This is called when the user explicitly stops a camera.
        It signals all active stream consumers to exit (via the _stopped event),
        cancels any delayed release timers, resets consumer count,
        and immediately releases the camera hardware.
        
        This fixes the bug where webcam LED stays on after stopping the camera.
        """
        source_key = self._get_source_key(source)
        with self._sources_lock:
            if source_key in self._sources:
                camera_source = self._sources[source_key]
                logger.info(f"Force-releasing camera source: {source_key} "
                          f"(had {camera_source.consumer_count} consumers)")
                
                # Signal stop to all consumers (they check is_stopped() in their loops)
                camera_source._stopped.set()
                
                # Reset consumer count so delayed release doesn't get confused
                with camera_source.consumer_lock:
                    camera_source.consumer_count = 0
                
                # Release hardware immediately
                camera_source.release()
                
                # Remove from sources dict so next start creates fresh instance
                del self._sources[source_key]
                
                logger.info(f"Camera {source_key} force-released successfully")
            else:
                logger.debug(f"Camera source {source_key} not found (already released)")
    
    def release_all(self):
        """Release all camera sources"""
        with self._sources_lock:
            for source in list(self._sources.values()):
                source.release()
            self._sources.clear()
        logger.info("All camera sources released")
    
    def get_active_sources(self) -> list:
        """Get list of active source keys"""
        with self._sources_lock:
            return list(self._sources.keys())


# Global singleton instance
shared_camera_manager = SharedCameraManager()
