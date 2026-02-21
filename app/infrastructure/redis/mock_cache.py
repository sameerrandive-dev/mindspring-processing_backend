"""In-memory mock cache provider for testing."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.domain.interfaces import ICacheProvider


class MockCacheProvider(ICacheProvider):
    """In-memory cache for testing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, Optional[datetime]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        # Check expiration
        expiry = self._expiry.get(key)
        if expiry and datetime.utcnow() > expiry:
            del self._cache[key]
            del self._expiry[key]
            return None
        
        return self._cache[key]
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache."""
        self._cache[key] = value
        if ttl_seconds:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        else:
            self._expiry[key] = None
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._expiry.clear()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if key not in self._cache:
            return False
        
        # Check expiration
        expiry = self._expiry.get(key)
        if expiry and datetime.utcnow() > expiry:
            await self.delete(key)
            return False
        
        return True
    
    async def health_check(self) -> bool:
        """Health check always returns True for mock."""
        return True
