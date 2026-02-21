from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base

if TYPE_CHECKING:
    from app.domain.models.notebook import Notebook
    from app.domain.models.user import User


class StudyGuide(Base):
    __tablename__ = "study_guides"
    
    id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    notebook_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    model: Mapped[str] = mapped_column(String(100), nullable=True)  # Model used to generate the study guide
    version: Mapped[int] = mapped_column(default=1)
    
    # Relationships
    notebook: Mapped["Notebook"] = relationship("Notebook", back_populates="study_guides")
    user: Mapped["User"] = relationship("User", back_populates="study_guides")