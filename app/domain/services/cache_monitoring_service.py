"""Cache monitoring service for Redis health and metrics."""

import logging
from typing import Optional, Dict, Any

from app.domain.interfaces import ICacheProvider

logger = logging.getLogger(__name__)


class CacheMonitoringService:
    """
    Cache monitoring service for health checks and observability.
    
    Responsibilities:
    - Cache health monitoring
    - Metrics collection
    - Eviction policies
    - Performance tracking
    """
    
    def __init__(self, cache_provider: ICacheProvider):
        self.cache_provider = cache_provider
    
    async def health_check(self) -> bool:
        """Check if cache provider is healthy."""
        try:
            healthy = await self.cache_provider.health_check()
            if healthy:
                logger.info("Cache health check passed")
            else:
                logger.warning("Cache health check failed")
            return healthy
        except Exception as e:
            logger.error(f"Cache health check exception: {e}")
            return False
    
    async def clear_expired_entries(self) -> None:
        """Clear expired cache entries (if supported by provider)."""
        # This is a no-op for Redis since it auto-expires keys
        # But for in-memory caches, we could implement cleanup
        logger.info("Cache cleanup initiated")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and metrics."""
        healthy = await self.health_check()
        
        return {
            "cache_healthy": healthy,
            "cache_type": self.cache_provider.__class__.__name__,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
    
    async def set_cache_metric(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store a cache metric."""
        metric_key = f"metrics:{key}"
        await self.cache_provider.set(metric_key, value, ttl_seconds)
    
    async def get_cache_metric(self, key: str) -> Optional[Any]:
        """Retrieve a cached metric."""
        metric_key = f"metrics:{key}"
        return await self.cache_provider.get(metric_key)
