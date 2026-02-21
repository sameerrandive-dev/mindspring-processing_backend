"""In-memory mock job queue provider for testing."""

from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from app.domain.interfaces import IQueueProvider, JobStatus


class MockQueueProvider(IQueueProvider):
    """In-memory job queue for testing."""
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
    
    async def enqueue(
        self,
        job_type: str,
        job_id: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """Enqueue a job in memory."""
        queue_job_id = str(uuid.uuid4())
        self._jobs[queue_job_id] = {
            "queue_job_id": queue_job_id,
            "job_type": job_type,
            "job_id": job_id,
            "payload": payload,
            "priority": priority,
            "status": JobStatus.PENDING,
            "result": None,
            "error": None,
            "created_at": datetime.utcnow(),
        }
        return queue_job_id
    
    async def get_job_status(self, queue_job_id: str) -> JobStatus:
        """Get job status from memory."""
        job = self._jobs.get(queue_job_id)
        if not job:
            return JobStatus.FAILED
        return JobStatus(job["status"])
    
    async def get_job_result(self, queue_job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result from memory."""
        job = self._jobs.get(queue_job_id)
        if not job:
            return None
        return job.get("result")
    
    async def dequeue(self, job_type: str) -> Optional[Dict[str, Any]]:
        """Get first pending job of type (for workers)."""
        for queue_job_id, job in self._jobs.items():
            if job["job_type"] == job_type and job["status"] == JobStatus.PENDING:
                job["status"] = JobStatus.RUNNING
                return job
        return None
    
    async def mark_complete(self, queue_job_id: str, result: Dict[str, Any]) -> None:
        """Mark job as completed."""
        if queue_job_id in self._jobs:
            self._jobs[queue_job_id]["status"] = JobStatus.COMPLETED
            self._jobs[queue_job_id]["result"] = result
    
    async def mark_failed(self, queue_job_id: str, error: str) -> None:
        """Mark job as failed."""
        if queue_job_id in self._jobs:
            self._jobs[queue_job_id]["status"] = JobStatus.FAILED
            self._jobs[queue_job_id]["error"] = error
