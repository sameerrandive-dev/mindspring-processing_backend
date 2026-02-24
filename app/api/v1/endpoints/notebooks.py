"""
Refactored notebook endpoints using service layer.

Endpoints are thin HTTP handlers that:
- Validate requests using Pydantic schemas
- Get services from the DI container
- Call services for business logic
- Convert DomainErrors to HTTP responses
- Return DTOs (not domain models)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.api.deps import get_current_user, get_service_container
from app.domain.models.user import User
from app.domain.schemas.notebook import (
    NotebookCreate,
    NotebookUpdate,
    NotebookResponse,
    NotebookListResponse,
    NotebookSummaryResponse,
    NotebookMindmapResponse,
    NotebookQuizGenerateRequest,
    NotebookStudyGuideGenerateRequest,
)
from app.domain.errors import DomainError
from app.infrastructure.container import ServiceContainer
from app.infrastructure.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# DEPENDENCY PROVIDERS
# ============================================================================

async def get_notebook_service(container: ServiceContainer = Depends(get_service_container)):
    """Get NotebookService from container."""
    return container.get_notebook_service()


async def get_source_generation_service(container: ServiceContainer = Depends(get_service_container)):
    """Get SourceGenerationService from container."""
    return container.get_source_generation_service()


# ============================================================================
# ENDPOINTS - THIN HTTP HANDLERS
# ============================================================================

@router.post("/", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    notebook_in: NotebookCreate,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new notebook."""
    logger.info(f"Creating notebook for user: {current_user.id}")
    notebook = await service.create_notebook(
        user_id=current_user.id,
        title=notebook_in.title,
        description=notebook_in.description or "",
        language=notebook_in.language,
        tone=notebook_in.tone,
        max_context_tokens=notebook_in.max_context_tokens,
    )
    await db.commit()
    await db.refresh(notebook)
    logger.info(f"Notebook created: {notebook.id}")
    return NotebookResponse.model_validate(notebook)


@router.get("/", response_model=NotebookListResponse)
async def list_notebooks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
):
    """List all notebooks for the current user."""
    notebooks = await service.list_user_notebooks(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return NotebookListResponse(
        notebooks=[NotebookResponse.model_validate(nb) for nb in notebooks],
        total=len(notebooks),
    )


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
):
    """Get notebook details by ID."""
    notebook = await service.get_notebook(
        notebook_id=notebook_id,
        user_id=current_user.id,
    )
    return NotebookResponse.model_validate(notebook)


@router.put("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a notebook."""
    # Build update dict from provided fields
    updates = {}
    if notebook_in.title is not None:
        updates["title"] = notebook_in.title
    if notebook_in.description is not None:
        updates["description"] = notebook_in.description
    if notebook_in.language is not None:
        updates["language"] = notebook_in.language
    if notebook_in.tone is not None:
        updates["tone"] = notebook_in.tone
    if notebook_in.max_context_tokens is not None:
        updates["max_context_tokens"] = notebook_in.max_context_tokens
    
    notebook = await service.update_notebook(
        notebook_id=notebook_id,
        user_id=current_user.id,
        **updates,
    )
    await db.commit()
    await db.refresh(notebook)
    logger.info(f"Notebook updated: {notebook_id}")
    return NotebookResponse.model_validate(notebook)


@router.delete("/{notebook_id}", status_code=status.HTTP_200_OK)
async def delete_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Soft delete a notebook by ID (sets deleted_at timestamp)."""
    success = await service.delete_notebook(
        notebook_id=notebook_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found"
        )
    await db.commit()
    logger.info(f"Notebook soft deleted: {notebook_id}")
    return {"message": "Notebook deleted successfully"}


@router.post("/{notebook_id}/restore", status_code=status.HTTP_200_OK)
async def restore_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    service=Depends(get_notebook_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Restore a soft-deleted notebook."""
    success = await service.restore_notebook(
        notebook_id=notebook_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found or already restored"
        )
    await db.commit()
    logger.info(f"Notebook restored: {notebook_id}")
    return {"message": "Notebook restored successfully"}


# ============================================================================
# NOTEBOOK GENERATION ENDPOINTS (NotebookLM-like features)
# ============================================================================

@router.post("/{notebook_id}/generate/summary", response_model=NotebookSummaryResponse)
async def generate_notebook_summary(
    notebook_id: str,
    max_length: int = 1000,
    style: str = "detailed",
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate summary from all sources in the notebook."""
    result = await service.generate_notebook_summary(
        notebook_id=notebook_id,
        user_id=current_user.id,
        max_length=max_length,
        style=style,
    )
    await db.commit()
    return NotebookSummaryResponse(**result)


@router.post("/{notebook_id}/generate/quiz")
async def generate_notebook_quiz(
    notebook_id: str,
    request: NotebookQuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate quiz from all sources in the notebook."""
    quiz = await service.generate_notebook_quiz(
        notebook_id=notebook_id,
        user_id=current_user.id,
        topic=request.topic,
        num_questions=request.num_questions,
        difficulty=request.difficulty,
    )
    await db.commit()
    await db.refresh(quiz)
    return {
        "id": quiz.id,
        "notebook_id": quiz.notebook_id,
        "topic": quiz.topic,
        "questions": quiz.questions,
        "model": quiz.model,
        "version": quiz.version,
        "created_at": quiz.created_at.isoformat(),
    }


@router.post("/{notebook_id}/generate/guide")
async def generate_notebook_study_guide(
    notebook_id: str,
    request: NotebookStudyGuideGenerateRequest,
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate study guide from all sources in the notebook."""
    guide = await service.generate_notebook_study_guide(
        notebook_id=notebook_id,
        user_id=current_user.id,
        topic=request.topic,
        format=request.format,
    )
    await db.commit()
    await db.refresh(guide)
    return {
        "id": guide.id,
        "notebook_id": guide.notebook_id,
        "topic": guide.topic,
        "content": guide.content,
        "model": guide.model,
        "version": guide.version,
        "created_at": guide.created_at.isoformat(),
    }


@router.post("/{notebook_id}/generate/mindmap", response_model=NotebookMindmapResponse)
async def generate_notebook_mindmap(
    notebook_id: str,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate mindmap from all sources in the notebook."""
    result = await service.generate_notebook_mindmap(
        notebook_id=notebook_id,
        user_id=current_user.id,
        format=format,
    )
    await db.commit()
    return NotebookMindmapResponse(**result)
