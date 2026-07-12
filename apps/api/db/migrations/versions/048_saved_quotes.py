"""Create saved_quotes table

Revision ID: 048_saved_quotes
Revises: 047_insight_theme
Create Date: 2026-07-12

Additive: quote saves get their own table, mirroring the counterview_saves /
mirror_saves / council_saves pattern exactly (soft-delete via deleted_at, one
row per user+quote). No changes to quotes. The partial index serves the
Reflections feed query (active saves for a user, newest first).
"""
from alembic import op

revision = '048_saved_quotes'
down_revision = '047_insight_theme'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE saved_quotes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
            saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_saved_quotes_user_quote UNIQUE (user_id, quote_id)
        )
    """)
    op.execute(
        "CREATE INDEX ix_saved_quotes_user_saved_at "
        "ON saved_quotes (user_id, saved_at DESC) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS saved_quotes")
