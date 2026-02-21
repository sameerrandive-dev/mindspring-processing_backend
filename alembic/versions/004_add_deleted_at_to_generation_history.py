"""Add deleted_at column to generation_history table

Revision ID: 004
Revises: 003_update_vector_dimension
Create Date: 2026-02-20 16:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003_update_vector_dimension'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deleted_at column to generation_history table for soft deletes
    op.add_column(
        'generation_history',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # Remove deleted_at column
    op.drop_column('generation_history', 'deleted_at')
