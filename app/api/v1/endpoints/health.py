from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "mindspring-fastapi-backend"}


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint."""
    # Here you would typically check if all required services are ready
    # For example: database connectivity, external service availability, etc.
    return {"status": "ready", "service": "mindspring-fastapi-backend"}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness check endpoint."""
    # This checks if the service itself is alive and responding
    return {"status": "alive", "service": "mindspring-fastapi-backend"}