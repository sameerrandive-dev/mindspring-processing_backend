from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings


# Base class for all models
class Base(DeclarativeBase):
    pass


# Create the async engine with connection pooling
def get_async_db_url(url: str) -> str:
    """Ensure the database URL uses the asyncpg driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

db_url = get_async_db_url(str(settings.DATABASE_URL))
# Strip query parameters for asyncpg if they cause issues
if "?" in db_url:
    db_url = db_url.split("?")[0]

print(f"DEBUG: Using DATABASE_URL (stripped): {db_url}")

engine = create_async_engine(
    db_url,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_POOL_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,  # Connection acquisition timeout
    pool_pre_ping=True,  # Verify connections are alive before using
    pool_recycle=300,
    connect_args={
        "ssl": True if "neon.tech" in db_url else False,
        "statement_cache_size": 0,  # Disable server-side prepared statement cache
        "command_timeout": 30,  # Command timeout in seconds
    }
)


# Create async session maker
AsyncSessionFactory = async_sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    print("DEBUG: Entering get_db_session")
    async with AsyncSessionFactory() as session:
        print("DEBUG: Got session from factory")
        try:
            yield session
            await session.commit()
            print("DEBUG: Transaction committed")
        except Exception as e:
            print(f"DEBUG: Exception in get_db_session: {e}")
            await session.rollback()
            print("DEBUG: Transaction rolled back")
            raise e
        finally:
            print("DEBUG: Closing session")
            await session.close()


# Alias for compatibility
get_db = get_db_session


async def init_db():
    """Initialize the database connection."""
    # Import all models here to ensure they are registered with Base.metadata
    # before calling create_all, while avoiding circular imports.
    from app.domain.models import (
        user, otp, refresh_token, notebook, source, 
        chunk, conversation, message, quiz, study_guide, 
        job, document, generation_history
    )
    
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)


# Context manager for database transactions
class DatabaseTransactionManager:
    """Manages database transactions with async context manager."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = AsyncSessionFactory()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()