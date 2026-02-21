"""Conversation and Message repositories."""

from typing import Optional, List
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models.conversation import Conversation
from app.domain.models.message import Message
from app.domain.errors import NotFoundError


class ConversationRepository:
    """Repository for Conversation entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        notebook_id: str,
        user_id: str,
        title: str,
        mode: str = "assistant",
        source_id: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            notebook_id=notebook_id,
            user_id=user_id,
            title=title,
            mode=mode,
            source_id=source_id,
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation
    
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_and_user(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Optional[Conversation]:
        """Get conversation by ID checking user ownership."""
        result = await self.db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()
    
    async def list_by_notebook(
        self,
        notebook_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Conversation]:
        """List conversations in a notebook."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(Conversation.updated_at))
            .options(selectinload(Conversation.messages))
        )
        return result.scalars().all()
    
    async def update(self, conversation_id: str, **updates) -> Conversation:
        """Update conversation fields."""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            raise NotFoundError(
                f"Conversation {conversation_id} not found",
                resource_type="Conversation",
                resource_id=conversation_id,
            )
        
        for key, value in updates.items():
            if hasattr(conversation, key) and key != "id" and key != "user_id":
                setattr(conversation, key, value)
        
        await self.db.flush()
        return conversation
    
    async def delete(self, conversation_id: str) -> bool:
        """Delete conversation (cascade deletes messages)."""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False
        
        await self.db.delete(conversation)
        await self.db.flush()
        return True


class MessageRepository:
    """Repository for Message entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        chunk_ids: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            chunk_ids=chunk_ids or [],
            metadata_=metadata or {},
        )
        self.db.add(message)
        await self.db.flush()
        return message
    
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """Get message by ID."""
        result = await self.db.execute(select(Message).where(Message.id == message_id))
        return result.scalar_one_or_none()
    
    async def list_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """List messages in a conversation with pagination."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .offset(skip)
            .limit(limit)
            .order_by(Message.created_at)
        )
        return result.scalars().all()
    
    async def delete(self, message_id: str) -> bool:
        """Delete message."""
        message = await self.get_by_id(message_id)
        if not message:
            return False
        
        await self.db.delete(message)
        await self.db.flush()
        return True
    
    async def delete_by_conversation(self, conversation_id: str) -> None:
        """Delete all messages in a conversation."""
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        messages = result.scalars().all()
        for message in messages:
            await self.db.delete(message)
        await self.db.flush()
