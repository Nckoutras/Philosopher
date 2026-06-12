"""Create mirror_saves table

Revision ID: 025_create_mirror_saves
Revises: 024_saved_line_conclusion_source
Create Date: 2026-06-12

Additive: Mirror verdict saves get their own table mirroring the
council_saves pattern exactly (P2-SMOKE-10 phase 1). No changes to
saved_lines or the mirrors table.
"""
from alembic import op

revision = '025_create_mirror_saves'
down_revision = '024_saved_line_conclusion_source'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mirror_saves (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            mirror_id UUID NOT NULL REFERENCES mirrors(id) ON DELETE CASCADE,
            saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ,
            CONSTRAINT uq_mirror_saves_user_mirror UNIQUE (user_id, mirror_id)
        )
    """)
    op.execute("CREATE INDEX ix_mirror_saves_user ON mirror_saves (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mirror_saves")
