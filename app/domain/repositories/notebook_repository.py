"""Notebook repository for managing notebooks and related entities."""

import time
import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pgvector.sqlalchemy import Vector
import numpy as np

from app.domain.models.notebook import Notebook
from app.domain.models.source import Source
from app.domain.models.chunk import Chunk
from app.domain.errors import NotFoundError
from app.domain.interfaces import ILLMClient
from app.core.config import settings
from app.infrastructure.monitoring.logging_setup import log_performance

logger = logging.getLogger(__name__)


class NotebookRepository:
    """Repository for Notebook entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        owner_id: str,
        title: str,
        description: str = "",
        language: str = "en",
        tone: str = "professional",
        max_context_tokens: int = 4096,
    ) -> Notebook:
        """Create a new notebook."""
        notebook = Notebook(
            owner_id=owner_id,
            title=title,
            description=description,
            language=language,
            tone=tone,
            max_context_tokens=max_context_tokens,
        )
        self.db.add(notebook)
        await self.db.flush()
        return notebook
    
    async def get_by_id(self, notebook_id: str, include_deleted: bool = False) -> Optional[Notebook]:
        """Get notebook by ID with relationships loaded."""
        query = select(Notebook).where(Notebook.id == notebook_id)
        
        # Filter out soft-deleted notebooks unless explicitly requested
        if not include_deleted:
            query = query.where(Notebook.deleted_at.is_(None))
        
        result = await self.db.execute(
            query.options(selectinload(Notebook.sources))
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_and_owner(self, notebook_id: str, owner_id: str, include_deleted: bool = False) -> Optional[Notebook]:
        """Get notebook by ID checking owner."""
        query = select(Notebook).where(
            and_(Notebook.id == notebook_id, Notebook.owner_id == owner_id)
        )
        
        # Filter out soft-deleted notebooks unless explicitly requested
        if not include_deleted:
            query = query.where(Notebook.deleted_at.is_(None))
        
        result = await self.db.execute(
            query.options(selectinload(Notebook.sources))
        )
        return result.scalar_one_or_none()
    
    async def update(self, notebook_id: str, **updates) -> Notebook:
        """Update notebook fields (only works on non-deleted notebooks)."""
        notebook = await self.get_by_id(notebook_id, include_deleted=False)
        if not notebook:
            raise NotFoundError(f"Notebook {notebook_id} not found", resource_type="Notebook", resource_id=notebook_id)
        
        for key, value in updates.items():
            if hasattr(notebook, key) and key != "id" and key != "owner_id" and key != "deleted_at":
                setattr(notebook, key, value)
        
        await self.db.flush()
        return notebook
    
    async def delete(self, notebook_id: str) -> bool:
        """Soft delete notebook by ID (sets deleted_at timestamp)."""
        notebook = await self.get_by_id(notebook_id, include_deleted=False)
        if not notebook:
            return False
        
        # Soft delete: set deleted_at timestamp
        notebook.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
    
    async def restore(self, notebook_id: str) -> bool:
        """Restore a soft-deleted notebook."""
        notebook = await self.get_by_id(notebook_id, include_deleted=True)
        if not notebook or notebook.deleted_at is None:
            return False
        
        # Restore: clear deleted_at timestamp
        notebook.deleted_at = None
        await self.db.flush()
        return True
    
    async def hard_delete(self, notebook_id: str) -> bool:
        """Permanently delete notebook from database (use with caution)."""
        notebook = await self.get_by_id(notebook_id, include_deleted=True)
        if not notebook:
            return False
        
        # Hard delete: physically remove from database
        self.db.delete(notebook)
        await self.db.flush()
        return True
    
    async def list_by_owner(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[Notebook]:
        """List notebooks by owner with pagination."""
        query = select(Notebook).where(Notebook.owner_id == owner_id)
        
        # Filter out soft-deleted notebooks unless explicitly requested
        if not include_deleted:
            query = query.where(Notebook.deleted_at.is_(None))
        
        result = await self.db.execute(
            query
            .offset(skip)
            .limit(limit)
            .order_by(desc(Notebook.created_at))
            .options(selectinload(Notebook.sources))
        )
        return result.scalars().all()


class SourceRepository:
    """Repository for Source (document/article) entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        notebook_id: str,
        source_type: str,
        title: str,
        original_url: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[dict] = None,
        status: str = "active",
    ) -> Source:
        """Create a new source."""
        source = Source(
            notebook_id=notebook_id,
            type=source_type,
            title=title,
            original_url=original_url,
            file_path=file_path,
            metadata=metadata or {},
            status=status,
        )
        self.db.add(source)
        await self.db.flush()
        return source
    
    async def get_by_id(self, source_id: str) -> Optional[Source]:
        """Get source by ID."""
        result = await self.db.execute(
            select(Source)
            .where(Source.id == source_id)
            .options(selectinload(Source.chunks))
        )
        return result.scalar_one_or_none()
    
    async def list_by_notebook(self, notebook_id: str) -> List[Source]:
        """List all sources in a notebook."""
        result = await self.db.execute(
            select(Source)
            .where(Source.notebook_id == notebook_id)
            .order_by(desc(Source.created_at))
            .options(selectinload(Source.chunks))
        )
        return result.scalars().all()
    
    async def update(self, source_id: str, **updates) -> Source:
        """Update source fields."""
        source = await self.get_by_id(source_id)
        if not source:
            raise NotFoundError(f"Source {source_id} not found", resource_type="Source", resource_id=source_id)
        
        for key, value in updates.items():
            if hasattr(source, key) and key != "id":
                setattr(source, key, value)
        
        await self.db.flush()
        return source
    
    async def delete(self, source_id: str) -> bool:
        """Delete source (cascade deletes chunks)."""
        source = await self.get_by_id(source_id)
        if not source:
            return False
        
        # session.delete() is synchronous - marks object for deletion
        self.db.delete(source)
        await self.db.flush()
        return True


