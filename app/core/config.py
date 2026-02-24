from typing import Optional, Union, List
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
import secrets



class Settings(BaseSettings):
    """Application settings."""
    
    # Project information
    PROJECT_NAME: str = "MindSpring FastAPI Backend"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Enterprise-grade FastAPI backend for MindSpring"
    
    # Server configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    DEBUG: bool = False
    
    # Database configuration
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 50  # Increased from 20 for 1000s concurrent users
    DATABASE_POOL_OVERFLOW: int = 30  # Increased from 10 for connection bursts
    DATABASE_POOL_TIMEOUT: int = 10  # Query timeout for connection acquisition
    DATABASE_ECHO: bool = False
    DATABASE_QUERY_TIMEOUT: int = 30  # Statement timeout in seconds
    
    # Redis configuration
    REDIS_URL: str
    REDIS_POOL_SIZE: int = 20
    
    # Authentication settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Clerk configuration (Deprecated/Legacy?)
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWT_ISSUER: Optional[str] = None
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Email/OTP settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    OTP_EXPIRE_MINUTES: int = 10
    
    # LLM Configuration
    LLM_BASE_URL: Optional[str] = "https://inference.ai.neevcloud.com/v1"
    AI_API_ENDPOINT: Optional[str] = "https://inference.ai.neevcloud.com/v1/chat/completions"
    LLM_MODEL: str = "gpt-oss-120b"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # CEPH/S3 storage settings
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "abhimindsping-ind"
    
    # Docling OCR settings
    DOCLING_OCR_BACKEND: str = "tesseract"
    DOCLING_ENABLE_OCR: bool = True
    DOCLING_ENABLE_TABLES: bool = False
    DOCLING_OCR_ALL_PAGES: bool = False
    DOCLING_VERBOSE: bool = False
    
    # CEPH settings
    CEPH_ENDPOINT: Optional[str] = None
    CEPH_ACCESS_KEY: Optional[str] = None
    CEPH_SECRET_KEY: Optional[str] = None
    CEPH_BUCKET: str = "vijamindspring"
    CEPH_PUBLIC_URL: Optional[str] = None
    
    # Celery settings
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Embedding settings
    EMBEDDING_DIMENSION: int = 1536  # text-embedding-ada-002 model
    EMBEDDING_ENDPOINT: Optional[str] = "https://api.openai.com/v1/embeddings"
    EMBEDDING_MODEL_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    CHUNK_SIZE_TOKENS: int = 400
    MAX_CHUNK_SIZE_TOKENS: int = 600
    
    # Rate limiting
    RATE_LIMIT_DEFAULT: str = "100/hour"
    RATE_LIMIT_DOCUMENT_UPLOAD: str = "10/day"
    
    # Vector search settings
    VECTOR_SEARCH_THRESHOLD: float = 0.7
    MAX_SIMILARITY_RESULTS: int = 10
    
    # Task settings
    TASK_TIMEOUT_SECONDS: int = 300
    DOCUMENT_PROCESSING_TIMEOUT: int = 1800
    REQUEST_TIMEOUT_SECONDS: float = 30.0
    
    # External services
    OPENAI_API_KEY: Optional[str] = None
    NEEVCLOUD_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
