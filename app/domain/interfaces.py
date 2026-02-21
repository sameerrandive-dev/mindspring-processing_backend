"""
Abstract interfaces for services, repositories, and infrastructure providers.

This module defines the contracts that services, repositories, and infrastructure
implementations must follow. This enables:
- Dependency injection without coupling
- Testability via mock implementations
- Interchangeability of implementations
- Clear architectural boundaries
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TypeVar, Generic
from datetime import datetime
from enum import Enum

T = TypeVar("T")
TEntity = TypeVar("TEntity")


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class IRepository(ABC, Generic[TEntity]):
    """
    Base repository interface for data access operations.
    
    All repositories must implement these common operations:
    - Create entities
    - Retrieve by ID or filters
    - Update entities
    - Delete entities
    - Query with pagination
    """
    
    @abstractmethod
    async def create(self, entity: TEntity) -> TEntity:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> Optional[TEntity]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: Any, **updates) -> TEntity:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: Any) -> bool:
        """Delete entity by ID. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[TEntity]:
        """List all entities with pagination."""
        pass


# ============================================================================
# SERVICE INTERFACES  
# ============================================================================

class IService(ABC):
    """
    Base service interface for business logic.
    
    Services contain domain logic and orchestrate repositories and infrastructure.
    Services are decoupled from HTTP/FastAPI.
    """
    pass


# ============================================================================
# INFRASTRUCTURE PROVIDER INTERFACES
# ============================================================================

class IStorageProvider(ABC):
    """Storage provider for files (S3, local filesystem, etc.)."""
    
    @abstractmethod
    async def store(self, key: str, content: bytes, metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Store file content.
        
        Args:
            key: Storage key/path
            content: File bytes
            metadata: Optional file metadata
            
        Returns:
            Storage URL or key for later retrieval
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> bytes:
        """Retrieve file content by key."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file by key. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    async def get_signed_url(self, key: str, expires_in: int = 600) -> str:
        """
        Get a pre-signed URL for direct file access (for private buckets).
        
        Args:
            key: Storage key/path
            expires_in: URL expiration time in seconds (default: 600 = 10 minutes)
            
        Returns:
            Pre-signed URL that can be used to access the file directly
        """
        pass


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IQueueProvider(ABC):
    """Background job queue provider."""
    
    @abstractmethod
    async def enqueue(
        self,
        job_type: str,
        job_id: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """
        Enqueue a job for async processing.
        
        Args:
            job_type: Type of job (e.g., 'pdf_processing', 'embedding_generation')
            job_id: Unique job identifier
            payload: Job data/parameters
            priority: Priority level (higher = more important)
            
        Returns:
            Queue job ID
        """
        pass
    
    @abstractmethod
    async def get_job_status(self, queue_job_id: str) -> JobStatus:
        """Get current status of queued job."""
        pass
    
    @abstractmethod
    async def get_job_result(self, queue_job_id: str) -> Optional[Dict[str, Any]]:
        """Get result of completed job."""
        pass
    
    @abstractmethod
    async def dequeue(self, job_type: str) -> Optional[Dict[str, Any]]:
        """Dequeue a job for processing (used by workers)."""
        pass
    
    @abstractmethod
    async def mark_complete(self, queue_job_id: str, result: Dict[str, Any]) -> None:
        """Mark job as completed with result."""
        pass
    
    @abstractmethod
    async def mark_failed(self, queue_job_id: str, error: str) -> None:
        """Mark job as failed with error message."""
        pass


class ICacheProvider(ABC):
    """In-memory or distributed cache provider."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear entire cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Health check for cache provider."""
        pass


class IEmailProvider(ABC):
    """Email provider for sending emails."""
    
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send email.
        
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def send_otp(
        self,
        to: str,
        code: str,
        action: str = "verify",
    ) -> bool:
        """Send OTP email."""
        pass


class ILLMClient(ABC):
    """Large Language Model client for AI interactions."""
    
    @abstractmethod
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate chat response from LLM."""
        pass
    
    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass
    
    @abstractmethod
    async def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions from content."""
        pass
    
    @abstractmethod
    async def generate_summary(
        self,
        content: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """
        Generate summary from content.
        
        Args:
            content: Text content to summarize
            max_length: Maximum length of summary in characters
            style: Summary style ('concise', 'detailed', 'bullet_points')
            
        Returns:
            Generated summary text
        """
        pass
    
    @abstractmethod
    async def generate_study_guide(
        self,
        content: str,
        topic: Optional[str] = None,
        format: str = "structured",
    ) -> str:
        """
        Generate study guide from content.
        
        Args:
            content: Text content to create guide from
            topic: Optional topic/title for the guide
            format: Guide format ('structured', 'outline', 'detailed')
            
        Returns:
            Generated study guide text
        """
        pass
    
    @abstractmethod
    async def generate_mindmap(
        self,
        content: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate mindmap structure from content.
        
        Args:
            content: Text content to create mindmap from
            format: Output format ('json', 'markdown', 'mermaid')
            
        Returns:
            Mindmap structure as dict (or string for markdown/mermaid)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Health check for LLM provider."""
        pass


class IPdfProcessor(ABC):
    """PDF processing provider for text extraction and parsing."""
    
    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """Extract text from PDF."""
        pass
    
    @abstractmethod
    async def extract_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract pages with page numbers and content.
        
        Returns:
            List of dicts with 'page_number', 'text', 'metadata'
        """
        pass


# ============================================================================
# UNIT OF WORK / TRANSACTION INTERFACE
# ============================================================================

class ITransaction(ABC):
    """
    Transaction/Unit of Work interface for managing multi-step operations.
    
    Enables repositories to participate in transactions:
    - Multiple repository operations in one atomic transaction
    - Commit or rollback all changes together
    """
    
    @abstractmethod
    async def commit(self) -> None:
        """Commit transaction."""
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        """Rollback transaction."""
        pass
    
    @abstractmethod
    async def __aenter__(self):
        """Async context manager entry."""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
