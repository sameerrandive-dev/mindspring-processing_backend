"""Notebook service for managing notebooks and documents."""

import logging
from typing import Optional, List

from app.domain.models.notebook import Notebook
from app.domain.models.source import Source
from app.domain.repositories.notebook_repository import (
    NotebookRepository,
    SourceRepository,
    ChunkRepository,
)
from app.domain.repositories.conversation_repository import ConversationRepository
from app.domain.errors import NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)


class NotebookService:
    """
    Notebook service managing notebook lifecycle and associated resources.
    
    Responsibilities:
    - Create/read/update/delete notebooks
    - Manage sources within notebooks
    - Authorization checks
    - Cascading deletes
    """
    
    def __init__(
        self,
        notebook_repo: NotebookRepository,
        source_repo: SourceRepository,
        chunk_repo: ChunkRepository,
        conversation_repo: ConversationRepository,
        max_notebooks_per_user: int = 50,
    ):
        self.notebook_repo = notebook_repo
        self.source_repo = source_repo
        self.chunk_repo = chunk_repo
        self.conversation_repo = conversation_repo
        self.max_notebooks_per_user = max_notebooks_per_user
    
    async def create_notebook(
        self,
        user_id: str,
        title: str,
        description: str = "",
        language: str = "en",
        tone: str = "professional",
        max_context_tokens: int = 4096,
    ) -> Notebook:
        """
        Create a new notebook.
        
        Raises:
            ForbiddenError: user has reached notebook limit
        """
        # Check notebook limit
        user_notebooks = await self.notebook_repo.list_by_owner(user_id, limit=1000)
        if len(user_notebooks) >= self.max_notebooks_per_user:
            raise ForbiddenError(
                f"Notebook limit ({self.max_notebooks_per_user}) reached for user"
            )
        
        notebook = await self.notebook_repo.create(
            owner_id=user_id,
            title=title,
            description=description,
            language=language,
            tone=tone,
            max_context_tokens=max_context_tokens,
        )
        
        logger.info(f"Notebook created: {notebook.id} by user: {user_id}")
        return notebook
    
    async def get_notebook(self, notebook_id: str, user_id: str) -> Notebook:
        """
        Get notebook with authorization check.
        
        Raises:
            NotFoundError: notebook not found or user not owner
        """
        notebook = await self.notebook_repo.get_by_id_and_owner(notebook_id, user_id)
        if not notebook:
            raise NotFoundError(
                f"Notebook {notebook_id} not found or user not authorized",
                resource_type="Notebook",
                resource_id=notebook_id,
            )
        return notebook
    
    async def update_notebook(
        self,
        notebook_id: str,
        user_id: str,
        **updates,
    ) -> Notebook:
        """Update notebook with authorization check."""
        notebook = await self.get_notebook(notebook_id, user_id)
        
        # Update allowed fields only
        allowed_fields = {"title", "description", "language", "tone", "max_context_tokens"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if filtered_updates:
            notebook = await self.notebook_repo.update(notebook_id, **filtered_updates)
            logger.info(f"Notebook updated: {notebook_id}")
        
        return notebook
    
    async def delete_notebook(self, notebook_id: str, user_id: str) -> bool:
        """Soft delete notebook (sets deleted_at timestamp)."""
        notebook = await self.get_notebook(notebook_id, user_id)
        
        # Soft delete: sets deleted_at timestamp
        # The notebook and its data remain in the database but are hidden from queries
        success = await self.notebook_repo.delete(notebook_id)
        
        if success:
            logger.info(f"Notebook soft deleted: {notebook_id}")
        
        return success
    
    async def restore_notebook(self, notebook_id: str, user_id: str) -> bool:
        """Restore a soft-deleted notebook."""
        # Check if notebook exists (including deleted ones) and user owns it
        notebook = await self.notebook_repo.get_by_id_and_owner(notebook_id, user_id, include_deleted=True)
        if not notebook:
            raise NotFoundError(
                f"Notebook {notebook_id} not found or user not authorized",
                resource_type="Notebook",
                resource_id=notebook_id,
            )
        
        if notebook.deleted_at is None:
            # Already restored or never deleted
            return True
        
        success = await self.notebook_repo.restore(notebook_id)
        
        if success:
            logger.info(f"Notebook restored: {notebook_id}")
        
        return success
    
    async def list_user_notebooks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Notebook]:
        """List all notebooks for a user."""
        return await self.notebook_repo.list_by_owner(user_id, skip=skip, limit=limit)
    
    # ========================================================================
    # Source Management
    # ========================================================================
    
    async def add_source_to_notebook(
        self,
        notebook_id: str,
        user_id: str,
        source_type: str,
        title: str,
        original_url: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Source:
        """Add a source (document/article/URL) to a notebook."""
        # Verify user owns notebook
        await self.get_notebook(notebook_id, user_id)
        
        source = await self.source_repo.create(
            notebook_id=notebook_id,
            source_type=source_type,
            title=title,
            original_url=original_url,
            file_path=file_path,
            metadata=metadata,
            status="active",
        )
        
        logger.info(f"Source added to notebook: {notebook_id}, source: {source.id}")
        return source
    
    async def get_notebook_sources(self, notebook_id: str, user_id: str) -> List[Source]:
        """Get all sources in a notebook."""
        # Verify user owns notebook
        await self.get_notebook(notebook_id, user_id)
        
        return await self.source_repo.list_by_notebook(notebook_id)
    
    async def delete_source(self, notebook_id: str, source_id: str, user_id: str) -> bool:
        """Delete a source from a notebook."""
        # Verify user owns notebook
        await self.get_notebook(notebook_id, user_id)
        
        source = await self.source_repo.get_by_id(source_id)
        if not source or source.notebook_id != notebook_id:
            raise NotFoundError(
                f"Source {source_id} not found in notebook",
                resource_type="Source",
                resource_id=source_id,
            )
        
        success = await self.source_repo.delete(source_id)
        if success:
            logger.info(f"Source deleted: {source_id}")
        
        return success
