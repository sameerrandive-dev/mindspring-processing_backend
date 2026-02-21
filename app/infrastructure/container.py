"""Dependency injection container for service instantiation and composition."""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services import (
    AuthService,
    NotebookService,
    ChatService,
    DocumentService,
    JobService,
    HistoryService,
    PdfService,
    RAGIngestService,
    QuizService,
    CacheMonitoringService,
    ExternalProcessingService,
    TransactionExampleService,
    SourceGenerationService,
    SourceProcessingService,
)
from app.domain.repositories import (
    UserRepository,
    NotebookRepository,
    SourceRepository,
    ChunkRepository,
    DocumentRepository,
    JobRepository,
    ConversationRepository,
    MessageRepository,
    QuizRepository,
    HistoryRepository,
)
from app.domain.repositories.study_guide_repository import StudyGuideRepository
from app.domain.interfaces import (
    IStorageProvider,
    IQueueProvider,
    ICacheProvider,
    IEmailProvider,
    ILLMClient,
    IPdfProcessor,
)
from app.infrastructure.storage.mock_storage import MockStorageProvider
from app.infrastructure.storage.ceph_storage import CephStorageProvider
from app.infrastructure.queues.mock_queue import MockQueueProvider
from app.infrastructure.redis.mock_cache import MockCacheProvider
from app.infrastructure.redis.redis_cache import RedisCacheProvider
from app.infrastructure.email.mock_email import MockEmailProvider
from app.infrastructure.email.smtp_email import SMTPEmailProvider
from app.infrastructure.llm_client import MockLLMClient
from app.infrastructure.real_llm_client import RealLLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container providing centralized service composition.
    
    Responsibilities:
    - Initialize infrastructure providers
    - Create repositories
    - Instantiate services
    - Manage service dependencies
    - Enable easy swapping of implementations (e.g., mock → real)
    
    Usage:
        container = ServiceContainer(db_session)
        chat_service = container.get_chat_service()
    """
    
    # Singleton instances
    _instance: Optional["ServiceContainer"] = None
    
    def __init__(
        self,
        db: AsyncSession,
        storage_provider: Optional[IStorageProvider] = None,
        queue_provider: Optional[IQueueProvider] = None,
        cache_provider: Optional[ICacheProvider] = None,
        email_provider: Optional[IEmailProvider] = None,
        llm_client: Optional[ILLMClient] = None,
    ):
        """
        Initialize container with dependencies.
        
        If infrastructure providers are not provided, mock implementations are used.
        This enables:
        - Development/testing without Redis, S3, LLM APIs
        - Easy substitution in production
        """
        self.db = db
        
        # Initialize storage provider - use CEPH if configured, otherwise mock
        if storage_provider:
            self.storage_provider = storage_provider
        elif all([
            settings.CEPH_ENDPOINT and settings.CEPH_ENDPOINT.strip(),
            settings.CEPH_ACCESS_KEY and settings.CEPH_ACCESS_KEY.strip(),
            settings.CEPH_SECRET_KEY and settings.CEPH_SECRET_KEY.strip(),
            settings.CEPH_BUCKET and settings.CEPH_BUCKET.strip(),
        ]):
            try:
                self.storage_provider = CephStorageProvider()
                logger.info("CEPH configuration detected - using CephStorageProvider")
            except Exception as e:
                logger.warning(f"Failed to initialize CephStorageProvider: {e}. Falling back to MockStorageProvider.")
                self.storage_provider = MockStorageProvider()
        else:
            self.storage_provider = MockStorageProvider()
            missing = []
            if not settings.CEPH_ENDPOINT or not settings.CEPH_ENDPOINT.strip():
                missing.append("CEPH_ENDPOINT")
            if not settings.CEPH_ACCESS_KEY or not settings.CEPH_ACCESS_KEY.strip():
                missing.append("CEPH_ACCESS_KEY")
            if not settings.CEPH_SECRET_KEY or not settings.CEPH_SECRET_KEY.strip():
                missing.append("CEPH_SECRET_KEY")
            if not settings.CEPH_BUCKET or not settings.CEPH_BUCKET.strip():
                missing.append("CEPH_BUCKET")
            logger.warning(f"CEPH not configured (missing: {', '.join(missing)}) - using MockStorageProvider. Files will not be persisted.")
        
        self.queue_provider = queue_provider or MockQueueProvider()
        
        # Initialize cache provider - use Redis if configured, otherwise mock
        if cache_provider:
            self.cache_provider = cache_provider
        elif settings.REDIS_URL and settings.REDIS_URL.strip():
            try:
                self.cache_provider = RedisCacheProvider()
                logger.info("REDIS_URL detected - using RedisCacheProvider")
            except Exception as e:
                logger.warning(f"Failed to initialize RedisCacheProvider: {e}. Falling back to MockCacheProvider.")
                self.cache_provider = MockCacheProvider()
        else:
            self.cache_provider = MockCacheProvider()
            logger.warning("REDIS_URL not configured - using MockCacheProvider. Caching will be in-memory only.")
        
        # Initialize email provider - use real SMTP if configured, otherwise mock
        if email_provider:
            self.email_provider = email_provider
        elif all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            self.email_provider = SMTPEmailProvider()
            logger.info("SMTP configuration detected - using SMTPEmailProvider")
        else:
            self.email_provider = MockEmailProvider()
            logger.warning("SMTP not configured - using MockEmailProvider. Emails will not be sent.")
        
        # Initialize LLM client - use real client if API key is configured, otherwise mock
        # Pass cache provider to LLM client for caching
        if llm_client:
            self.llm_client = llm_client
        elif settings.OPENAI_API_KEY:
            self.llm_client = RealLLMClient(cache_provider=self.cache_provider)
            logger.info("OPENAI_API_KEY detected - using RealLLMClient")
        else:
            self.llm_client = MockLLMClient()
            logger.warning("OPENAI_API_KEY not configured - using MockLLMClient. LLM features will use mock responses.")
        
        logger.info(f"ServiceContainer initialized with providers:")
        logger.info(f"  Storage: {self.storage_provider.__class__.__name__}")
        logger.info(f"  Queue: {self.queue_provider.__class__.__name__}")
        logger.info(f"  Cache: {self.cache_provider.__class__.__name__}")
        logger.info(f"  Email: {self.email_provider.__class__.__name__}")
        logger.info(f"  LLM: {self.llm_client.__class__.__name__}")
    
    # ========================================================================
    # REPOSITORY FACTORIES
    # ========================================================================
    
    def get_user_repository(self) -> UserRepository:
        """Get or create UserRepository."""
        return UserRepository(self.db)
    
    def get_notebook_repository(self) -> NotebookRepository:
        """Get or create NotebookRepository."""
        return NotebookRepository(self.db)
    
    def get_source_repository(self) -> SourceRepository:
        """Get or create SourceRepository."""
        return SourceRepository(self.db)
    
    def get_chunk_repository(self) -> ChunkRepository:
        """Get or create ChunkRepository."""
        return ChunkRepository(self.db)
    
    def get_document_repository(self) -> DocumentRepository:
        """Get or create DocumentRepository."""
        return DocumentRepository(self.db)
    
    def get_job_repository(self) -> JobRepository:
        """Get or create JobRepository."""
        return JobRepository(self.db)
    
    def get_conversation_repository(self) -> ConversationRepository:
        """Get or create ConversationRepository."""
        return ConversationRepository(self.db)
    
    def get_message_repository(self) -> MessageRepository:
        """Get or create MessageRepository."""
        return MessageRepository(self.db)
    
    def get_quiz_repository(self) -> QuizRepository:
        """Get or create QuizRepository."""
        return QuizRepository(self.db)
    
    def get_history_repository(self) -> HistoryRepository:
        """Get or create HistoryRepository."""
        return HistoryRepository(self.db)
    
    def get_study_guide_repository(self) -> StudyGuideRepository:
        """Get or create StudyGuideRepository."""
        return StudyGuideRepository(self.db)
    
    # ========================================================================
    # SERVICE FACTORIES
    # ========================================================================
    
    def get_auth_service(self) -> AuthService:
        """
        Get AuthService instance.
        
        Service composition:
        - UserRepository (for user/token/OTP operations)
        - IEmailProvider (for OTP delivery)
        """
        return AuthService(
            user_repo=self.get_user_repository(),
            email_provider=self.email_provider,
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )
    
    def get_notebook_service(self) -> NotebookService:
        """
        Get NotebookService instance.
        
        Service composition:
        - NotebookRepository
        - SourceRepository
        - ChunkRepository
        - ConversationRepository
        """
        return NotebookService(
            notebook_repo=self.get_notebook_repository(),
            source_repo=self.get_source_repository(),
            chunk_repo=self.get_chunk_repository(),
            conversation_repo=self.get_conversation_repository(),
            max_notebooks_per_user=50,
        )
    
    def get_chat_service(self) -> ChatService:
        """
        Get ChatService instance.
        
        Service composition:
        - ConversationRepository
        - MessageRepository
        - HistoryRepository
        """
        return ChatService(
            conversation_repo=self.get_conversation_repository(),
            message_repo=self.get_message_repository(),
            history_repo=self.get_history_repository(),
        )
    
    def get_document_service(self) -> DocumentService:
        """
        Get DocumentService instance.
        
        Service composition:
        - DocumentRepository
        - JobRepository
        - IStorageProvider
        - IQueueProvider
        """
        return DocumentService(
            document_repo=self.get_document_repository(),
            job_repo=self.get_job_repository(),
            storage_provider=self.storage_provider,
            queue_provider=self.queue_provider,
            max_file_size_mb=50,
        )
    
    def get_job_service(self) -> JobService:
        """
        Get JobService instance.
        
        Service composition:
        - JobRepository
        """
        return JobService(
            job_repo=self.get_job_repository(),
            max_retries=3,
        )
    
    def get_history_service(self) -> HistoryService:
        """
        Get HistoryService instance.
        
        Service composition:
        - HistoryRepository
        """
        return HistoryService(
            history_repo=self.get_history_repository(),
            retention_days=90,
        )
    
    def get_pdf_service(self) -> PdfService:
        """
        Get PdfService instance.
        
        Note: Requires IPdfProcessor implementation (not mocked).
        Should be provided when initializing container for production.
        """
        # For now, return with None processor - will throw error if actually used
        # Production setup should provide real IPdfProcessor
        class NullPdfProcessor:
            async def extract_text(self, file_path: str) -> str:
                raise NotImplementedError("PDF processor not configured")
            
            async def extract_pages(self, file_path: str) -> list:
                raise NotImplementedError("PDF processor not configured")
        
        return PdfService(pdf_processor=NullPdfProcessor())
    
    def get_rag_ingest_service(self) -> RAGIngestService:
        """
        Get RAGIngestService instance.
        
        Service composition:
        - ChunkRepository
        - ILLMClient
        """
        return RAGIngestService(
            chunk_repo=self.get_chunk_repository(),
            llm_client=self.llm_client,
            chunk_size=512,
            overlap=100,
        )
    
    def get_quiz_service(self) -> QuizService:
        """
        Get QuizService instance.
        
        Service composition:
        - QuizRepository
        - ILLMClient
        """
        return QuizService(
            quiz_repo=self.get_quiz_repository(),
            llm_client=self.llm_client,
        )
    
    def get_cache_monitoring_service(self) -> CacheMonitoringService:
        """
        Get CacheMonitoringService instance.
        
        Service composition:
        - ICacheProvider
        """
        return CacheMonitoringService(
            cache_provider=self.cache_provider,
        )
    
    def get_external_processing_service(self) -> ExternalProcessingService:
        """
        Get ExternalProcessingService instance.
        
        Service composition:
        - ILLMClient
        """
        return ExternalProcessingService(
            llm_client=self.llm_client,
            max_retries=3,
            timeout_seconds=30,
        )
    
    def get_transaction_example_service(self) -> TransactionExampleService:
        """
        Get TransactionExampleService instance.
        
        Service composition:
        - NotebookRepository
        - SourceRepository
        - ChunkRepository
        """
        return TransactionExampleService(
            notebook_repo=self.get_notebook_repository(),
            source_repo=self.get_source_repository(),
            chunk_repo=self.get_chunk_repository(),
        )
    
    def get_source_generation_service(self) -> SourceGenerationService:
        """
        Get SourceGenerationService instance.
        
        Service composition:
        - SourceRepository
        - ChunkRepository
        - QuizRepository
        - StudyGuideRepository
        - HistoryRepository
        - ILLMClient
        """
        return SourceGenerationService(
            source_repo=self.get_source_repository(),
            chunk_repo=self.get_chunk_repository(),
            quiz_repo=self.get_quiz_repository(),
            study_guide_repo=self.get_study_guide_repository(),
            history_repo=self.get_history_repository(),
            llm_client=self.llm_client,
        )
    
    def get_source_processing_service(self) -> SourceProcessingService:
        """
        Get SourceProcessingService instance.
        
        Service composition:
        - SourceRepository
        - IStorageProvider
        - RAGIngestService
        - PdfService (optional)
        """
        return SourceProcessingService(
            source_repo=self.get_source_repository(),
            storage_provider=self.storage_provider,
            rag_ingest_service=self.get_rag_ingest_service(),
            pdf_service=None,  # Optional - will use PyMuPDF fallback if not provided
        )
    
    # ========================================================================
    # SINGLETON PATTERN (optional)
    # ========================================================================
    
    @classmethod
    def set_instance(cls, instance: "ServiceContainer") -> None:
        """Set singlet on instance."""
        cls._instance = instance
    
    @classmethod
    def get_instance(cls) -> Optional["ServiceContainer"]:
        """Get singleton instance."""
        return cls._instance
