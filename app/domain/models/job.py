from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.domain.models.document import Document


class Job(Base):
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'document_processing', 'embedding', 'quiz_generation', etc.
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # Progress percentage (0-100)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)  # Result data
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)  # Changed from metadata to avoid SQLAlchemy reserved name
    error_message: Mapped[str] = mapped_column(Text, nullable=True)  # Error details if failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="jobs")