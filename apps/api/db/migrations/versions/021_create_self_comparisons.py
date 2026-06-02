"""Create self_comparisons table

Revision ID: 021_create_self_comparisons
Revises: 020_create_council_saves
Create Date: 2026-06-02
"""
from alembic import op

revision = '021_create_self_comparisons'
down_revision = '020_create_council_saves'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE self_comparisons (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            prompt TEXT NOT NULL,
            then_start TIMESTAMPTZ,
            then_end TIMESTAMPTZ,
            now_start TIMESTAMPTZ,
            now_end TIMESTAMPTZ,
            payload JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            ring_true VARCHAR(10),
            ring_true_note TEXT,
            ring_true_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_self_comparisons_user ON self_comparisons (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS self_comparisons")
