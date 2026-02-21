from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.domain.models.notebook import Notebook
    from app.domain.models.user import User
    from app.domain.models.source import Source
    from app.domain.models.message import Message


class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    notebook_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    mode: Mapped[str] = mapped_column(String(50), default="chat")  # 'chat', 'query', etc.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    source_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="conversations")
    source: Mapped["Source"] = relationship("Source", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")