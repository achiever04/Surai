import time
import statistics
from functools import wraps
from collections import defaultdict
from loguru import logger

class FPSProfiler:
    """Latency and FPS profiler across your async pipeline bottlenecks."""
    def __init__(self):
        self._fps_timers = defaultdict(list)
        self._max_samples = 100
        self._start_points = {}

    def log_stats(self):
        """Invoke every N frames from stream_processor to output dashboard throughput"""
        for name, times in self._fps_timers.items():
            if times:
                avg_time = statistics.mean(times)
                fps = 1.0 / avg_time if avg_time > 0 else 0
                logger.info(f"PROFILER [{name}]: Latency = {avg_time*1000:.2f}ms | Est. FPS = {fps:.1f}")

profiler = FPSProfiler()

def profile_latency(name: str):
    """Decorator to instantly measure the cost of any function without cluttering code"""
    def decorator(func):
        # Handle async functions gracefully
        import asyncio
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                
                profiler._fps_timers[name].append(elapsed)
                if len(profiler._fps_timers[name]) > profiler._max_samples:
                    profiler._fps_timers[name].pop(0)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                
                profiler._fps_timers[name].append(elapsed)
                if len(profiler._fps_timers[name]) > profiler._max_samples:
                    profiler._fps_timers[name].pop(0)
                return result
            return sync_wrapper
    return decorator
