import time
from functools import wraps
from loguru import logger
import statistics
from collections import defaultdict

class FPSProfiler:
    """Latency and FPS profiler across pipeline bottlenecks."""
    def __init__(self):
        self._fps_timers = defaultdict(list)
        self._max_samples = 100
        self._start_points = {}

    def start_track(self, name: str):
        self._start_points[name] = time.perf_counter()

    def end_track(self, name: str):
        if name in self._start_points:
            elapsed = time.perf_counter() - self._start_points[name]
            self._fps_timers[name].append(elapsed)
            if len(self._fps_timers[name]) > self._max_samples:
                self._fps_timers[name].pop(0)

    def log_stats(self):
        """Invoke every N frames to get throughput"""
        for name, times in self._fps_timers.items():
            if times:
                avg_time = statistics.mean(times)
                fps = 1.0 / avg_time if avg_time > 0 else 0
                logger.info(f"PROFILER [{name}]: Avg Latency = {avg_time*1000:.2f}ms | Est. FPS = {fps:.1f}")

profiler = FPSProfiler()

def profile_latency(name: str):
    """Decorator for profiling synchronous functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            profiler._fps_timers[name].append(elapsed)
            if len(profiler._fps_timers[name]) > profiler._max_samples:
                profiler._fps_timers[name].pop(0)
            return result
        return wrapper
    return decorator
