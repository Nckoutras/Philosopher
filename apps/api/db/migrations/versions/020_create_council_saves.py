"""Create council_saves table

Revision ID: 020_create_council_saves
Revises: 019_create_council
Create Date: 2026-06-01
"""
from alembic import op

revision = '020_create_council_saves'
down_revision = '019_create_council'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE council_saves (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id UUID NOT NULL REFERENCES council_sessions(id) ON DELETE CASCADE,
            saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_council_saves_user_session UNIQUE (user_id, session_id)
        )
    """)
    op.execute("CREATE INDEX ix_council_saves_user ON council_saves (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS council_saves")
