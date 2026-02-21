from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Generator, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.domain.models.user import User
from app.infrastructure.database.session import get_db_session
from app.infrastructure.container import ServiceContainer


# Dependency to get the current user
CurrentUser = Depends(get_current_user)

# Dependency to get the database session
DBSession = Depends(get_db_session)

# Security scheme
security = HTTPBearer()

# Service container singleton
_service_container: ServiceContainer = None


async def get_service_container(db: AsyncSession = Depends(get_db_session)) -> ServiceContainer:
    """
    Get or create the service container.
    
    Creates a new container instance per request to avoid session conflicts.
    Each request gets its own container with its own database session.
    """
    # Create a new container for each request to ensure session isolation
    return ServiceContainer(db=db)


def get_current_active_user(current_user: User = CurrentUser) -> User:
    """Get the current active user, raising an exception if inactive."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user
