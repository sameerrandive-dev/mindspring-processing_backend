"""History service for audit trail and retention management."""

import logging
from typing import Optional, List

from app.domain.models.generation_history import GenerationHistory
from app.domain.repositories.history_repository import HistoryRepository
from app.domain.errors import NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)


class HistoryService:
    """
    History service for audit trails and generation tracking.
    
    Responsibilities:
    - Record all generations (chat, quiz, study guides, etc.)
    - Query audit trails
    - Retention policy enforcement
    - Access control
    """
    
    def __init__(
        self,
        history_repo: HistoryRepository,
        retention_days: int = 90,
    ):
        self.history_repo = history_repo
        self.retention_days = retention_days
    
    async def record_generation(
        self,
        user_id: int,
        generation_type: str,
        title: str,
        content: str,
        content_preview: Optional[str] = None,
        resource_id: Optional[int] = None,
        notebook_id: Optional[int] = None,
        document_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> GenerationHistory:
        """Record a generation in history."""
        history = await self.history_repo.create(
            user_id=user_id,
            history_type=generation_type,
            title=title,
            content=content,
            content_preview=content_preview or content[:200],
            resource_id=resource_id,
            notebook_id=notebook_id,
            document_id=document_id,
            metadata=metadata or {},
        )
        
        logger.info(f"Generation recorded: {history.id} for user {user_id}")
        return history
    
    async def get_history(self, history_id: int, user_id: int) -> GenerationHistory:
        """Get history record with authorization."""
        history = await self.history_repo.get_by_id(history_id)
        if not history or history.user_id != user_id:
            raise NotFoundError(
                f"History record {history_id} not found or user not authorized",
                resource_type="GenerationHistory",
                resource_id=history_id,
            )
        return history
    
    async def list_user_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List all history for a user."""
        return await self.history_repo.list_by_user(user_id, skip=skip, limit=limit)
    
    async def list_user_history_by_type(
        self,
        user_id: int,
        history_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List history of specific type for a user."""
        return await self.history_repo.list_by_user_and_type(
            user_id,
            history_type,
            skip=skip,
            limit=limit,
        )
    
    async def list_notebook_history(
        self,
        notebook_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List history for a notebook."""
        # Could add user ownership check here if needed
        return await self.history_repo.list_by_notebook(
            notebook_id,
            skip=skip,
            limit=limit,
        )
    
    async def delete_history(self, history_id: int, user_id: int) -> bool:
        """Delete a history record."""
        history = await self.get_history(history_id, user_id)
        
        success = await self.history_repo.delete(history_id)
        if success:
            logger.info(f"History deleted: {history_id}")
        
        return success
    
    async def enforce_retention_policy(self, user_id: int) -> int:
        """Delete old history records beyond retention period."""
        deleted_count = await self.history_repo.delete_by_user_older_than(
            user_id,
            days=self.retention_days,
        )
        
        if deleted_count > 0:
            logger.info(f"Retention policy enforced: deleted {deleted_count} records for user {user_id}")
        
        return deleted_count
