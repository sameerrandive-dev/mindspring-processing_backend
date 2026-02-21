from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.domain.models.user import User
    from app.domain.models.source import Source
    from app.domain.models.chunk import Chunk
    from app.domain.models.conversation import Conversation
    from app.domain.models.quiz import Quiz
    from app.domain.models.study_guide import StudyGuide


class Notebook(Base):
    __tablename__ = "notebooks"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="en")
    tone: Mapped[str] = mapped_column(String(50), default="educational")
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=8000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="notebooks")
    sources: Mapped[list["Source"]] = relationship("Source", back_populates="notebook")
    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="notebook")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="notebook")
    quizzes: Mapped[list["Quiz"]] = relationship("Quiz", back_populates="notebook")
    study_guides: Mapped[list["StudyGuide"]] = relationship("StudyGuide", back_populates="notebook")