"""
Domain-level exception hierarchy.

All business logic errors are represented as DomainError subclasses.
These are caught by endpoint error handlers and converted to HTTP responses.

Pattern:
- Services raise DomainError subclasses (never HTTP exceptions)
- Endpoints catch DomainError and convert to appropriate HTTP status code
- HTTP layer (FastAPI) is completely decoupled from business logic
"""

from enum import Enum
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for all domain errors."""
    
    # Validation errors
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Business rule violations
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    
    # System errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class DomainError(Exception):
    """
    Base exception for all domain-level errors.
    
    Used by services to signal failures without coupling to HTTP layer.
    Endpoints catch this and convert to appropriate HTTP status codes.
    
    Attributes:
        code: Machine-readable error code (ErrorCode enum)
        message: Human-readable error message
        details: Additional context as dict (logged but not exposed to client)
        http_status_code: Suggested HTTP status code (for endpoint mapping)
    """
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        http_status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.http_status_code = http_status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        return f"{self.code.value}: {self.message}"
    
    def log(self, logger_instance=None):
        """Log error with full context for debugging."""
        target_logger = logger_instance or logger
        target_logger.error(
            f"Domain error: {self.code.value} - {self.message}",
            extra={
                "error_code": self.code.value,
                "error_message": self.message,
                "details": self.details,
                "http_status": self.http_status_code,
            },
        )


class ValidationError(DomainError):
    """Input validation failed."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            http_status_code=400,
            details=details,
        )


class NotFoundError(DomainError):
    """Requested resource not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if resource_type:
            full_details["resource_type"] = resource_type
        if resource_id:
            full_details["resource_id"] = resource_id
        
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            http_status_code=404,
            details=full_details,
        )


class ConflictError(DomainError):
    """Resource already exists or conflicts with existing data."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.RESOURCE_CONFLICT,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            http_status_code=409,
            details=details,
        )


class AuthError(DomainError):
    """Authentication or authorization failure."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
    ):
        http_status = 401 if code in (ErrorCode.UNAUTHORIZED, ErrorCode.TOKEN_EXPIRED, ErrorCode.TOKEN_INVALID, ErrorCode.INVALID_CREDENTIALS) else 403
        
        super().__init__(
            code=code,
            message=message,
            http_status_code=http_status,
            details=details,
        )


class ForbiddenError(DomainError):
    """User lacks permission to perform this action."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            http_status_code=403,
            details=details,
        )


class BusinessRuleViolationError(DomainError):
    """Business logic constraint violated."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.BUSINESS_RULE_VIOLATION,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            http_status_code=400,
            details=details,
        )


class RateLimitError(DomainError):
    """User exceeded rate limit."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if retry_after:
            full_details["retry_after"] = retry_after
        
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            http_status_code=429,
            details=full_details,
        )


class ExternalServiceError(DomainError):
    """External service (LLM, S3, etc.) call failed."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
        code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if service_name:
            full_details["service_name"] = service_name
        if original_error:
            full_details["original_error"] = str(original_error)
        
        super().__init__(
            code=code,
            message=message,
            http_status_code=502,
            details=full_details,
        )


class InternalServerError(DomainError):
    """Unexpected internal error."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if original_error:
            full_details["original_error"] = str(original_error)
        
        super().__init__(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=message,
            http_status_code=500,
            details=full_details,
        )
