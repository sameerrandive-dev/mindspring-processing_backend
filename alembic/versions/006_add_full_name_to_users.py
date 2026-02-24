"""Add full_name to users table

Revision ID: 006
Revises: 005
Create Date: 2026-02-24 15:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add full_name column to users table
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='users' AND column_name='full_name'
            ) THEN
                ALTER TABLE users ADD COLUMN full_name VARCHAR(255);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove full_name column
    op.drop_column('users', 'full_name')