class ChunkRepository:
    """Repository for Chunk (document chunk) entity operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def bulk_create(
        self,
        chunks_data: List[dict],
    ) -> List[Chunk]:
        """
        Create multiple chunks in a single batch.
        
        Args:
            chunks_data: List of dicts containing:
                - source_id: str
                - notebook_id: str
                - plain_text: str
                - chunk_index: int
                - offsets: Optional[dict]
                - embedding_json: Optional[list]
                - embedding_vector: Optional[list[float]]
                - metadata: Optional[dict]
                
        Returns:
            List of created chunks
        """
        chunks = []
        for data in chunks_data:
            embedding_vector = data.get("embedding_vector")
            embedding_json = data.get("embedding_json")
            if embedding_vector is None and embedding_json:
                embedding_vector = embedding_json
                
            chunk = Chunk(
                source_id=data["source_id"],
                notebook_id=data["notebook_id"],
                plain_text=data["plain_text"],
                chunk_index=data["chunk_index"],
                start_offset=data.get("offsets", {}).get("start") if data.get("offsets") else None,
                end_offset=data.get("offsets", {}).get("end") if data.get("offsets") else None,
                embedding=embedding_json if embedding_json else None,
                embedding_vector=embedding_vector,
                metadata_=data.get("metadata") or {},
            )
            chunks.append(chunk)
            self.db.add(chunk)
        
        await self.db.flush()
        return chunks
    
    async def get_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Get chunk by ID."""
        result = await self.db.execute(select(Chunk).where(Chunk.id == chunk_id))
        return result.scalar_one_or_none()
    
    async def list_by_source(self, source_id: str) -> List[Chunk]:
        """List all chunks for a source."""
        result = await self.db.execute(
            select(Chunk)
            .where(Chunk.source_id == source_id)
            .order_by(Chunk.chunk_index)
        )
        return result.scalars().all()
    
    async def list_by_notebook(self, notebook_id: str) -> List[Chunk]:
        """List all chunks in a notebook."""
        result = await self.db.execute(
            select(Chunk).where(Chunk.notebook_id == notebook_id)
        )
        return result.scalars().all()
    
    async def delete_by_source(self, source_id: str) -> None:
        """Delete all chunks for a source."""
        result = await self.db.execute(select(Chunk).where(Chunk.source_id == source_id))
        chunks = result.scalars().all()
        for chunk in chunks:
            # session.delete() is synchronous - marks object for deletion
            self.db.delete(chunk)
        await self.db.flush()
    
    async def search_by_embedding(
        self,
        query_embedding: list[float],
        notebook_id: Optional[str] = None,
        source_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Chunk]:
        """
        Vector similarity search using cosine distance.
        
        Args:
            query_embedding: Query vector embedding (list of floats)
            notebook_id: Optional filter by notebook
            source_id: Optional filter by source
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of Chunks ordered by similarity (most similar first)
        """
        start_time = time.time()
        
        # Build base query
        query = select(Chunk).where(
            Chunk.embedding_vector.isnot(None)  # Only chunks with vectors
        )
        
        # Apply filters
        if notebook_id:
            query = query.where(Chunk.notebook_id == notebook_id)
        if source_id:
            query = query.where(Chunk.source_id == source_id)
        
        # Calculate cosine distance (1 - cosine similarity)
        # pgvector uses cosine distance, where 0 = identical, 2 = opposite
        # Get more candidates for threshold filtering (top_k * 3 for better accuracy)
        query = query.order_by(
            Chunk.embedding_vector.cosine_distance(query_embedding)
        ).limit(top_k * 3)
        
        result = await self.db.execute(query)
        chunks = result.scalars().all()
        
        # Filter by similarity threshold and calculate actual scores
        filtered_chunks = []
        logger.info(
            f"🔍 Vector search: Found {len(chunks)} candidate chunks, "
            f"filtering by similarity threshold {similarity_threshold}"
        )
        
        for chunk in chunks:
            if chunk.embedding_vector:
                # Calculate cosine similarity
                similarity = self._calculate_cosine_similarity(
                    query_embedding,
                    list(chunk.embedding_vector)
                )
                if similarity >= similarity_threshold:
                    # Store similarity in metadata for reference
                    if not chunk.metadata_:
                        chunk.metadata_ = {}
                    chunk.metadata_['similarity_score'] = float(similarity)
                    filtered_chunks.append(chunk)
                    logger.info(
                        f"✅ Retrieved chunk from embeddings: "
                        f"chunk_id={chunk.id}, chunk_index={chunk.chunk_index}, "
                        f"source_id={chunk.source_id}, similarity_score={similarity:.4f}, "
                        f"text_preview='{chunk.plain_text[:80]}...'"
                    )
        
        # Log performance
        duration = time.time() - start_time
        log_performance(
            logger,
            "vector_search",
            duration,
            resource="vector_db",
            extra_data={
                "top_k": top_k,
                "results_found": len(filtered_chunks),
                "candidates_checked": len(chunks)
            }
        )
        
        logger.info(
            f"📊 Vector search completed: Retrieved {len(filtered_chunks)} chunks "
            f"from embeddings (saved during ingestion), returning top {top_k}"
        )
        
        # Return top_k after filtering
        return filtered_chunks[:top_k]
    
    def _calculate_cosine_similarity(
        self,
        vec1: list[float],
        vec2: list[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def search_by_text(
        self,
        query_text: str,
        notebook_id: Optional[str] = None,
        source_id: Optional[str] = None,
        top_k: int = 5,
        llm_client: Optional[ILLMClient] = None,
    ) -> List[Chunk]:
        """
        Semantic search by text query (generates embedding automatically).
        
        Args:
            query_text: Natural language query
            notebook_id: Optional filter by notebook
            source_id: Optional filter by source
            top_k: Number of results to return
            llm_client: LLM client for generating query embedding
            
        Returns:
            List of Chunks ordered by similarity
        """
        if not llm_client:
            raise ValueError("LLM client required for text-based search")
        
        logger.info(
            f"🔎 Starting semantic search: query='{query_text[:100]}...', "
            f"notebook_id={notebook_id}, source_id={source_id}, top_k={top_k}"
        )
        
        # Generate embedding for query text
        logger.info(f"🧠 Generating embedding for query text to search saved chunk embeddings")
        embeddings = await llm_client.generate_embeddings([query_text])
        query_embedding = embeddings[0]
        logger.info(
            f"✅ Query embedding generated: dimension={len(query_embedding)}, "
            f"now searching chunks saved with embeddings"
        )
        
        # Use vector search
        results = await self.search_by_embedding(
            query_embedding=query_embedding,
            notebook_id=notebook_id,
            source_id=source_id,
            top_k=top_k,
            similarity_threshold=settings.VECTOR_SEARCH_THRESHOLD,
        )
        
        logger.info(
            f"🎯 Semantic search completed: Found {len(results)} chunks "
            f"using embeddings that were saved during document ingestion"
        )
        
        return results