"""
Source endpoints for managing sources and generating artifacts.

Endpoints:
- List sources in notebook
- Upload source file (with async processing)
- Generate summary from source
- Generate quiz from source
- Generate study guide from source
- Generate mindmap from source
- Create conversation based on source
"""

import logging
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator

from app.api.deps import get_current_user, get_service_container
from app.domain.models.user import User
from app.domain.errors import DomainError
from app.infrastructure.container import ServiceContainer
from app.infrastructure.database.session import get_db_session, AsyncSessionFactory
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils import extract_text_from_url, process_text_content, get_file_type

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class SourceCreate(BaseModel):
    source_type: str
    title: str
    original_url: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[dict] = None


class SourceResponse(BaseModel):
    id: str
    notebook_id: str
    type: str
    title: str
    original_url: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    created_at: str
    
    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        """Convert datetime to ISO format string."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v
    
    class Config:
        from_attributes = True


class SummaryResponse(BaseModel):
    summary: str
    source_id: str
    source_title: str
    history_id: str
    style: str


class MindmapResponse(BaseModel):
    mindmap: dict
    source_id: Optional[str] = None
    source_title: Optional[str] = None
    format: str
    history_id: str


class TextMindmapRequest(BaseModel):
    text: str
    format: str = "json"

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"json", "mermaid", "markdown"}
        if v.lower() not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v.lower()


ALLOWED_QUESTION_COUNTS = {10, 20, 30, 40, 50}
ALLOWED_DIFFICULTIES = {"novice", "intermediate", "master", "easy", "medium", "hard"}


class QuizGenerateRequest(BaseModel):
    topic: str
    num_questions: int = 10
    difficulty: str = "intermediate"

    @field_validator("num_questions")
    @classmethod
    def validate_num_questions(cls, v: int) -> int:
        if v not in ALLOWED_QUESTION_COUNTS:
            raise ValueError(
                f"num_questions must be one of {sorted(ALLOWED_QUESTION_COUNTS)}"
            )
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v.lower() not in ALLOWED_DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {ALLOWED_DIFFICULTIES}"
            )
        return v.lower()


class StudyGuideGenerateRequest(BaseModel):
    topic: Optional[str] = None
    format: str = "structured"


# ============================================================================
# DEPENDENCY PROVIDERS
# ============================================================================

async def get_source_generation_service(container: ServiceContainer = Depends(get_service_container)):
    """Get SourceGenerationService from container."""
    return container.get_source_generation_service()


async def get_notebook_service(container: ServiceContainer = Depends(get_service_container)):
    """Get NotebookService from container."""
    return container.get_notebook_service()


async def get_chat_service(container: ServiceContainer = Depends(get_service_container)):
    """Get ChatService from container."""
    return container.get_chat_service()


async def get_source_processing_service(container: ServiceContainer = Depends(get_service_container)):
    """Get SourceProcessingService from container."""
    return container.get_source_processing_service()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/notebooks/{notebook_id}/sources", status_code=status.HTTP_201_CREATED)
async def add_source_to_notebook(
    notebook_id: str,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),  # NEW: Bulk upload support
    url: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    notebook_service = Depends(get_notebook_service),
    processing_service = Depends(get_source_processing_service),
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Add source(s) to a notebook (multi-file, single file, URL, or text).
    
    Accepts FormData with:
    - files: List[UploadFile] (NEW: support for multiple files at once)
    - file: UploadFile (optional, for backward compatibility)
    - url: str (optional)
    - text: str (optional)
    - title: str (optional)
    """
    # 1. Standardize sources list
    upload_list = []
    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)
        
    # Validate that at least one source type is provided
    if not upload_list and not url and not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either files, url, or text must be provided"
        )
    
    results = []
    
    try:
        # Handle bulk/single file uploads
        if upload_list:
            for upload in upload_list:
                source_type = get_file_type(upload.filename or "", upload.content_type or "")
                source_title = upload.filename or "Untitled Document"
                
                # Metadata for this source
                metadata: dict = {
                    "uploadedBy": current_user.id,
                    "fileSize": upload.size,
                    "mimeType": upload.content_type,
                }
                
                # Validate type and size
                allowed_types = ["application/pdf", "text/plain", "text/markdown"]
                file_ext = (upload.filename or "").split('.')[-1].lower() if '.' in (upload.filename or "") else ''
                
                if upload.content_type not in allowed_types and file_ext not in ['pdf', 'txt', 'md']:
                    logger.warning(f"Skipping file {upload.filename}: Unsupported type")
                    continue # Skip unsupported files in a bulk batch

                if upload.size > 50 * 1024 * 1024:
                    logger.warning(f"Skipping file {upload.filename}: Exceeds 50MB")
                    continue

                # Read and storage
                file_content = await upload.read()
                source_id = str(uuid.uuid4())
                timestamp = int(time.time() * 1000)
                storage_key = f"{current_user.id}/notebooks/{notebook_id}/sources/{timestamp}-{upload.filename}"
                
                storage_provider = container.storage_provider
                stored_key = await storage_provider.store(
                    key=storage_key,
                    content=file_content,
                    metadata={
                        "filename": upload.filename,
                        "user_id": str(current_user.id),
                        "notebook_id": notebook_id,
                    },
                )
                
                # Create record
                from app.domain.models.source import Source
                source = Source(
                    id=source_id,
                    notebook_id=notebook_id,
                    type=source_type,
                    title=source_title,
                    file_path=stored_key,
                    metadata_=metadata,
                    status="processing",
                )
                db.add(source)
                
                # Background task closure
                async def process_task(sid=source_id, skey=storage_key):
                    async with AsyncSessionFactory() as bg_db:
                        try:
                            bg_container = ServiceContainer(db=bg_db)
                            svc = bg_container.get_source_processing_service()
                            await svc.process_source_file(source_id=sid, storage_key=skey)
                            await bg_db.commit()
                        except Exception as e:
                            logger.error(f"Bulk source processing error for {sid}: {e}")
                
                background_tasks.add_task(process_task)
                results.append({"id": source_id, "title": source_title, "status": "processing"})

            await db.commit()
            
            return {
                "success": True,
                "data": results,
                "meta": {"count": len(results), "timestamp": datetime.utcnow().isoformat()},
            }
        
        # Handle URL source
        elif url:
            source_type = "url"
            source_title = url
            
            try:
                url_content = await extract_text_from_url(url)
                content = url_content["text"]
                if url_content.get("title"):
                    source_title = url_content["title"]
            except ValueError as e:
                logger.error(f"URL extraction failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"URL extraction error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to extract content from URL: {str(e)}"
                )
        
        # Handle text source
        elif text:
            source_type = "text"
            source_title = title or "Text Document"
            try:
                content = process_text_content(text)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # Validate content
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content extracted from source"
            )
        
        # Create source record for URL/text sources
        from app.domain.models.source import Source
        source_id = str(uuid.uuid4())
        source = Source(
            id=source_id,
            notebook_id=notebook_id,
            type=source_type,
            title=source_title,
            original_url=url if url else None,
            file_path=None,
            metadata_=metadata,
            status="processing",
        )
        db.add(source)
        await db.flush()
        await db.commit()
        await db.refresh(source)
        
        # Process content in background (chunk and embed)
        async def process_content_in_background():
            """Process source content in background."""
            async with AsyncSessionFactory() as bg_db:
                try:
                    bg_container = ServiceContainer(db=bg_db)
                    rag_ingest_service = bg_container.get_rag_ingest_service()
                    source_repo = bg_container.get_source_repository()
                    
                    # Chunk and generate embeddings
                    chunks = await rag_ingest_service.ingest_document(
                        source_id=source_id,
                        notebook_id=notebook_id,
                        document_text=content,
                        metadata={
                            "title": source_title,
                            "type": source_type,
                            **metadata,
                        },
                    )
                    
                    # Update source status to completed
                    await source_repo.update(source_id, status="completed")
                    await bg_db.commit()
                    logger.info(f"Source {source_id} processing completed successfully")
                except Exception as e:
                    await bg_db.rollback()
                    logger.error(f"Background processing failed for source {source_id}: {e}", exc_info=True)
                    try:
                        await source_repo.update(source_id, status="failed")
                        await bg_db.commit()
                    except:
                        pass
        
        background_tasks.add_task(process_content_in_background)
        
        logger.info(f"Source {source_id} created and background processing queued")
        
        # Return Next.js format response
        return {
            "success": True,
            "data": {
                "sourceId": source.id,
                "sourceTitle": source.title,
                "status": source.status,
                "message": "Source uploaded successfully. Processing in background...",
            },
            "meta": {
                "version": "v1",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        
    except HTTPException:
        await db.rollback()
        raise
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in add_source_to_notebook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notebooks/{notebook_id}/sources", response_model=List[SourceResponse])
async def list_notebook_sources(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    notebook_service = Depends(get_notebook_service),
):
    """List all sources in a notebook."""
    try:
        sources = await notebook_service.get_notebook_sources(
            notebook_id=notebook_id,
            user_id=current_user.id,
        )
        return [SourceResponse.model_validate(s) for s in sources]
    except DomainError as e:
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in list_notebook_sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sources/{source_id}/generate/summary", response_model=SummaryResponse)
async def generate_summary(
    source_id: str,
    max_length: int = 500,
    style: str = "concise",
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate summary from source."""
    try:
        result = await service.generate_summary(
            source_id=source_id,
            user_id=current_user.id,
            max_length=max_length,
            style=style,
        )
        await db.commit()
        return SummaryResponse(**result)
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in generate_summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sources/{source_id}/generate/quiz")
async def generate_quiz(
    source_id: str,
    request: QuizGenerateRequest,
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate quiz from source."""
    try:
        quiz = await service.generate_quiz(
            source_id=source_id,
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
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in generate_quiz: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sources/{source_id}/generate/guide")
async def generate_study_guide(
    source_id: str,
    request: StudyGuideGenerateRequest,
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate study guide from source."""
    try:
        guide = await service.generate_study_guide(
            source_id=source_id,
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
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in generate_study_guide: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sources/{source_id}/generate/mindmap", response_model=MindmapResponse)
async def generate_mindmap(
    source_id: str,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate mindmap from source."""
    try:
        result = await service.generate_mindmap(
            source_id=source_id,
            user_id=current_user.id,
            format=format,
        )
        await db.commit()
        return MindmapResponse(**result)
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in generate_mindmap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sources/{source_id}/conversations")
async def create_source_conversation(
    source_id: str,
    title: Optional[str] = None,
    mode: str = "chat",
    current_user: User = Depends(get_current_user),
    chat_service = Depends(get_chat_service),
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db_session),
):
    """Create conversation based on source."""
    try:
        # Get source to get notebook_id
        source_repo = container.get_source_repository()
        source = await source_repo.get_by_id(source_id)
        
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source {source_id} not found"
            )
        
        conversation = await chat_service.create_conversation(
            notebook_id=source.notebook_id,
            user_id=current_user.id,
            title=title or f"Chat about {source.title}",
            mode=mode,
            source_id=source_id,
        )
        await db.commit()
        await db.refresh(conversation)
        return {
            "id": conversation.id,
            "notebook_id": conversation.notebook_id,
            "source_id": conversation.source_id,
            "title": conversation.title,
            "mode": conversation.mode,
            "created_at": conversation.created_at.isoformat(),
        }
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in create_source_conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Gap 4: Text-to-Mindmap (no source required)
# ============================================================================

@router.post("/mindmap/generate", response_model=MindmapResponse)
async def generate_mindmap_from_text(
    request: TextMindmapRequest,
    current_user: User = Depends(get_current_user),
    service = Depends(get_source_generation_service),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate a mindmap from freeform text — no source needed.
    
    Send any concept or description and receive a structured mindmap
    in JSON, Mermaid, or Markdown format.
    """
    try:
        result = await service.generate_mindmap_from_text(
            text=request.text,
            user_id=current_user.id,
            format=request.format,
        )
        await db.commit()
        return MindmapResponse(**result)
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in generate_mindmap_from_text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Gap 5: Interactive Node Threading — create a conversation from a mindmap node
# ============================================================================

@router.post("/mindmap-node/conversations")
async def create_node_conversation(
    notebook_id: str,
    node_id: str,
    node_label: str,
    history_id: str,
    title: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    chat_service = Depends(get_chat_service),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a focused conversation thread anchored to a specific mindmap node.

    The node label becomes the initial topic context and the conversation
    is set to 'tutor' mode for in-depth learning about that concept.
    The history_id links this thread back to the parent mindmap.
    """
    try:
        conversation = await chat_service.create_conversation(
            notebook_id=notebook_id,
            user_id=current_user.id,
            title=title or f"Exploring: {node_label}",
            mode="tutor",
            source_id=None,
        )
        await db.commit()
        await db.refresh(conversation)

        return {
            "id": conversation.id,
            "notebook_id": conversation.notebook_id,
            "node_id": node_id,
            "node_label": node_label,
            "mindmap_history_id": history_id,
            "mode": conversation.mode,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
        }
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in create_node_conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
