"""
Helper utility functions
"""
from datetime import datetime, timedelta
from typing import Optional
import random
import string

def generate_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate random ID
    
    Args:
        prefix: Prefix for ID
        length: Length of random part
        
    Returns:
        Generated ID string
    """
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    if prefix:
        return f"{prefix}_{random_part}"
    
    return random_part

def format_timestamp(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string"""
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string
    
    Args:
        dt: Datetime to compare
        
    Returns:
        String like "2 hours ago"
    """
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"

def bytes_to_human_readable(size_bytes: int) -> str:
    """
    Convert bytes to human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string like "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"

def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string with suffix
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add
        
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    
    return s[:max_length - len(suffix)] + suffix
