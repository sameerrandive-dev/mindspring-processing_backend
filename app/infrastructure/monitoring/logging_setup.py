import logging
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger
from typing import Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.fromtimestamp(record.created).isoformat()
        log_record['level'] = record.levelname
        log_record['service'] = 'mindspring-fastapi-backend'
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID and structured logging with performance tracking."""
    
    async def dispatch(self, request: Request, call_next):
        import time
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request details to the log context
        request_details = {
            'request_id': request_id,
            'method': request.method,
            'url': str(request.url),
            'user_agent': request.headers.get('user-agent'),
            'remote_addr': request.client.host if request.client else None
        }
        
        # Log the incoming request
        logger = get_logger(__name__)
        logger.info("Incoming request", extra=request_details)
        
        # Measure request duration
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the response with performance metrics
        response_details = {
            'request_id': request_id,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'endpoint': str(request.url.path)
        }
        logger.info("Outgoing response", extra=response_details)
        
        # Log performance metric
        log_performance(
            logger,
            operation=f"{request.method} {request.url.path}",
            duration=duration,
            resource="api_endpoint",
            extra_data={
                'status_code': response.status_code,
                'method': request.method
            }
        )
        
        return response


def setup_logging():
    """Setup structured logging configuration."""
    # Create a custom logger
    logger = logging.getLogger()
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set the logging level
    logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    
    # Create handler that writes to stdout
    handler = logging.StreamHandler(sys.stdout)
    
    # Create custom formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(service)s %(module)s %(function)s %(line)d %(message)s'
    )
    
    handler.setFormatter(formatter)
    
    # Add handler to the logger
    logger.addHandler(handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    logger = logging.getLogger(name)
    
    # Ensure the logger has the proper configuration
    if not logger.handlers:
        setup_logging()
    
    return logger


def log_api_call(
    logger: logging.Logger, 
    endpoint: str, 
    method: str, 
    user_id: str = None, 
    status_code: int = None, 
    response_time: float = None,
    extra_data: Dict[str, Any] = None
):
    """Log an API call with structured data."""
    log_data = {
        'event': 'api_call',
        'endpoint': endpoint,
        'method': method,
        'user_id': user_id,
        'status_code': status_code,
        'response_time_ms': round(response_time * 1000, 2) if response_time else None
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info("API call", extra=log_data)


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str = None,
    user_id: str = None,
    extra_data: Dict[str, Any] = None
):
    """Log an error with structured data."""
    log_data = {
        'event': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'user_id': user_id
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.error("Error occurred", extra=log_data)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    resource: str = None,
    user_id: str = None,
    extra_data: Dict[str, Any] = None
):
    """Log performance metrics."""
    log_data = {
        'event': 'performance',
        'operation': operation,
        'duration_ms': round(duration * 1000, 2),
        'resource': resource,
        'user_id': user_id
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.info("Performance metric", extra=log_data)