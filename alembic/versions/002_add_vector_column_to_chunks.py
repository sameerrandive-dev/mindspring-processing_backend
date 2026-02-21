"""Add vector column to chunks for pgvector

Revision ID: 002_add_vector_column
Revises: 001_initial_schema_with_proper_uuids
Create Date: 2024-12-19 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_add_vector_column'
down_revision = '001'  # Matches the revision ID in 001_initial_schema_with_proper_uuids.py
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension if not already enabled
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add vector column to chunks table
    # Using raw SQL to add vector type directly
    op.execute("""
        ALTER TABLE chunks 
        ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)
    """)
    
    # Note: Existing chunks with JSONB embeddings will have NULL vector column
    # New chunks will populate both embedding (JSONB) and embedding_vector
    # A separate migration script can backfill vectors from JSONB if needed
    
    # Create HNSW index for fast vector similarity search
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_vector 
        ON chunks 
        USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding_vector IS NOT NULL
    """)
    
    # Also create index for source_id + vector search (common query pattern)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_source_vector 
        ON chunks (source_id)
        WHERE embedding_vector IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('idx_chunks_source_vector', table_name='chunks')
    op.drop_index('idx_chunks_embedding_vector', table_name='chunks')
    op.drop_column('chunks', 'embedding_vector')
    # Note: We don't drop the vector extension as it might be used elsewhere
