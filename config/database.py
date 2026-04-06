"""
Database configuration and utilities
"""
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from typing import Optional
from loguru import logger

from config.settings import settings


def get_engine(
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True
) -> AsyncEngine:
    """
    Create async database engine
    
    Args:
        echo: Log all SQL statements
        pool_size: Connection pool size
        max_overflow: Max connections above pool_size
        pool_pre_ping: Verify connections before using
        
    Returns:
        AsyncEngine instance
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=echo,
        future=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        poolclass=QueuePool
    )
    
    logger.info(f"Database engine created: {settings.POSTGRES_DB}")
    return engine


def get_test_engine() -> AsyncEngine:
    """Create engine for testing (uses NullPool)"""
    test_url = settings.DATABASE_URL.replace(
        settings.POSTGRES_DB,
        f"{settings.POSTGRES_DB}_test"
    )
    
    return create_async_engine(
        test_url,
        echo=False,
        poolclass=NullPool
    )


async def check_db_connection(engine: AsyncEngine) -> bool:
    """
    Check if database connection is working
    
    Args:
        engine: Database engine
        
    Returns:
        True if connection successful
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# Database connection string utilities
def mask_db_url(url: str) -> str:
    """Mask password in database URL for logging"""
    try:
        if '@' in url:
            parts = url.split('@')
            credentials = parts[0].split('://')
            if len(credentials) == 2:
                protocol = credentials[0]
                user_pass = credentials[1].split(':')
                if len(user_pass) == 2:
                    return f"{protocol}://{user_pass[0]}:***@{parts[1]}"
        return url
    except:
        return "***"