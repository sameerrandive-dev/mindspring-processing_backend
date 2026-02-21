"""Test fixtures and factories for service tests."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models.user import User
from app.domain.models.notebook import Notebook
from app.domain.models.document import Document
from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.domain.models.quiz import Quiz
from app.domain.models.generation_history import GenerationHistory
from app.domain.models.job import Job
from app.domain.models.source import Source
from app.domain.models.chunk import Chunk
from app.infrastructure.storage.mock_storage import MockStorageProvider
from app.infrastructure.queues.mock_queue import MockQueueProvider
from app.infrastructure.redis.mock_cache import MockCacheProvider
from app.infrastructure.email.mock_email import MockEmailProvider
from app.infrastructure.llm_client import MockLLMClient


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
async def async_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create all tables
    async with engine.begin() as conn:
        from app.domain.models import Base
        await conn.run_sync(Base.metadata.create_all)
    
    # Create sessionmaker
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_storage():
    """Create a mock storage provider."""
    return MockStorageProvider()


@pytest.fixture
def mock_queue():
    """Create a mock queue provider."""
    return MockQueueProvider()


@pytest.fixture
def mock_cache():
    """Create a mock cache provider."""
    return MockCacheProvider()


@pytest.fixture
def mock_email():
    """Create a mock email provider."""
    return MockEmailProvider()


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    return MockLLMClient()


# ============================================================================
# DATA FACTORIES
# ============================================================================

class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        email: str = "test@example.com",
        hashed_password: str = "hashed_password",
        is_verified: bool = True,
        is_active: bool = True,
    ) -> User:
        """Create a test user."""
        user = User(
            email=email,
            hashed_password=hashed_password,
            is_verified=is_verified,
            is_active=is_active,
        )
        db.add(user)
        await db.flush()
        return user


class NotebookFactory:
    """Factory for creating test notebooks."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        owner_id: int,
        title: str = "Test Notebook",
        language: str = "en",
    ) -> Notebook:
        """Create a test notebook."""
        notebook = Notebook(
            owner_id=owner_id,
            title=title,
            language=language,
        )
        db.add(notebook)
        await db.flush()
        return notebook


class DocumentFactory:
    """Factory for creating test documents."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        file_name: str = "test.pdf",
        file_hash: str = "abc123",
    ) -> Document:
        """Create a test document."""
        document = Document(
            user_id=user_id,
            file_name=file_name,
            file_size=1000,
            file_hash=file_hash,
            storage_key=f"documents/{user_id}/{file_hash}",
            status="ready",
        )
        db.add(document)
        await db.flush()
        return document


class ConversationFactory:
    """Factory for creating test conversations."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        notebook_id: int,
        user_id: int,
        title: str = "Test Conversation",
    ) -> Conversation:
        """Create a test conversation."""
        conversation = Conversation(
            notebook_id=notebook_id,
            user_id=user_id,
            title=title,
        )
        db.add(conversation)
        await db.flush()
        return conversation


class MessageFactory:
    """Factory for creating test messages."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        conversation_id: int,
        role: str = "user",
        content: str = "Test message",
    ) -> Message:
        """Create a test message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        db.add(message)
        await db.flush()
        return message


class QuizFactory:
    """Factory for creating test quizzes."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        notebook_id: int,
        user_id: int,
        topic: str = "Test Topic",
    ) -> Quiz:
        """Create a test quiz."""
        questions = [
            {"question": "Q1?", "options": ["A", "B"], "correct": "A"},
        ]
        quiz = Quiz(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            questions_json=questions,
        )
        db.add(quiz)
        await db.flush()
        return quiz


class JobFactory:
    """Factory for creating test jobs."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        document_id: int,
        user_id: int,
        job_type: str = "document_processing",
        status: str = "PENDING",
    ) -> Job:
        """Create a test job."""
        job = Job(
            document_id=document_id,
            user_id=user_id,
            job_type=job_type,
            status=status,
        )
        db.add(job)
        await db.flush()
        return job


# ============================================================================
# COMPOSITE FIXTURES (Multiple entities at once)
# ============================================================================

@pytest.fixture
async def user_with_notebook(async_db: AsyncSession):
    """Create a user with a notebook."""
    user = await UserFactory.create(async_db)
    notebook = await NotebookFactory.create(async_db, owner_id=user.id)
    return user, notebook


@pytest.fixture
async def user_with_conversation(async_db: AsyncSession):
    """Create a user with a notebook and conversation."""
    user = await UserFactory.create(async_db)
    notebook = await NotebookFactory.create(async_db, owner_id=user.id)
    conversation = await ConversationFactory.create(
        async_db,
        notebook_id=notebook.id,
        user_id=user.id,
    )
    return user, notebook, conversation
