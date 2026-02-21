"""Add deleted_at column to quizzes, study_guides, and otps tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-20 16:15:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deleted_at column to quizzes table for soft deletes
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='quizzes' AND column_name='deleted_at'
            ) THEN
                ALTER TABLE quizzes ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)
    
    # Add deleted_at column to study_guides table for soft deletes
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='study_guides' AND column_name='deleted_at'
            ) THEN
                ALTER TABLE study_guides ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove deleted_at columns
    op.drop_column('study_guides', 'deleted_at')
    op.drop_column('quizzes', 'deleted_at')
