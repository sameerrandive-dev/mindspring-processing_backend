import time
import logging
from typing import Optional, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.config import settings
from app.infrastructure.redis.redis_cache import RedisCacheProvider

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based rate limiting middleware.
    Limits requests based on user_id (if authenticated) or IP address.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = RedisCacheProvider()
        # Parse default rate limit e.g. "100/hour"
        self.default_limit, self.default_period = self._parse_rate_limit(settings.RATE_LIMIT_DEFAULT)

    def _parse_rate_limit(self, limit_str: str) -> Tuple[int, int]:
        """Parse rate limit string like '100/hour' or '10/minute'."""
        try:
            count, period_name = limit_str.split("/")
            count = int(count)
            periods = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400
            }
            return count, periods.get(period_name.lower(), 3600)
        except Exception:
            logger.error(f"Failed to parse rate limit string: {limit_str}. Using default 100/hour.")
            return 100, 3600

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and OpenAPI docs
        if request.url.path in ["/health", "/readiness", "/live", "/api/v1/openapi.json", "/docs", "/redoc"]:
            return await call_next(request)

        # Identify user or client
        identifier = await self._get_identifier(request)
        key = f"rate_limit:{identifier}:{request.url.path}"
        
        # Check rate limit
        limit = self.default_limit
        period = self.default_period
        
        # Special case for document upload if it were a specific path
        if "/documents/upload" in request.url.path:
            limit, period = self._parse_rate_limit(settings.RATE_LIMIT_DOCUMENT_UPLOAD)

        is_allowed, remaining, reset_time = await self._check_rate_limit(key, limit, period)
        
        if not is_allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "details": {"retry_after": int(reset_time - time.time())}
                    }
                },
                headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining), "X-RateLimit-Reset": str(int(reset_time))}
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        return response

    async def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for the request (user_id or IP)."""
        # Try to get user from request state (set by Auth middleware if it ran before)
        # However, BaseHTTPMiddleware runs before dependencies are resolved.
        # We might need to check the token manually if we want per-user limiting here,
        # or use IP as fallback.
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    async def _check_rate_limit(self, key: str, limit: int, period: int) -> Tuple[bool, int, float]:
        """
        Check if request is allowed.
        Returns (is_allowed, remaining, reset_time)
        """
        try:
            client = await self.redis._get_client()
            current_time = time.time()
            
            # Use Lua script for atomic check
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local period = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            
            local current = redis.call('get', key)
            if not current then
                redis.call('setex', key, period, 1)
                return {1, limit - 1, current_time + period}
            end
            
            if tonumber(current) >= limit then
                local ttl = redis.call('ttl', key)
                return {0, 0, current_time + ttl}
            end
            
            local new_val = redis.call('incr', key)
            local ttl = redis.call('ttl', key)
            return {1, limit - new_val, current_time + ttl}
            """
            
            result = await client.eval(lua_script, 1, key, limit, period, current_time)
            return bool(result[0]), int(result[1]), float(result[2])
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On redis failure, allow request but log error
            return True, 1, time.time() + period
