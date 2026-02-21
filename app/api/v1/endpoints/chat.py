from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
import json
import logging

from app.core.security import get_current_user
from app.domain.models.user import User
from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.infrastructure.database.session import get_db_session
from app.infrastructure.container import ServiceContainer
from app.api.deps import get_service_container
from app.domain.errors import DomainError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/conversations")
async def create_conversation(
    notebook_id: str,
    title: Optional[str] = None,
    mode: Optional[str] = "chat",
    source_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new conversation."""
    conversation_id = str(uuid4())
    conversation = Conversation(
        id=conversation_id,
        notebook_id=notebook_id,
        user_id=current_user.id,
        title=title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        mode=mode,
        source_id=source_id
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return {
        "id": conversation.id,
        "notebook_id": conversation.notebook_id,
        "title": conversation.title,
        "mode": conversation.mode,
        "created_at": conversation.created_at.isoformat()
    }


@router.get("/conversations")
async def list_conversations(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """List all conversations for a notebook."""
    query = select(Conversation).where(
        Conversation.notebook_id == notebook_id,
        Conversation.user_id == current_user.id
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    return {
        "conversations": [
            {
                "id": conv.id,
                "title": conv.title,
                "mode": conv.mode,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ],
        "total": len(conversations)
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get conversation details by ID."""
    query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages for this conversation
    msg_query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()
    
    return {
        "id": conversation.id,
        "notebook_id": conversation.notebook_id,
        "title": conversation.title,
        "mode": conversation.mode,
        "source_id": conversation.source_id,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "chunk_ids": msg.chunk_ids,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    content: str,
    role: str = "user",
    use_rag: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Send a message in a conversation.
    
    If use_rag=True and conversation has source_id, uses RAG vector search.
    Otherwise, sends message without RAG context.
    """
    try:
        container = await get_service_container(db)
        chat_service = container.get_chat_service()
        chunk_repo = container.get_chunk_repository()
        llm_client = container.llm_client
        
        # If RAG is enabled and role is user, use RAG service
        if use_rag and role == "user":
            # Verify conversation belongs to user first
            conversation = await chat_service.get_conversation(conversation_id, current_user.id)
            
            # Use RAG if enabled (will search entire notebook if source_id is None)
            assistant_msg = await chat_service.send_message_with_rag(
                conversation_id=conversation_id,
                user_id=current_user.id,
                user_message=content,
                llm_client=llm_client,
                chunk_repo=chunk_repo,
            )
            await db.commit()
            await db.refresh(assistant_msg)
            return {
                "id": assistant_msg.id,
                "conversation_id": assistant_msg.conversation_id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "chunk_ids": assistant_msg.chunk_ids,
                "created_at": assistant_msg.created_at.isoformat()
            }
        
        # Fallback: regular message (Syntra Contextual Chat)
        if role == "user":
            assistant_msg = await chat_service.send_message_with_context(
                conversation_id=conversation_id,
                user_id=current_user.id,
                user_message=content,
                llm_client=llm_client,
            )
            await db.commit()
            await db.refresh(assistant_msg)
            return {
                "id": assistant_msg.id,
                "conversation_id": assistant_msg.conversation_id,
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "created_at": assistant_msg.created_at.isoformat()
            }
        
        # Original fallback for non-user messages (e.g. manual history injection)
        message_id = str(uuid4())
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat()
        }
    except DomainError as e:
        await db.rollback()
        e.log(logger)
        raise HTTPException(status_code=e.http_status_code, detail=e.message)
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in send_message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """Get messages for a conversation."""
    # Verify conversation belongs to user
    conv_query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )
    conv_result = await db.execute(conv_query)
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages
    msg_query = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).offset(skip).limit(limit)
    
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()
    
    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "chunk_ids": msg.chunk_ids,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ],
        "total": len(messages)
    }