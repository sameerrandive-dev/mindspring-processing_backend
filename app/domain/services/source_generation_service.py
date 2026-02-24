"""Source generation service for generating summaries, quizzes, guides, and mindmaps from sources."""

import logging
import json
from typing import Optional, List, Dict, Any

from app.domain.models.source import Source
from app.domain.models.quiz import Quiz
from app.domain.models.study_guide import StudyGuide
from app.domain.repositories.notebook_repository import SourceRepository, ChunkRepository
from app.domain.repositories.quiz_repository import QuizRepository
from app.domain.repositories.study_guide_repository import StudyGuideRepository
from app.domain.repositories.history_repository import HistoryRepository
from app.domain.errors import NotFoundError, ValidationError
from app.domain.interfaces import ILLMClient

logger = logging.getLogger(__name__)


class SourceGenerationService:
    """
    Unified service for generating all artifacts from sources:
    - Summary
    - Quiz
    - Study Guide
    - Mindmap
    """
    
    def __init__(
        self,
        source_repo: SourceRepository,
        chunk_repo: ChunkRepository,
        quiz_repo: QuizRepository,
        study_guide_repo: StudyGuideRepository,
        history_repo: HistoryRepository,
        llm_client: ILLMClient,
    ):
        self.source_repo = source_repo
        self.chunk_repo = chunk_repo
        self.quiz_repo = quiz_repo
        self.study_guide_repo = study_guide_repo
        self.history_repo = history_repo
        self.llm_client = llm_client
    
    async def _get_source_content(self, source_id: str) -> str:
        """Helper: Get all chunk text from a source."""
        chunks = await self.chunk_repo.list_by_source(source_id)
        if not chunks:
            raise ValidationError("Source has no content. Please ensure the source has been processed and chunked.")
        return "\n\n".join([chunk.plain_text for chunk in chunks])

    async def _get_notebook_content(self, notebook_id: str) -> str:
        """Helper: Get all chunk text from all sources in a notebook."""
        chunks = await self.chunk_repo.list_by_notebook(notebook_id)
        if not chunks:
            summary = "Notebook has no sources or sources have no content. Please upload and process sources first."
            raise ValidationError(summary)
        return "\n\n".join([chunk.plain_text for chunk in chunks])
    
    # ========================================================================
    # Summary Generation
    # ========================================================================
    
    async def generate_summary(
        self,
        source_id: str,
        user_id: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> Dict[str, Any]:
        """
        Generate summary from source.
        
        Args:
            source_id: Source ID to summarize
            user_id: User generating the summary
            max_length: Maximum length of summary in characters
            style: Summary style ('concise', 'detailed', 'bullet_points')
            
        Returns:
            Dict with summary, source info, and history_id
        """
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found", resource_type="Source", resource_id=source_id)
        
        content = await self._get_source_content(source_id)
        
        summary = await self.llm_client.generate_summary(
            content=content,
            max_length=max_length,
            style=style,
        )
        
        # Store in generation_history
        history = await self.history_repo.create(
            user_id=user_id,
            history_type="summary",
            title=f"Summary: {source.title}",
            content=summary,
            content_preview=summary[:200] if summary else "",
            resource_id=source_id,
            notebook_id=source.notebook_id,
            metadata={"style": style, "max_length": max_length},
        )
        
        logger.info(f"Summary generated for source {source_id} by user {user_id}")
        return {
            "summary": summary,
            "source_id": source_id,
            "source_title": source.title,
            "history_id": history.id,
            "style": style,
        }

    async def generate_notebook_summary(
        self,
        notebook_id: str,
        user_id: str,
        max_length: int = 1000,
        style: str = "detailed",
    ) -> Dict[str, Any]:
        """Generate summary from all sources in a notebook."""
        content = await self._get_notebook_content(notebook_id)
        
        summary = await self.llm_client.generate_summary(
            content=content,
            max_length=max_length,
            style=style,
        )
        
        # Store in generation_history
        history = await self.history_repo.create(
            user_id=user_id,
            history_type="summary",
            title=f"Notebook Summary: {notebook_id}",
            content=summary,
            content_preview=summary[:200] if summary else "",
            resource_id=notebook_id,
            notebook_id=notebook_id,
            metadata={"style": style, "max_length": max_length, "scope": "notebook"},
        )
        
        logger.info(f"Summary generated for notebook {notebook_id} by user {user_id}")
        return {
            "summary": summary,
            "notebook_id": notebook_id,
            "history_id": history.id,
            "style": style,
        }
    
    # ========================================================================
    # Quiz Generation
    # ========================================================================
    
    async def generate_quiz(
        self,
        source_id: str,
        user_id: str,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "medium",
    ) -> Quiz:
        """
        Generate quiz from source.
        
        Args:
            source_id: Source ID to generate quiz from
            user_id: User generating the quiz
            topic: Quiz topic/title
            num_questions: Number of questions to generate
            difficulty: Question difficulty ('easy', 'medium', 'hard')
            
        Returns:
            Created Quiz object
        """
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found", resource_type="Source", resource_id=source_id)
        
        content = await self._get_source_content(source_id)
        
        # Generate questions using LLM
        questions = await self.llm_client.generate_quiz(
            content=content,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        
        # Create quiz
        quiz = await self.quiz_repo.create(
            notebook_id=source.notebook_id,
            user_id=user_id,
            topic=topic,
            questions_json=questions,
            model="gpt-4",  # TODO: Get from config
            metadata={"source_id": source_id, "difficulty": difficulty},
        )
        
        logger.info(f"Quiz generated for source {source_id} by user {user_id}")
        return quiz

    async def generate_notebook_quiz(
        self,
        notebook_id: str,
        user_id: str,
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium",
    ) -> Quiz:
        """Generate quiz from all sources in a notebook."""
        content = await self._get_notebook_content(notebook_id)
        
        # Generate questions using LLM
        questions = await self.llm_client.generate_quiz(
            content=content,
            num_questions=num_questions,
            difficulty=difficulty,
        )
        
        # Create quiz
        quiz = await self.quiz_repo.create(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            questions_json=questions,
            model="gpt-4",  # TODO: Get from config
            metadata={"scope": "notebook", "difficulty": difficulty},
        )
        
        logger.info(f"Quiz generated for notebook {notebook_id} by user {user_id}")
        return quiz
    
    # ========================================================================
    # Study Guide Generation
    # ========================================================================
    
    async def generate_study_guide(
        self,
        source_id: str,
        user_id: str,
        topic: Optional[str] = None,
        format: str = "structured",
    ) -> StudyGuide:
        """
        Generate study guide from source.
        
        Args:
            source_id: Source ID to generate guide from
            user_id: User generating the guide
            topic: Optional topic/title (defaults to source title)
            format: Guide format ('structured', 'outline', 'detailed')
            
        Returns:
            Created StudyGuide object
        """
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found", resource_type="Source", resource_id=source_id)
        
        content = await self._get_source_content(source_id)
        
        guide_content = await self.llm_client.generate_study_guide(
            content=content,
            topic=topic or source.title,
            format=format,
        )
        
        study_guide = await self.study_guide_repo.create(
            notebook_id=source.notebook_id,
            user_id=user_id,
            topic=topic or source.title,
            content=guide_content,
            model="gpt-4",  # TODO: Get from config
            metadata={"source_id": source_id, "format": format},
        )
        
        logger.info(f"Study guide generated for source {source_id} by user {user_id}")
        return study_guide

    async def generate_notebook_study_guide(
        self,
        notebook_id: str,
        user_id: str,
        topic: str,
        format: str = "structured",
    ) -> StudyGuide:
        """Generate study guide from all sources in a notebook."""
        content = await self._get_notebook_content(notebook_id)
        
        guide_content = await self.llm_client.generate_study_guide(
            content=content,
            topic=topic,
            format=format,
        )
        
        study_guide = await self.study_guide_repo.create(
            notebook_id=notebook_id,
            user_id=user_id,
            topic=topic,
            content=guide_content,
            model="gpt-4",  # TODO: Get from config
            metadata={"scope": "notebook", "format": format},
        )
        
        logger.info(f"Study guide generated for notebook {notebook_id} by user {user_id}")
        return study_guide
    
    # ========================================================================
    # Mindmap Generation
    # ========================================================================
    
    async def generate_mindmap(
        self,
        source_id: str,
        user_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate mindmap from source.
        
        Args:
            source_id: Source ID to generate mindmap from
            user_id: User generating the mindmap
            format: Output format ('json', 'markdown', 'mermaid')
            
        Returns:
            Dict with mindmap data, source info, and history_id
        """
        source = await self.source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found", resource_type="Source", resource_id=source_id)
        
        content = await self._get_source_content(source_id)
        
        mindmap = await self.llm_client.generate_mindmap(
            content=content,
            format=format,
        )
        
        # Store in generation_history
        mindmap_content = json.dumps(mindmap) if isinstance(mindmap, dict) else str(mindmap)
        history = await self.history_repo.create(
            user_id=user_id,
            history_type="mindmap",
            title=f"Mindmap: {source.title}",
            content=mindmap_content,
            content_preview=mindmap_content[:200] if mindmap_content else "",
            resource_id=source_id,
            notebook_id=source.notebook_id,
            metadata={"format": format},
        )
        
        logger.info(f"Mindmap generated for source {source_id} by user {user_id}")
        return {
            "mindmap": mindmap,
            "source_id": source_id,
            "source_title": source.title,
            "format": format,
            "history_id": history.id,
        }

    async def generate_notebook_mindmap(
        self,
        notebook_id: str,
        user_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """Generate mindmap from all sources in a notebook."""
        content = await self._get_notebook_content(notebook_id)
        
        mindmap = await self.llm_client.generate_mindmap(
            content=content,
            format=format,
        )
        
        # Store in generation_history
        mindmap_content = json.dumps(mindmap) if isinstance(mindmap, dict) else str(mindmap)
        history = await self.history_repo.create(
            user_id=user_id,
            history_type="mindmap",
            title=f"Notebook Mindmap: {notebook_id}",
            content=mindmap_content,
            content_preview=mindmap_content[:200] if mindmap_content else "",
            resource_id=notebook_id,
            notebook_id=notebook_id,
            metadata={"format": format, "scope": "notebook"},
        )
        
        logger.info(f"Mindmap generated for notebook {notebook_id} by user {user_id}")
        return {
            "mindmap": mindmap,
            "notebook_id": notebook_id,
            "format": format,
            "history_id": history.id,
        }

    # ========================================================================
    # Text-to-Mindmap (no source required)
    # ========================================================================

    async def generate_mindmap_from_text(
        self,
        text: str,
        user_id: str,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Generate a mindmap directly from freeform text — no source needed.
        Satisfies the 'Text-to-Mindmap' feature in FEATURES.md.

        Args:
            text: Raw concept or description to map
            user_id: User requesting the mindmap
            format: Output format ('json', 'markdown', 'mermaid')

        Returns:
            Dict with mindmap, format, and history_id
        """
        if not text or not text.strip():
            raise ValidationError("text must not be empty")

        mindmap = await self.llm_client.generate_mindmap(
            content=text,
            format=format,
        )

        mindmap_content = json.dumps(mindmap) if isinstance(mindmap, dict) else str(mindmap)
        history = await self.history_repo.create(
            user_id=user_id,
            history_type="mindmap",
            title="Text-to-Mindmap",
            content=mindmap_content,
            content_preview=mindmap_content[:200] if mindmap_content else "",
            resource_id=None,
            notebook_id=None,
            metadata={"format": format, "source": "text_prompt"},
        )

        logger.info(f"Text-to-Mindmap generated for user {user_id}")
        return {
            "mindmap": mindmap,
            "source_id": None,
            "source_title": None,
            "format": format,
            "history_id": history.id,
        }

