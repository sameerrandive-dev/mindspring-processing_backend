"""GenerationHistory repository for audit trails and usage tracking."""

from typing import Optional, List
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.generation_history import GenerationHistory
from app.domain.errors import NotFoundError


class HistoryRepository:
    """Repository for GenerationHistory entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        user_id: str,
        history_type: str,
        title: str,
        content: str,
        content_preview: Optional[str] = None,
        resource_id: Optional[str] = None,
        notebook_id: Optional[str] = None,
        document_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> GenerationHistory:
        """Create a new history record."""
        history = GenerationHistory(
            user_id=user_id,
            type=history_type,
            title=title,
            content=content,
            content_preview=content_preview or content[:200] if content else "",
            resource_id=resource_id,
            notebook_id=notebook_id,
            document_id=document_id,
            metadata_=metadata or {},
        )
        self.db.add(history)
        await self.db.flush()
        return history
    
    async def get_by_id(self, history_id: str) -> Optional[GenerationHistory]:
        """Get history record by ID."""
        result = await self.db.execute(
            select(GenerationHistory).where(GenerationHistory.id == history_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List history records for a user."""
        result = await self.db.execute(
            select(GenerationHistory)
            .where(GenerationHistory.user_id == user_id)
            .where(GenerationHistory.deleted_at.is_(None))  # Exclude soft-deleted
            .offset(skip)
            .limit(limit)
            .order_by(desc(GenerationHistory.created_at))
        )
        return result.scalars().all()
    
    async def list_by_user_and_type(
        self,
        user_id: str,
        history_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List history records of a specific type for a user."""
        result = await self.db.execute(
            select(GenerationHistory)
            .where(
                and_(
                    GenerationHistory.user_id == user_id,
                    GenerationHistory.type == history_type,
                    GenerationHistory.deleted_at.is_(None),
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(desc(GenerationHistory.created_at))
        )
        return result.scalars().all()
    
    async def list_by_notebook(
        self,
        notebook_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenerationHistory]:
        """List history records for a notebook."""
        result = await self.db.execute(
            select(GenerationHistory)
            .where(GenerationHistory.notebook_id == notebook_id)
            .where(GenerationHistory.deleted_at.is_(None))  # Exclude soft-deleted
            .offset(skip)
            .limit(limit)
            .order_by(desc(GenerationHistory.created_at))
        )
        return result.scalars().all()
    
    async def delete(self, history_id: str) -> bool:
        """Soft delete history record."""
        history = await self.get_by_id(history_id)
        if not history:
            return False
        
        # Soft delete: set deleted_at timestamp
        from datetime import datetime, timezone
        history.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
    
    async def delete_by_user_older_than(self, user_id: str, days: int) -> int:
        """Delete history records older than specified days (retention policy)."""
        from datetime import datetime, timedelta
        
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(GenerationHistory).where(
                and_(
                    GenerationHistory.user_id == user_id,
                    GenerationHistory.created_at < cutoff_date,
                    GenerationHistory.deleted_at.is_(None),
                )
            )
        )
        records = result.scalars().all()
        count = len(records)
        
        for record in records:
            await self.db.delete(record)
        
        await self.db.flush()
        return count
