"""Unit tests for DocumentService (no FastAPI, demonstrates infrastructure integration)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.services.document_service import DocumentService
from app.domain.repositories.document_repository import DocumentRepository, JobRepository
from app.domain.errors import NotFoundError, ValidationError
from app.infrastructure.storage.mock_storage import MockStorageProvider
from app.infrastructure.queues.mock_queue import MockQueueProvider
from tests._fixtures import UserFactory, async_db


class TestDocumentService:
    """Test cases for DocumentService with infrastructure integration."""
    
    @pytest.fixture
    async def document_service(self, async_db: AsyncSession):
        """Create DocumentService with mock infrastructure."""
        return DocumentService(
            document_repo=DocumentRepository(async_db),
            job_repo=JobRepository(async_db),
            storage_provider=MockStorageProvider(),
            queue_provider=MockQueueProvider(),
            max_file_size_mb=100,
        )
    
    # ========================================================================
    # UPLOAD DOCUMENT TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test successful document upload."""
        user = await UserFactory.create(async_db)
        
        file_content = b"PDF content here"
        document = await document_service.upload_document(
            user_id=user.id,
            filename="report.pdf",
            file_content=file_content,
            content_type="application/pdf",
        )
        
        assert document.owner_id == user.id
        assert document.filename == "report.pdf"
        assert document.content_type == "application/pdf"
        assert document.size_bytes == len(file_content)
    
    @pytest.mark.asyncio
    async def test_upload_document_exceeds_size_limit(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test upload fails when file size exceeds limit."""
        user = await UserFactory.create(async_db)
        
        # Create file larger than 100MB limit
        large_content = b"x" * (101 * 1024 * 1024)  # 101 MB
        
        with pytest.raises(ValidationError):
            await document_service.upload_document(
                user_id=user.id,
                filename="huge.pdf",
                file_content=large_content,
            )
    
    @pytest.mark.asyncio
    async def test_upload_document_deduplication(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test that duplicate files return existing document."""
        user = await UserFactory.create(async_db)
        
        file_content = b"Same content"
        
        # Upload first time
        doc1 = await document_service.upload_document(
            user_id=user.id,
            filename="file1.pdf",
            file_content=file_content,
        )
        
        # Upload same content with different filename
        doc2 = await document_service.upload_document(
            user_id=user.id,
            filename="file2.pdf",
            file_content=file_content,
        )
        
        # Should return same document (SHA256 hash matches)
        assert doc1.id == doc2.id
        assert doc1.file_hash == doc2.file_hash
    
    @pytest.mark.asyncio
    async def test_upload_creates_processing_job(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test that upload creates background job for processing."""
        user = await UserFactory.create(async_db)
        queue = document_service.queue_provider  # Get mock queue
        
        document = await document_service.upload_document(
            user_id=user.id,
            filename="document.pdf",
            file_content=b"PDF content",
        )
        
        # Verify job was created and queued
        jobs = await document_service.job_repo.list_by_status("PENDING")
        assert len(jobs) >= 1
        
        # Verify job references document
        job = jobs[0]
        assert job.document_id == document.id
        assert job.job_type == "PDF_TEXT_EXTRACTION"
    
    # ========================================================================
    # GET DOCUMENT TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_get_document_success(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test retrieving document."""
        user = await UserFactory.create(async_db)
        document = await document_service.upload_document(
            user_id=user.id,
            filename="test.pdf",
            file_content=b"content",
        )
        
        retrieved = await document_service.get_document(document.id, user.id)
        
        assert retrieved.id == document.id
        assert retrieved.owner_id == user.id
    
    @pytest.mark.asyncio
    async def test_get_document_unauthorized(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test authorization check on get."""
        user1 = await UserFactory.create(async_db, email="user1@example.com")
        user2 = await UserFactory.create(async_db, email="user2@example.com")
        
        document = await document_service.upload_document(
            user_id=user1.id,
            filename="private.pdf",
            file_content=b"secret",
        )
        
        # User 2 tries to access User 1's document
        with pytest.raises(NotFoundError):
            await document_service.get_document(document.id, user2.id)
    
    # ========================================================================
    # DOCUMENT STATUS TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_get_document_status_pending(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test getting status of pending document."""
        user = await UserFactory.create(async_db)
        document = await document_service.upload_document(
            user_id=user.id,
            filename="processing.pdf",
            file_content=b"content",
        )
        
        status = await document_service.get_document_status(document.id, user.id)
        
        assert status["status"] == "processing"
        assert status["document_id"] == document.id
    
    @pytest.mark.asyncio
    async def test_document_status_progresses(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test document status progression through job lifecycle."""
        user = await UserFactory.create(async_db)
        document = await document_service.upload_document(
            user_id=user.id,
            filename="doc.pdf",
            file_content=b"content",
        )
        
        # Initial status is processing
        status = await document_service.get_document_status(document.id, user.id)
        assert status["status"] == "processing"
        
        # Get the job
        jobs = await document_service.job_repo.list_by_status("PENDING")
        job = jobs[0]
        
        # Mark job as running
        await document_service.job_repo.update_job_status(job.id, "RUNNING")
        
        # Mark job as completed
        await document_service.job_repo.update_job_status(job.id, "COMPLETED")
        
        # Status should now be ready
        status = await document_service.get_document_status(document.id, user.id)
        assert status["status"] == "ready"
    
    # ========================================================================
    # DELETE DOCUMENT TESTS
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_delete_document_success(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test successful document deletion."""
        user = await UserFactory.create(async_db)
        document = await document_service.upload_document(
            user_id=user.id,
            filename="delete_me.pdf",
            file_content=b"content",
        )
        
        deleted = await document_service.delete_document(document.id, user.id)
        
        assert deleted is True
        
        # Verify it's deleted
        with pytest.raises(NotFoundError):
            await document_service.get_document(document.id, user.id)
    
    @pytest.mark.asyncio
    async def test_delete_document_removes_from_storage(
        self,
        async_db: AsyncSession,
        document_service: DocumentService,
    ):
        """Test that deletion removes file from storage."""
        user = await UserFactory.create(async_db)
        storage = document_service.storage_provider
        
        document = await document_service.upload_document(
            user_id=user.id,
            filename="stored.pdf",
            file_content=b"stored content",
        )
        
        # Verify file exists in storage
        assert storage.files.get(document.storage_key) is not None
        
        # Delete document
        await document_service.delete_document(document.id, user.id)
        
        # Verify file removed from storage
        assert storage.files.get(document.storage_key) is None


# ============================================================================
# ARCHITECTURE INSIGHTS FROM THESE TESTS
# ============================================================================
"""
This test demonstrates several critical enterprise patterns:

1. INFRASTRUCTURE ABSTRACTION ENABLES TESTING
   Problem: Can't test file upload without S3, job queue without Celery
   Solution: Inject mock providers at test time
   Result: Tests run in memory, no external dependencies

2. BUSINESS LOGIC SEPARATE FROM I/O
   DocumentService doesn't know about MockStorageProvider
   It only knows about IStorageProvider interface
   Swap MockStorageProvider for S3Provider in production
   Tests pass identically with either implementation

3. MULTI-LAYER INTEGRATION TESTING
   - Upload creates Document record
   - Upload stores file in storage
   - Upload creates Job in repository
   - Job workflow progresses through states
   All without any HTTP/web framework knowledge

4. DEDUPLICATION LOGIC IS TESTABLE
   - File hashing is pure function
   - Can test duplicate detection
   - Can test that same content returns same document

5. AUTHORIZATION BUILT INTO SERVICE
   - Get document checks ownership
   - Delete document checks ownership
   - Delete cascades properly
   - No need for middleware/decorators

6. ERROR HANDLING IS CONSISTENT
   - Size limit validation
   - Not found errors are business errors (not HTTP)
   - All errors are from DomainError hierarchy

WHY THIS MATTERS FOR ENTERPRISE:
✓ Tests are isolated (in-memory database)
✓ Tests are independent (no test ordering)
✓ Tests are deterministic (always same result)
✓ Tests document expected behavior
✓ Tests enable refactoring safely
✓ Tests validate architecture patterns
✓ New team members understand patterns by reading tests
"""
