from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.infrastructure.database.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.domain.models.notebook import Notebook
    from app.domain.models.source import Source


class Chunk(Base):
    __tablename__ = "chunks"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    notebook_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    plain_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Legacy JSONB storage
    embedding_vector: Mapped[Optional[list[float]]] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)  # pgvector column
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="chunks")
    source: Mapped["Source"] = relationship("Source", back_populates="chunks")