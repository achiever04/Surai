"""
Redis configuration and client setup
"""
import redis.asyncio as aioredis
from redis.asyncio import Redis
from typing import Optional
from loguru import logger

from config.settings import settings


class RedisConfig:
    """Redis configuration manager"""
    
    _client: Optional[Redis] = None
    
    @classmethod
    async def get_client(cls) -> Redis:
        """
        Get Redis client (singleton)
        
        Returns:
            Redis async client
        """
        if cls._client is None:
            cls._client = await cls.create_client()
        
        return cls._client
    
    @classmethod
    async def create_client(cls) -> Redis:
        """
        Create new Redis client
        
        Returns:
            Redis async client
        """
        try:
            client = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            
            # Test connection
            await client.ping()
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
            return client
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("Redis connection closed")


class RedisKeys:
    """Redis key patterns"""
    
    # Cache keys
    WATCHLIST_EMBEDDINGS = "watchlist:embeddings"
    WATCHLIST_PERSON = "watchlist:person:{person_id}"
    CAMERA_STATUS = "camera:status:{camera_id}"
    DETECTION_CACHE = "detection:cache:{event_id}"
    
    # Session keys
    USER_SESSION = "session:user:{user_id}"
    
    # Queue keys
    DETECTION_QUEUE = "queue:detections"
    ALERT_QUEUE = "queue:alerts"
    
    # Lock keys
    CAMERA_LOCK = "lock:camera:{camera_id}"
    FL_TRAINING_LOCK = "lock:fl:training"
    
    # Statistics keys
    STATS_DAILY_DETECTIONS = "stats:detections:daily:{date}"
    STATS_CAMERA_FPS = "stats:camera:{camera_id}:fps"
    
    @staticmethod
    def format_key(pattern: str, **kwargs) -> str:
        """Format key pattern with values"""
        return pattern.format(**kwargs)


# Cache utilities
class CacheManager:
    """Helper for caching operations"""
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def set_with_expiry(
        self,
        key: str,
        value: str,
        expiry_seconds: int = 3600
    ):
        """Set value with expiration"""
        await self.redis.setex(key, expiry_seconds, value)
    
    async def get_or_none(self, key: str) -> Optional[str]:
        """Get value or return None if not exists"""
        return await self.redis.get(key)
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=pattern, count=100
            )
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break
    
    async def increment_counter(
        self,
        key: str,
        expiry_seconds: Optional[int] = None
    ) -> int:
        """Increment counter and optionally set expiry"""
        count = await self.redis.incr(key)
        
        if expiry_seconds and count == 1:
            await self.redis.expire(key, expiry_seconds)
        
        return count