from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.infrastructure.database.session import init_db
from app.infrastructure.monitoring.logging_setup import setup_logging


from fastapi.exceptions import RequestValidationError
from app.api.exception_handlers import (
    domain_error_handler,
    validation_error_handler,
    generic_error_handler,
)
from app.api.middleware.timeout import TimeoutMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.infrastructure.monitoring.logging_setup import LoggingMiddleware
from app.domain.errors.exceptions import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    await init_db()
    
    yield
    
    # Shutdown
    # Cleanup operations can be added here


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MindSpring API",
        version=settings.VERSION,
        description="Enterprise-grade AI-powered learning and research platform backend.",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Exception Handlers
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    # Middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TimeoutMiddleware)
    
    # CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Root health endpoints (required by some load balancers/orchestrators)
    @app.get("/health", tags=["system"])
    async def health_check():
        """Liveness check."""
        return {"status": "healthy", "service": "mindspring-fastapi-backend"}

    @app.get("/readiness", tags=["system"])
    async def readiness_check():
        """Readiness check."""
        # Add actual dependency checks here if needed
        return {"status": "ready", "service": "mindspring-fastapi-backend"}
    
    # Include API routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )