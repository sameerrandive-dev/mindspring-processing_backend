"""Document service for file upload and processing coordination."""

import logging
import hashlib
from typing import Optional

from app.domain.models.document import Document
from app.domain.models.job import Job
from app.domain.repositories.document_repository import DocumentRepository, JobRepository
from app.domain.errors import NotFoundError, ForbiddenError, ConflictError, ErrorCode, ExternalServiceError
from app.domain.interfaces import IStorageProvider, IQueueProvider

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Document service managing file uploads and processing.
    
    Responsibilities:
    - File upload with deduplication
    - Job creation and queueing
    - Document lifecycle management
    - Storage coordination
    - Triggering RAG ingestion
    """
    
    def __init__(
        self,
        document_repo: DocumentRepository,
        job_repo: JobRepository,
        storage_provider: IStorageProvider,
        queue_provider: IQueueProvider,
        max_file_size_mb: int = 50,
    ):
        self.document_repo = document_repo
        self.job_repo = job_repo
        self.storage_provider = storage_provider
        self.queue_provider = queue_provider
        self.max_file_size_mb = max_file_size_mb
    
    async def upload_document(
        self,
        user_id: int,
        file_name: str,
        file_content: bytes,
        file_type: str = "pdf",
    ) -> Document:
        """
        Upload a document with deduplication.
        
        If file hash matches existing document, returns existing document.
        Otherwise, creates new document and queues for processing.
        
        Raises:
            ExternalServiceError: storage provider failed
            ConflictError: file too large
        """
        # Validate file size
        file_size = len(file_content)
        max_bytes = self.max_file_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ConflictError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds limit ({self.max_file_size_mb} MB)",
                code=ErrorCode.RESOURCE_CONFLICT,
            )
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicate
        existing = await self.document_repo.get_by_hash(file_hash)
        if existing:
            logger.info(f"Document already exists (duplicate): {existing.id}")
            return existing
        
        # Store file
        storage_key = f"documents/{user_id}/{file_hash[:10]}/{file_name}"
        try:
            await self.storage_provider.store(
                key=storage_key,
                content=file_content,
                metadata={"original_name": file_name, "file_type": file_type},
            )
        except Exception as e:
            raise ExternalServiceError(
                "Failed to store file",
                service_name="StorageProvider",
                original_error=e,
            )
        
        # Create document record
        document = await self.document_repo.create(
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
            storage_key=storage_key,
            status="processing",
            metadata={"file_type": file_type},
        )
        
        # Create processing job
        job = await self.job_repo.create(
            document_id=document.id,
            user_id=user_id,
            job_type="document_processing",
            status="PENDING",
            progress=0,
        )
        
        # Queue job
        try:
            queue_job_id = await self.queue_provider.enqueue(
                job_type="document_processing",
                job_id=str(job.id),
                payload={
                    "document_id": document.id,
                    "user_id": user_id,
                    "file_type": file_type,
                    "storage_key": storage_key,
                },
                priority=1,
            )
            
            # Update job with queue ID
            await self.job_repo.update(job.id, queue_job_id=queue_job_id)
            
        except Exception as e:
            logger.error(f"Failed to queue document job: {e}")
            await self.document_repo.update(document.id, status="error")
            raise ExternalServiceError(
                "Failed to queue document for processing",
                service_name="QueueProvider",
                original_error=e,
            )
        
        logger.info(f"Document uploaded and queued: {document.id}")
        return document
    
    async def get_document(self, document_id: int, user_id: int) -> Document:
        """Get document with authorization check."""
        document = await self.document_repo.get_by_id(document_id)
        if not document or document.user_id != user_id:
            raise NotFoundError(
                f"Document {document_id} not found or user not authorized",
                resource_type="Document",
                resource_id=document_id,
            )
        return document
    
    async def get_document_status(self, document_id: int, user_id: int) -> dict:
        """Get document processing status."""
        document = await self.get_document(document_id, user_id)
        
        # Get associated job
        jobs = await self.job_repo.list_by_document(document_id)
        latest_job = jobs[0] if jobs else None
        
        return {
            "document_id": document.id,
            "file_name": document.file_name,
            "status": document.status,
            "file_size": document.file_size,
            "job_status": latest_job.status if latest_job else None,
            "job_progress": latest_job.progress if latest_job else 0,
            "error": latest_job.error_message if latest_job and latest_job.status == "FAILED" else None,
        }
    
    async def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete document and associated storage."""
        document = await self.get_document(document_id, user_id)
        
        # Delete from storage
        try:
            await self.storage_provider.delete(document.storage_key)
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")
        
        # Delete database record
        success = await self.document_repo.delete(document_id)
        if success:
            logger.info(f"Document deleted: {document_id}")
        
        return success
