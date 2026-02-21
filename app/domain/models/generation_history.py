from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base


class GenerationHistory(Base):
    __tablename__ = "generation_history"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'quiz', 'study_guide', 'summary', 'chat', 'roadmap'
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)  # Generated content
    content_preview: Mapped[str] = mapped_column(String(500), nullable=True)  # Short preview
    resource_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=True)  # ID of the generated resource
    notebook_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=True)  # Associated notebook
    document_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)  # Associated document
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)