"""Study guide repository for managing study guides."""

from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.study_guide import StudyGuide
from app.domain.errors import NotFoundError


class StudyGuideRepository:
    """Repository for StudyGuide entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        notebook_id: str,
        user_id: str,
        topic: str,
        content: str,
        model: Optional[str] = None,
        version: int = 1,
        metadata: Optional[dict] = None,
    ) -> StudyGuide:
        """Create a new study guide."""
        study_guide = StudyGuide(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            content=content,
            model=model,
            version=version,
            metadata_=metadata or {},
        )
        self.db.add(study_guide)
        await self.db.flush()
        return study_guide
    
    async def get_by_id(self, guide_id: str) -> Optional[StudyGuide]:
        """Get study guide by ID."""
        result = await self.db.execute(select(StudyGuide).where(StudyGuide.id == guide_id))
        return result.scalar_one_or_none()
    
    async def get_by_id_and_user(self, guide_id: str, user_id: str) -> Optional[StudyGuide]:
        """Get study guide by ID checking user ownership."""
        result = await self.db.execute(
            select(StudyGuide).where(StudyGuide.id == guide_id, StudyGuide.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_notebook(
        self,
        notebook_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudyGuide]:
        """List study guides in a notebook."""
        result = await self.db.execute(
            select(StudyGuide)
            .where(StudyGuide.notebook_id == notebook_id)
            .where(StudyGuide.deleted_at.is_(None))  # Exclude soft-deleted
            .offset(skip)
            .limit(limit)
            .order_by(desc(StudyGuide.created_at))
        )
        return result.scalars().all()
    
    async def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StudyGuide]:
        """List study guides for a user."""
        result = await self.db.execute(
            select(StudyGuide)
            .where(StudyGuide.user_id == user_id)
            .where(StudyGuide.deleted_at.is_(None))  # Exclude soft-deleted
            .offset(skip)
            .limit(limit)
            .order_by(desc(StudyGuide.created_at))
        )
        return result.scalars().all()
    
    async def update(self, guide_id: str, **updates) -> StudyGuide:
        """Update study guide fields."""
        guide = await self.get_by_id(guide_id)
        if not guide:
            raise NotFoundError(f"Study guide {guide_id} not found", resource_type="StudyGuide", resource_id=guide_id)
        
        # Increment version if content is being updated
        if "content" in updates:
            updates["version"] = (guide.version or 1) + 1
        
        for key, value in updates.items():
            if hasattr(guide, key) and key != "id" and key != "deleted_at":
                setattr(guide, key, value)
        
        await self.db.flush()
        return guide
    
    async def delete(self, guide_id: str) -> bool:
        """Soft delete study guide."""
        guide = await self.get_by_id(guide_id)
        if not guide:
            return False
        
        # Soft delete: set deleted_at timestamp
        from datetime import datetime, timezone
        guide.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
