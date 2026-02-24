import asyncio
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.config import settings

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce a global timeout on all requests."""
    
    def __init__(self, app, timeout: float = None):
        super().__init__(app)
        self.timeout = timeout or getattr(settings, "REQUEST_TIMEOUT_SECONDS", 30.0)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            # Use wait_for to enforce timeout
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {self.timeout}s: {request.url.path}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": f"Request processing timed out after {self.timeout} seconds.",
                        "details": None
                    }
                }
            )
        except Exception as e:
            # Re-raise other exceptions to be caught by the generic error handler
            raise e
