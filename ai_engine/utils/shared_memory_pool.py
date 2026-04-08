import numpy as np
from multiprocessing import shared_memory
import uuid
import logging

class SharedMemoryPool:
    """
    Manages zero-copy shared memory blocks across processes for passing
    camera frames into the AI perception engine dynamically without overhead.
    """
    def __init__(self):
        self.active_blocks = {}
        
    def allocate_frame(self, frame: np.ndarray, name: str = None) -> str:
        """
        Allocate a new shared memory block for a frame.
        Returns the unique name of the shared memory block.
        """
        if name is None:
            name = f"cam_frame_{uuid.uuid4().hex[:8]}"
            
        # Clean up if already exists
        if name in self.active_blocks:
            self.free_frame(name)
            
        try:
            shm = shared_memory.SharedMemory(create=True, size=frame.nbytes, name=name)
        except FileExistsError:
            # If randomly or previously leaked, connect and unlink it
            shm = shared_memory.SharedMemory(name=name)
            shm.unlink()
            shm = shared_memory.SharedMemory(create=True, size=frame.nbytes, name=name)
            
        # Create a numpy array backed by shared memory
        shared_array = np.ndarray(frame.shape, dtype=frame.dtype, buffer=shm.buf)
        np.copyto(shared_array, frame)
        
        self.active_blocks[name] = {
            'shm': shm,
            'shape': frame.shape,
            'dtype': frame.dtype
        }
        return name
        
    def get_frame(self, name: str, shape: tuple, dtype: type) -> np.ndarray:
        """
        Retrieve a frame from shared memory by name.
        """
        if name in self.active_blocks:
            shm = self.active_blocks[name]['shm']
            return np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            
        # Cross-process retrieval
        try:
            shm = shared_memory.SharedMemory(name=name)
            array = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            # We don't want to leak it, but the creator should unlink it.
            return array
        except FileNotFoundError:
            logging.error(f"Shared memory block '{name}' not found.")
            return None
        
    def free_frame(self, name: str):
        if name in self.active_blocks:
            shm = self.active_blocks[name]['shm']
            shm.close()
            try:
                shm.unlink()
            except FileNotFoundError:
                pass
            del self.active_blocks[name]
            
    def cleanup(self):
        for name in list(self.active_blocks.keys()):
            self.free_frame(name)

# Global pool singleton
shm_pool = SharedMemoryPool()
