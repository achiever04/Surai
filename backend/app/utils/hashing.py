"""
Hashing utilities for data integrity
"""
import hashlib
import json
from typing import Any, Dict

def compute_sha256(data: bytes) -> str:
    """
    Compute SHA-256 hash of data
    
    Args:
        data: Data as bytes
        
    Returns:
        Hex-encoded hash string
    """
    return hashlib.sha256(data).hexdigest()

def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA-256 hash of file
    
    Args:
        file_path: Path to file
        
    Returns:
        Hex-encoded hash string
    """
    sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    
    return sha256.hexdigest()

def compute_dict_hash(data: Dict[str, Any]) -> str:
    """
    Compute hash of dictionary (sorted keys for consistency)
    
    Args:
        data: Dictionary to hash
        
    Returns:
        Hex-encoded hash string
    """
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()

def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verify data matches expected hash
    
    Args:
        data: Data to verify
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches
    """
    actual_hash = compute_sha256(data)
    return actual_hash == expected_hash

def verify_file_hash(file_path: str, expected_hash: str) -> bool:
    """
    Verify file matches expected hash
    
    Args:
        file_path: Path to file
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches
    """
    actual_hash = compute_file_hash(file_path)
    return actual_hash == expected_hash