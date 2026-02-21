"""Job service for background job orchestration and state management."""

import logging
from typing import Optional, List

from app.domain.models.job import Job
from app.domain.repositories.document_repository import JobRepository
from app.domain.errors import NotFoundError, ForbiddenError, BusinessRuleViolationError, ErrorCode

logger = logging.getLogger(__name__)


class JobService:
    """
    Job service managing background job lifecycle and state transitions.
    
    Responsibilities:
    - Job creation and state tracking
    - State machine enforcement (PENDING → RUNNING → COMPLETED/FAILED)
    - Retry logic and failure handling
    - Worker coordination
    """
    
    def __init__(
        self,
        job_repo: JobRepository,
        max_retries: int = 3,
    ):
        self.job_repo = job_repo
        self.max_retries = max_retries
    
    async def get_job(self, job_id: int, user_id: int) -> Job:
        """Get job with authorization check."""
        job = await self.job_repo.get_by_id(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError(
                f"Job {job_id} not found or user not authorized",
                resource_type="Job",
                resource_id=job_id,
            )
        return job
    
    async def list_user_jobs(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Job]:
        """List all jobs for a user."""
        return await self.job_repo.list_by_user(user_id, skip=skip, limit=limit)
    
    async def mark_job_running(self, job_id: int) -> Job:
        """Mark job as running (worker picked it up)."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found", resource_type="Job", resource_id=job_id)
        
        if job.status != "PENDING":
            raise BusinessRuleViolationError(
                f"Cannot start job in {job.status} status. Must be PENDING.",
                code=ErrorCode.OPERATION_NOT_ALLOWED,
            )
        
        job = await self.job_repo.update(job_id, status="RUNNING", progress=10)
        logger.info(f"Job marked running: {job_id}")
        return job
    
    async def update_job_progress(self, job_id: int, progress: int) -> Job:
        """Update job progress (0-100)."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found", resource_type="Job", resource_id=job_id)
        
        if job.status not in ("RUNNING", "PENDING"):
            raise BusinessRuleViolationError(
                f"Cannot update progress for job in {job.status} status",
                code=ErrorCode.OPERATION_NOT_ALLOWED,
            )
        
        # Ensure progress is between 0 and 100
        progress = max(0, min(100, progress))
        
        job = await self.job_repo.update(job_id, progress=progress)
        logger.info(f"Job progress updated: {job_id} -> {progress}%")
        return job
    
    async def mark_job_completed(self, job_id: int, result: Optional[dict] = None) -> Job:
        """Mark job as completed with result."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found", resource_type="Job", resource_id=job_id)
        
        if job.status != "RUNNING":
            raise BusinessRuleViolationError(
                f"Cannot complete job in {job.status} status. Must be RUNNING.",
                code=ErrorCode.OPERATION_NOT_ALLOWED,
            )
        
        job = await self.job_repo.update(
            job_id,
            status="COMPLETED",
            progress=100,
            result_json=result or {},
            error_message=None,
        )
        logger.info(f"Job completed: {job_id}")
        return job
    
    async def mark_job_failed(self, job_id: int, error_message: str) -> Job:
        """Mark job as failed with error message."""
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError(f"Job {job_id} not found", resource_type="Job", resource_id=job_id)
        
        if job.status not in ("RUNNING", "PENDING"):
            raise BusinessRuleViolationError(
                f"Cannot fail job in {job.status} status",
                code=ErrorCode.OPERATION_NOT_ALLOWED,
            )
        
        # Check if retries available
        retry_count = job.metadata.get("retry_count", 0) if job.metadata else 0
        
        if retry_count < self.max_retries:
            # Mark for retry
            new_metadata = (job.metadata or {}).copy()
            new_metadata["retry_count"] = retry_count + 1
            
            job = await self.job_repo.update(
                job_id,
                status="PENDING",
                error_message=error_message,
                metadata=new_metadata,
            )
            logger.warning(f"Job failed and queued for retry: {job_id} (retry {retry_count + 1}/{self.max_retries})")
        else:
            # No more retries
            job = await self.job_repo.update(
                job_id,
                status="FAILED",
                error_message=error_message,
                progress=0,
            )
            logger.error(f"Job failed permanently: {job_id} - {error_message}")
        
        return job
    
    async def list_pending_jobs(
        self,
        job_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Job]:
        """List pending jobs (for workers to pickup)."""
        return await self.job_repo.list_by_status("PENDING", limit=limit)
