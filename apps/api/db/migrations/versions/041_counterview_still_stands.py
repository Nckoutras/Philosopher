"""Add counterviews.still_stands (the "what still stands" closing line)

Revision ID: 041_counterview_still_stands
Revises: 040_self_comparison_saves
Create Date: 2026-07-09

Additive, nullable: one quiet closing line naming what of the belief survives the
challenge, generated on the same LLM call as the two verdicts (grounded-or-null).
Old rows stay NULL and render exactly as before. No changes to
counterview_responses or counterview_turns.
"""
from alembic import op

revision = '041_counterview_still_stands'
down_revision = '040_self_comparison_saves'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE counterviews ADD COLUMN still_stands TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE counterviews DROP COLUMN IF EXISTS still_stands")
