"""Create counterview_saves table

Revision ID: 033_create_counterview_saves
Revises: 032_create_counterviews
Create Date: 2026-06-21

Additive: Counterview verdict saves get their own table, mirroring the
mirror_saves / council_saves pattern exactly. No changes to counterviews or
counterview_responses.
"""
from alembic import op

revision = '033_create_counterview_saves'
down_revision = '032_create_counterviews'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE counterview_saves (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            counterview_id UUID NOT NULL REFERENCES counterviews(id) ON DELETE CASCADE,
            saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_counterview_saves_user_cv UNIQUE (user_id, counterview_id)
        )
    """)
    op.execute("CREATE INDEX ix_counterview_saves_user ON counterview_saves (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS counterview_saves")
