"""Update vector dimension of chunks table

Revision ID: 003_update_vector_dimension
Revises: 002_add_vector_column
Create Date: 2026-02-20 15:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003_update_vector_dimension'
down_revision = '002_add_vector_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop the existing indices that depend on the column
    op.execute('DROP INDEX IF EXISTS idx_chunks_embedding_vector')
    op.execute('DROP INDEX IF EXISTS idx_chunks_source_vector')
    
    # 2. Change the column type (requires dropping and recreating for vector type)
    # Note: This will CLEAR all existing embeddings as they are incompatible with the new dimension
    op.execute('ALTER TABLE chunks DROP COLUMN IF EXISTS embedding_vector')
    op.execute('ALTER TABLE chunks ADD COLUMN embedding_vector vector(4096)')
    
    # 3. Skip index creation for embedding_vector
    # Note: pgvector with >2000 dimensions cannot be indexed in this environment.
    # Searching will fall back to exact (non-indexed) scan, which is accurate but slower.
    pass


def downgrade() -> None:
    # 1. Revert to 1536 dimensions
    op.execute('ALTER TABLE chunks DROP COLUMN IF EXISTS embedding_vector')
    op.execute('ALTER TABLE chunks ADD COLUMN embedding_vector vector(1536)')
    
    # 2. Recreate original indices
    op.execute("""
        CREATE INDEX idx_chunks_embedding_vector 
        ON chunks 
        USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE embedding_vector IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX idx_chunks_source_vector 
        ON chunks (source_id)
        WHERE embedding_vector IS NOT NULL
    """)
