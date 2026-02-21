"""Document and Job repositories."""

from typing import Optional, List
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.document import Document
from app.domain.models.job import Job
from app.domain.errors import NotFoundError


class DocumentRepository:
    """Repository for Document entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        user_id: int,
        file_name: str,
        file_size: int,
        file_hash: str,
        storage_key: str,
        status: str = "pending",
        metadata: Optional[dict] = None,
    ) -> Document:
        """Create a new document."""
        document = Document(
            user_id=user_id,
            file_name=file_name,
            file_size=file_size,
            file_hash=file_hash,
            storage_key=storage_key,
            status=status,
            metadata=metadata or {},
        )
        self.db.add(document)
        await self.db.flush()
        return document
    
    async def get_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID."""
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, file_hash: str) -> Optional[Document]:
        """Get document by file hash (for deduplication)."""
        result = await self.db.execute(select(Document).where(Document.file_hash == file_hash))
        return result.scalar_one_or_none()
    
    async def list_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        """List documents by user with pagination."""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(Document.created_at))
        )
        return result.scalars().all()
    
    async def update(self, document_id: int, **updates) -> Document:
        """Update document fields."""
        document = await self.get_by_id(document_id)
        if not document:
            raise NotFoundError(f"Document {document_id} not found", resource_type="Document", resource_id=document_id)
        
        for key, value in updates.items():
            if hasattr(document, key) and key != "id" and key != "user_id":
                setattr(document, key, value)
        
        await self.db.flush()
        return document
    
    async def delete(self, document_id: int) -> bool:
        """Delete document."""
        document = await self.get_by_id(document_id)
        if not document:
            return False
        
        await self.db.delete(document)
        await self.db.flush()
        return True


class JobRepository:
    """Repository for Job (background task) entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        document_id: int,
        user_id: int,
        job_type: str,
        status: str = "PENDING",
        progress: int = 0,
        result_json: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> Job:
        """Create a new job."""
        job = Job(
            document_id=document_id,
            user_id=user_id,
            job_type=job_type,
            status=status,
            progress=progress,
            result_json=result_json or {},
            error_message=error_message,
        )
        self.db.add(job)
        await self.db.flush()
        return job
    
    async def get_by_id(self, job_id: int) -> Optional[Job]:
        """Get job by ID."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()
    
    async def list_by_document(self, document_id: int) -> List[Job]:
        """List all jobs for a document."""
        result = await self.db.execute(
            select(Job).where(Job.document_id == document_id).order_by(desc(Job.created_at))
        )
        return result.scalars().all()
    
    async def list_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Job]:
        """List jobs by user with pagination."""
        result = await self.db.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(Job.created_at))
        )
        return result.scalars().all()
    
    async def list_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Job]:
        """List jobs by status (useful for workers to find jobs to process)."""
        result = await self.db.execute(
            select(Job)
            .where(Job.status == status)
            .offset(skip)
            .limit(limit)
            .order_by(Job.created_at)  # Process older jobs first
        )
        return result.scalars().all()
    
    async def update(self, job_id: int, **updates) -> Job:
        """Update job fields."""
        job = await self.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found", resource_type="Job", resource_id=job_id)
        
        for key, value in updates.items():
            if hasattr(job, key) and key != "id":
                setattr(job, key, value)
        
        await self.db.flush()
        return job
    
    async def delete(self, job_id: int) -> bool:
        """Delete job."""
        job = await self.get_by_id(job_id)
        if not job:
            return False
        
        await self.db.delete(job)
        await self.db.flush()
        return True
