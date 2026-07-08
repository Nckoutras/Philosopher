"""Create self_comparison_saves table

Revision ID: 040_self_comparison_saves
Revises: 039_portrait_cache
Create Date: 2026-07-08

Additive: saved YvY "sentence you owe yourself" lines get their own table,
mirroring counterview_saves exactly. The save row references the SelfComparison
run; the Reflections feed producer joins to it and pulls
payload["closing"]["sentence_owed"] (null-skipped). No changes to
self_comparisons.
"""
from alembic import op

revision = '040_self_comparison_saves'
down_revision = '039_portrait_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE self_comparison_saves (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            self_comparison_id UUID NOT NULL REFERENCES self_comparisons(id) ON DELETE CASCADE,
            saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_self_comparison_saves_user_sc UNIQUE (user_id, self_comparison_id)
        )
    """)
    op.execute("CREATE INDEX ix_self_comparison_saves_user ON self_comparison_saves (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS self_comparison_saves")
