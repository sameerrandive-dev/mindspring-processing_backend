"""In-memory mock storage provider for testing."""

import uuid
from datetime import datetime
from typing import Dict, Optional
from app.domain.interfaces import IStorageProvider


class MockStorageProvider(IStorageProvider):
    """In-memory file storage for testing."""
    
    def __init__(self):
        self._storage: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, str]] = {}
    
    def _generate_key(self, prefix: str = "sources", filename: Optional[str] = None) -> str:
        """Generate storage key for file (same format as CephStorageProvider)."""
        now = datetime.utcnow()
        file_id = str(uuid.uuid4())
        
        if filename:
            if '.' in filename:
                ext = filename.rsplit('.', 1)[1]
                key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}.{ext}"
            else:
                key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}"
        else:
            key = f"{prefix}/{now.year}/{now.month:02d}/{file_id}"
        
        return key
    
    async def store(self, key: str, content: bytes, metadata: Optional[Dict[str, str]] = None) -> str:
        """Store file in memory."""
        # Auto-generate key if not provided
        if not key:
            filename = metadata.get("filename") if metadata else None
            key = self._generate_key(filename=filename)
        
        self._storage[key] = content
        if metadata:
            self._metadata[key] = metadata
        return key
    
    async def retrieve(self, key: str) -> bytes:
        """Retrieve file from memory."""
        return self._storage.get(key, b"")
    
    async def delete(self, key: str) -> bool:
        """Delete file from memory."""
        if key in self._storage:
            del self._storage[key]
            if key in self._metadata:
                del self._metadata[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if file exists in memory."""
        return key in self._storage
    
    async def get_signed_url(self, key: str, expires_in: int = 600) -> str:
        """
        Get a mock presigned URL for testing.
        
        In production, this would generate a real presigned URL.
        For mock storage, we return a mock URL that indicates the key.
        """
        if key not in self._storage:
            raise FileNotFoundError(f"File not found: {key}")
        # Return a mock URL format for testing
        return f"mock://storage/{key}?expires={expires_in}"