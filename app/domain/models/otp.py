from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.sql import func
import enum

from app.infrastructure.database.session import Base

class OTPType(str, enum.Enum):
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"

class OTP(Base):
    __tablename__ = "otps"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # Hashed in real production, but for now string
    type: Mapped[OTPType] = mapped_column(String(20), nullable=False, default=OTPType.SIGNUP)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
