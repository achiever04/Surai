"""
Performance optimization utilities for CPU-only systems
"""
import torch
import cv2
import numpy as np
from typing import Optional, Tuple
import psutil
from loguru import logger  # ADD THIS

class CPUOptimizer:
    """Optimize inference for CPU-only execution"""
    
    _pytorch_configured = False  # Track if already configured
    
    @staticmethod
    def configure_pytorch():
        """Configure PyTorch for optimal CPU performance"""
        # Skip if already configured (idempotent)
        if CPUOptimizer._pytorch_configured:
            logger.debug("PyTorch already configured, skipping")
            return
            
        # Use all available cores but leave some for system
        num_cores = psutil.cpu_count(logical=False)
        torch.set_num_threads(max(1, num_cores - 1))
        torch.set_num_interop_threads(2)
        
        # Disable gradient computation for inference
        torch.set_grad_enabled(False)
        
        logger.info(f"PyTorch configured: {torch.get_num_threads()} threads")
        CPUOptimizer._pytorch_configured = True
    
    @staticmethod
    def quantize_model(model: torch.nn.Module) -> torch.nn.Module:
        """
        Apply dynamic quantization to reduce model size and improve speed
        INT8 quantization can provide 2-4x speedup on CPU
        """
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear, torch.nn.Conv2d},
            dtype=torch.qint8
        )
        logger.info("Model quantized to INT8")
        return quantized_model
    
    @staticmethod
    def optimize_image_size(
        image: np.ndarray,
        max_dimension: int = 640
    ) -> np.ndarray:
        """
        Resize image if too large to reduce processing time
        """
        h, w = image.shape[:2]
        
        if max(h, w) <= max_dimension:
            return image
        
        # Calculate new dimensions
        if h > w:
            new_h = max_dimension
            new_w = int(w * (max_dimension / h))
        else:
            new_w = max_dimension
            new_h = int(h * (max_dimension / w))
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized

class FrameSkipper:
    """Skip frames intelligently to reduce CPU load"""
    
    def __init__(self, process_every_n: int = 3):
        self.process_every_n = process_every_n
        self.frame_count = 0
        self.last_result = None
    
    def should_process(self) -> bool:
        """Determine if current frame should be processed"""
        self.frame_count += 1
        return (self.frame_count % self.process_every_n) == 0
    
    def update_result(self, result):
        """Store last processing result"""
        self.last_result = result
    
    def get_last_result(self):
        """Get cached result for skipped frames"""
        return self.last_result

class MotionDetector:
    """Detect motion to skip processing static scenes"""
    
    def __init__(self, threshold: float = 25.0):
        self.threshold = threshold
        self.previous_frame = None
    
    def has_motion(self, frame: np.ndarray) -> bool:
        """Check if frame has significant motion compared to previous"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.previous_frame is None:
            self.previous_frame = gray
            return True
        
        # Compute absolute difference
        frame_delta = cv2.absdiff(self.previous_frame, gray)
        mean_delta = np.mean(frame_delta)
        
        self.previous_frame = gray
        
        return mean_delta > self.threshold

class BatchProcessor:
    """Batch multiple operations to improve efficiency"""
    
    def __init__(self, batch_size: int = 4):
        self.batch_size = batch_size
        self.batch = []
    
    def add(self, item):
        """Add item to batch"""
        self.batch.append(item)
        
        if len(self.batch) >= self.batch_size:
            return self.process_batch()
        
        return None
    
    def process_batch(self):
        """Process accumulated batch"""
        if not self.batch:
            return None
        
        # Process batch here
        results = self.batch.copy()
        self.batch.clear()
        
        return results
    
    def flush(self):
        """Process remaining items"""
        return self.process_batch()

class MemoryManager:
    """Monitor and manage memory usage"""
    
    @staticmethod
    def get_memory_usage() -> float:
        """Get current memory usage percentage"""
        memory = psutil.virtual_memory()
        return memory.percent
    
    @staticmethod
    def should_reduce_load() -> bool:
        """Check if should reduce processing load due to memory"""
        return MemoryManager.get_memory_usage() > 85.0
    
    @staticmethod
    def log_memory_stats():
        """Log current memory statistics"""
        memory = psutil.virtual_memory()
        logger.info(
            f"Memory: {memory.percent}% "
            f"({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"
        )

# Initialize optimizer on module import
CPUOptimizer.configure_pytorch()