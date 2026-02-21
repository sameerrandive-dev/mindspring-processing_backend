"""RAG document ingestion service for chunking and embeddings."""

import logging
from typing import Optional, List

from app.domain.models.chunk import Chunk
from app.domain.repositories.notebook_repository import ChunkRepository
from app.domain.errors import ExternalServiceError, ValidationError
from app.domain.interfaces import ILLMClient

logger = logging.getLogger(__name__)


class RAGIngestService:
    """
    RAG ingestion service for document chunking and embedding generation.
    
    Responsibilities:
    - Split documents into chunks
    - Generate embeddings for chunks
    - Store vectors
    - Integrate with embedding models
    """
    
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        llm_client: ILLMClient,
        chunk_size: int = 512,
        overlap: int = 100,
    ):
        self.chunk_repo = chunk_repo
        self.llm_client = llm_client
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    async def ingest_document(
        self,
        source_id: str,
        notebook_id: str,
        document_text: str,
        metadata: Optional[dict] = None,
    ) -> List[Chunk]:
        """
        Ingest a document by chunking and generating embeddings.
        
        Args:
            source_id: Source document ID
            notebook_id: Notebook for organization
            document_text: Full document text
            metadata: Additional metadata
            
        Returns:
            List of created chunks with embeddings
        """
        if not document_text or len(document_text.strip()) == 0:
            raise ValidationError("Document text is empty")
        
        # Create chunks
        logger.info(f"Chunking document for source {source_id} ({len(document_text)} characters)")
        chunks_data = self._chunk_text(document_text, self.chunk_size, self.overlap)
        logger.info(f"Created {len(chunks_data)} chunks for source {source_id}")
        
        if not chunks_data:
            raise ValidationError("Document produced no chunks")
        
        # Extract texts for embedding
        chunk_texts = [c["text"] for c in chunks_data]
        
        # Generate embeddings
        try:
            logger.info(f"Starting embedding generation for {len(chunk_texts)} chunks (batch size: 20)")
            embeddings = await self.llm_client.generate_embeddings(chunk_texts)
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
        except Exception as e:
            raise ExternalServiceError(
                "Failed to generate embeddings",
                service_name="LLMClient",
                original_error=e,
            )
        
        # Store chunks with both JSONB (legacy) and vector embeddings
        # Prepare chunk data for bulk insert
        chunks_to_create = []
        for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunks_to_create.append({
                "source_id": source_id,
                "notebook_id": notebook_id,
                "plain_text": chunk_data["text"],
                "chunk_index": i,
                "offsets": chunk_data.get("offsets", {}),
                "embedding_json": embedding,
                "embedding_vector": embedding,
                "metadata": metadata or {},
            })
            
        # Store chunks in bulk
        created_chunks = await self.chunk_repo.bulk_create(chunks_to_create)
        
        logger.info(f"Document ingested: {len(created_chunks)} chunks created for source {source_id}")
        return created_chunks
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[dict]:
        """
        Split text into overlapping chunks.
        
        Returns:
            List of dicts with 'text' and 'offsets'
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            chunks.append({
                "text": chunk_text,
                "offsets": {
                    "start": start,
                    "end": end,
                },
            })
            
            # If we've reached the end of the text, we are done
            if end >= len(text):
                break
                
            # Move start forward, ensuring we make progress to avoid infinite loops
            new_start = end - overlap
            if new_start <= start:
                # If overlap is too large ( >= chunk_size), move forward by at least 1
                start = start + max(1, chunk_size - overlap)
            else:
                start = new_start
        
        return chunks if chunks else []
