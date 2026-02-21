from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.domain.models.conversation import Conversation


class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_ids: Mapped[list[str]] = mapped_column(ARRAY(PG_UUID(as_uuid=False)), default=list)  # Array of chunk IDs for RAG
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")