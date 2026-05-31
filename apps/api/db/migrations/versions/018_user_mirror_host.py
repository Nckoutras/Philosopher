"""Add mirror_host_slug to users table

Revision ID: 018_user_mirror_host
Revises: 017_create_mirrors
Create Date: 2026-05-31
"""
from alembic import op

revision = '018_user_mirror_host'
down_revision = '017_create_mirrors'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE users ADD COLUMN mirror_host_slug VARCHAR(100)')


def downgrade() -> None:
    op.execute('ALTER TABLE users DROP COLUMN IF EXISTS mirror_host_slug')
