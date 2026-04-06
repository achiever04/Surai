# Export all endpoint modules
from . import (
    auth,
    cameras,
    camera_stream_annotated,
    detections,
    watchlist,
    evidence,
    blockchain,
    analytics,
    federated_learning
)

__all__ = [
    'auth',
    'cameras',
    'camera_stream_annotated',
    'detections',
    'watchlist',
    'evidence',
    'blockchain',
    'analytics',
    'federated_learning'
]
