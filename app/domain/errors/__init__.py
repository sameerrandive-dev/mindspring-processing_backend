"""Domain error hierarchy."""

from .exceptions import (
    DomainError,
    ValidationError,
    NotFoundError,
    ConflictError,
    AuthError,
    ForbiddenError,
    BusinessRuleViolationError,
    RateLimitError,
    ExternalServiceError,
    InternalServerError,
    ErrorCode,
)

__all__ = [
    "DomainError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "AuthError",
    "ForbiddenError",
    "BusinessRuleViolationError",
    "RateLimitError",
    "ExternalServiceError",
    "InternalServerError",
    "ErrorCode",
]
