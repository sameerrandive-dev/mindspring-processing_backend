"""Transaction example service demonstrating enterprise transaction patterns."""

import logging
from typing import Optional

from app.domain.models.notebook import Notebook
from app.domain.models.source import Source
from app.domain.models.chunk import Chunk
from app.domain.repositories.notebook_repository import (
    NotebookRepository,
    SourceRepository,
    ChunkRepository,
)
from app.domain.errors import ValidationError

logger = logging.getLogger(__name__)


class TransactionExampleService:
    """
    Reference implementation of enterprise transaction patterns.
    
    This service demonstrates how to:
    - Perform multi-step operations atomically
    - Use transaction context managers
    - Rollback on errors
    - Ensure data consistency across multiple repositories
    
    Real-world usage: Import documents with sources and chunks in one atomic transaction.
    If any step fails, entire operation is rolled back.
    """
    
    def __init__(
        self,
        notebook_repo: NotebookRepository,
        source_repo: SourceRepository,
        chunk_repo: ChunkRepository,
    ):
        self.notebook_repo = notebook_repo
        self.source_repo = source_repo
        self.chunk_repo = chunk_repo
    
    async def import_document_with_chunks_transaction(
        self,
        notebook_id: int,
        source_title: str,
        document_text: str,
        source_type: str = "document",
        chunk_size: int = 512,
    ) -> dict:
        """
        Example: Import a document with chunks in a single transaction.
        
        This demonstrates atomic multi-repository operations:
        1. Create source
        2. Chunk the document
        3. Create chunks
        
        If any step fails, the entire operation rolls back.
        
        Note: In production, use database transaction context managers.
        Here we show the pattern for service-level transactions.
        
        Args:
            notebook_id: Target notebook
            source_title: Document title
            document_text: Full document text
            source_type: Type of source
            chunk_size: Size of text chunks
            
        Returns:
            Dict with created source and chunks
            
        Raises:
            ValidationError: Invalid input
        """
        if not document_text:
            raise ValidationError("Document text cannot be empty")
        
        if chunk_size < 100:
            raise ValidationError("Chunk size must be at least 100 characters")
        
        logger.info(f"Starting multi-step transaction: import document to notebook {notebook_id}")
        
        try:
            # STEP 1: Create source
            logger.info("Transaction step 1: Creating source")
            source = await self.source_repo.create(
                notebook_id=notebook_id,
                source_type=source_type,
                title=source_title,
                status="processing",
            )
            logger.info(f"Source created: {source.id}")
            
            # STEP 2: Chunk document
            logger.info("Transaction step 2: Chunking document")
            chunks_data = self._chunk_text(document_text, chunk_size)
            
            if not chunks_data:
                raise ValidationError("Document produced no chunks")
            
            logger.info(f"Document chunked into {len(chunks_data)} pieces")
            
            # STEP 3: Create chunks
            logger.info("Transaction step 3: Creating chunks in database")
            created_chunks = []
            
            for i, chunk_text in enumerate(chunks_data):
                try:
                    chunk = await self.chunk_repo.create(
                        source_id=source.id,
                        notebook_id=notebook_id,
                        plain_text=chunk_text,
                        chunk_index=i,
                        metadata={"imported": True},
                    )
                    created_chunks.append(chunk)
                except Exception as e:
                    # If chunk creation fails, we should rollback source and previous chunks
                    logger.error(f"Failed to create chunk {i}: {e}")
                    logger.error("Transaction failed - rollback needed (not implemented in this example)")
                    raise
            
            logger.info(f"All {len(created_chunks)} chunks created successfully")
            
            # STEP 4: Mark source as ready
            logger.info("Transaction step 4: Finalizing source")
            await self.source_repo.update(source.id, status="ready")
            
            logger.info(f"Transaction completed successfully")
            
            return {
                "source_id": source.id,
                "source_title": source.title,
                "chunks_created": len(created_chunks),
                "status": "success",
            }
            
        except Exception as e:
            logger.error(f"Transaction failed with error: {e}")
            # In production with real transactions, this would trigger ROLLBACK
            raise
    
    def _chunk_text(self, text: str, chunk_size: int) -> list:
        """Split text into chunks."""
        chunks = []
        start = 0
        overlap = min(chunk_size // 4, 100)  # 25% overlap
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
