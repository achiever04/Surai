"""
Structured logging configuration
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings

def setup_logging():
    """Configure application logging"""
    # Remove default handler
    logger.remove()
    
    # Console handler (colorized)
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO"
    )
    
    # File handler - General logs
    log_path = Path("logs/backend")
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_path / "app.log",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    # Error log file
    logger.add(
        log_path / "error.log",
        rotation="50 MB",
        retention="90 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR"
    )
    
    logger.info("Logging configured successfully")
    
    return logger