"""Quiz service for quiz management and generation."""

import logging
from typing import Optional, List

from app.domain.models.quiz import Quiz
from app.domain.repositories.quiz_repository import QuizRepository
from app.domain.errors import NotFoundError, ForbiddenError
from app.domain.interfaces import ILLMClient

logger = logging.getLogger(__name__)


class QuizService:
    """
    Quiz service for managing quizzes and question generation.
    
    Responsibilities:
    - Create/read/update/delete quizzes
    - Generate quiz questions from content
    - Authorization checks
    - Version management
    """
    
    def __init__(
        self,
        quiz_repo: QuizRepository,
        llm_client: ILLMClient,
    ):
        self.quiz_repo = quiz_repo
        self.llm_client = llm_client
    
    async def create_quiz(
        self,
        notebook_id: int,
        user_id: int,
        topic: str,
        questions_json: list,
        model: str = "gpt-4",
        metadata: Optional[dict] = None,
    ) -> Quiz:
        """Create a new quiz."""
        quiz = await self.quiz_repo.create(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            questions_json=questions_json,
            model=model,
            version=1,
            metadata=metadata,
        )
        
        logger.info(f"Quiz created: {quiz.id} in notebook: {notebook_id}")
        return quiz
    
    async def get_quiz(self, quiz_id: int, user_id: int) -> Quiz:
        """Get quiz with authorization."""
        quiz = await self.quiz_repo.get_by_id_and_user(quiz_id, user_id)
        if not quiz:
            raise NotFoundError(
                f"Quiz {quiz_id} not found or user not authorized",
                resource_type="Quiz",
                resource_id=quiz_id,
            )
        return quiz
    
    async def list_notebook_quizzes(
        self,
        notebook_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Quiz]:
        """List quizzes in a notebook."""
        return await self.quiz_repo.list_by_notebook(notebook_id, skip=skip, limit=limit)
    
    async def update_quiz(
        self,
        quiz_id: int,
        user_id: int,
        questions_json: Optional[list] = None,
        **updates,
    ) -> Quiz:
        """Update quiz (increments version if questions change)."""
        quiz = await self.get_quiz(quiz_id, user_id)
        
        # Allow updating questions and topic
        allowed_fields = {"topic", "model"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if questions_json is not None:
            filtered_updates["questions_json"] = questions_json
        
        if filtered_updates:
            quiz = await self.quiz_repo.update(quiz_id, **filtered_updates)
            logger.info(f"Quiz updated: {quiz_id} (version {quiz.version})")
        
        return quiz
    
    async def delete_quiz(self, quiz_id: int, user_id: int) -> bool:
        """Delete a quiz."""
        quiz = await self.get_quiz(quiz_id, user_id)
        
        success = await self.quiz_repo.delete(quiz_id)
        if success:
            logger.info(f"Quiz deleted: {quiz_id}")
        
        return success
    
    async def generate_quiz_questions(
        self,
        content: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> list:
        """Generate quiz questions from content using LLM."""
        questions = await self.llm_client.generate_quiz(
            content=content,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        
        logger.info(f"Quiz questions generated: {len(questions)} questions")
        return questions
