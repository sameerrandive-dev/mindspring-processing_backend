"""Domain schemas for API request/response validation."""

from .auth import (
    UserCreate,
    UserLogin,
    Token,
    UserResponse,
    OTPVerify,
    Msg,
    PasswordResetRequest,
    PasswordReset,
    ResendOTPRequest,
)
from .notebook import (
    NotebookCreate,
    NotebookUpdate,
    NotebookResponse,
    NotebookListResponse,
)

__all__ = [
    # Auth schemas
    "UserCreate",
    "UserLogin",
    "Token",
    "UserResponse",
    "OTPVerify",
    "Msg",
    "PasswordResetRequest",
    "PasswordReset",
    "ResendOTPRequest",
    # Notebook schemas
    "NotebookCreate",
    "NotebookUpdate",
    "NotebookResponse",
    "NotebookListResponse",
]
