"""
ONNX Runtime Graph Optimization Caching

Patches ONNX Runtime InferenceSession to cache optimized model graphs.
On first load, ONNX optimizes the computation graph (graph fusion, constant
folding, etc.) — this takes most of InsightFace's 70s load time.

With this cache, subsequent loads read the pre-optimized graph directly,
cutting InsightFace load from ~70s to ~10-15s.

Usage: import this module BEFORE any onnxruntime usage.
"""
import os
import hashlib
from loguru import logger

# Cache directory for optimized ONNX models
ONNX_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.onnx_cache')
os.makedirs(ONNX_CACHE_DIR, exist_ok=True)

_original_init = None
_patched = False


def _get_cache_path(model_path: str) -> str:
    """Generate a cache path for an optimized ONNX model."""
    if not model_path or not os.path.exists(model_path):
        return ""
    
    # Use file hash + size for cache key (detects model changes)
    file_size = os.path.getsize(model_path)
    basename = os.path.basename(model_path)
    cache_key = f"{basename}_{file_size}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
    return os.path.join(ONNX_CACHE_DIR, f"{basename}.{cache_hash}.optimized")


def _patched_inference_session_init(self, path_or_bytes, sess_options=None, providers=None, **kwargs):
    """Patched InferenceSession.__init__ with graph optimization caching."""
    import onnxruntime as ort
    
    # Only cache file-based models (not byte-loaded)
    if isinstance(path_or_bytes, str) and os.path.exists(path_or_bytes):
        cache_path = _get_cache_path(path_or_bytes)
        
        if cache_path:
            if sess_options is None:
                sess_options = ort.SessionOptions()
            
            # Enable graph optimization
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Thread tuning: limit per-session threads to reduce contention
            # when multiple ONNX models load in parallel (InsightFace loads 5)
            sess_options.intra_op_num_threads = 2
            sess_options.inter_op_num_threads = 1
            
            # Enable parallel execution for faster inference
            sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            
            # Set optimized model output path — ONNX reads this on next load
            if os.path.exists(cache_path):
                # Load from cached optimized model instead
                logger.debug(f"ONNX cache hit: {os.path.basename(path_or_bytes)}")
                path_or_bytes = cache_path
            else:
                # Save optimized model to cache for next startup
                sess_options.optimized_model_filepath = cache_path
                logger.debug(f"ONNX cache miss: {os.path.basename(path_or_bytes)} → caching")
    
    # Call original constructor
    _original_init(self, path_or_bytes, sess_options=sess_options, providers=providers, **kwargs)


def patch_onnx_runtime():
    """Apply ONNX optimization caching patch. Safe to call multiple times."""
    global _original_init, _patched
    
    if _patched:
        return
    
    try:
        import onnxruntime as ort
        _original_init = ort.InferenceSession.__init__
        ort.InferenceSession.__init__ = _patched_inference_session_init
        _patched = True
        logger.info(f"✅ ONNX optimization caching enabled (cache: {ONNX_CACHE_DIR})")
    except ImportError:
        logger.debug("onnxruntime not available, skipping ONNX cache patch")
    except Exception as e:
        logger.warning(f"Failed to patch ONNX Runtime: {e}")


# Auto-patch on import
patch_onnx_runtime()
