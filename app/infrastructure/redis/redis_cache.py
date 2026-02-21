"""Redis cache provider implementation."""

import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.domain.interfaces import ICacheProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCacheProvider(ICacheProvider):
    """Redis cache provider using async Redis client."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache provider.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.REDIS_URL
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None
        self._pool: Optional[aioredis.ConnectionPool] = None
    
    async def _get_client(self) -> aioredis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            try:
                # Create connection pool for better performance
                self._pool = aioredis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=settings.REDIS_POOL_SIZE,
                    decode_responses=False,  # We'll handle encoding/decoding ourselves
                )
                self._client = aioredis.Redis(connection_pool=self._pool)
                # Test connection
                await self._client.ping()
                logger.info(f"Redis cache provider initialized: {self.redis_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                raise
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value is None:
                return None
            
            # Deserialize JSON
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to deserialize cache value for key {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        try:
            client = await self._get_client()
            # Serialize to JSON
            serialized = json.dumps(value).encode('utf-8')
            
            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized)
            else:
                await client.set(key, serialized)
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            # Don't raise - cache failures shouldn't break the application
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache. Returns True if deleted, False if not found."""
        try:
            client = await self._get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def clear(self) -> None:
        """Clear entire cache."""
        try:
            client = await self._get_client()
            await client.flushdb()
            logger.warning("Redis cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            client = await self._get_client()
            result = await client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache key existence {key}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Health check for cache provider."""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._client = None
        self._pool = None
        logger.info("Redis cache provider closed")
