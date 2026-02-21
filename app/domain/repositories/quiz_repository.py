"""Quiz repository for managing quizzes."""

from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.quiz import Quiz
from app.domain.errors import NotFoundError


class QuizRepository:
    """Repository for Quiz entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        notebook_id: str,
        user_id: str,
        topic: str,
        questions_json: list,
        model: str = "gpt-4",
        version: int = 1,
        metadata: Optional[dict] = None,
    ) -> Quiz:
        """Create a new quiz."""
        quiz = Quiz(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            questions=questions_json,  # Note: model uses 'questions' not 'questions_json'
            model=model,
            version=version,
            metadata_=metadata or {},
        )
        self.db.add(quiz)
        await self.db.flush()
        return quiz
    
    async def get_by_id(self, quiz_id: str) -> Optional[Quiz]:
        """Get quiz by ID."""
        result = await self.db.execute(select(Quiz).where(Quiz.id == quiz_id))
        return result.scalar_one_or_none()
    
    async def get_by_id_and_user(self, quiz_id: str, user_id: str) -> Optional[Quiz]:
        """Get quiz by ID checking user ownership."""
        result = await self.db.execute(
            select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_notebook(
        self,
        notebook_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Quiz]:
        """List quizzes in a notebook."""
        result = await self.db.execute(
            select(Quiz)
            .where(Quiz.notebook_id == notebook_id)
            .where(Quiz.deleted_at.is_(None))  # Exclude soft-deleted
            .offset(skip)
            .limit(limit)
            .order_by(desc(Quiz.created_at))
        )
        return result.scalars().all()
    
    async def update(self, quiz_id: str, **updates) -> Quiz:
        """Update quiz fields."""
        quiz = await self.get_by_id(quiz_id)
        if not quiz:
            raise NotFoundError(f"Quiz {quiz_id} not found", resource_type="Quiz", resource_id=quiz_id)
        
        # Increment version if questions are being updated
        if "questions" in updates or "questions_json" in updates:
            updates["version"] = (quiz.version or 1) + 1
            # Map questions_json to questions if needed
            if "questions_json" in updates:
                updates["questions"] = updates.pop("questions_json")
        
        for key, value in updates.items():
            if hasattr(quiz, key) and key != "id" and key != "deleted_at":
                setattr(quiz, key, value)
        
        await self.db.flush()
        return quiz
    
    async def delete(self, quiz_id: str) -> bool:
        """Soft delete quiz."""
        quiz = await self.get_by_id(quiz_id)
        if not quiz:
            return False
        
        # Soft delete: set deleted_at timestamp
        from datetime import datetime, timezone
        quiz.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
