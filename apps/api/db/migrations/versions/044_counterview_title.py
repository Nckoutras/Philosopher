"""Add counterviews.title (the terrain-of-the-belief share-card heading)

Revision ID: 044_counterview_title
Revises: 043_future_self_prediction
Create Date: 2026-07-10

Additive, nullable: a 2-4 word title naming the abstract terrain of the belief,
generated on the same LLM call as the two verdicts (grounded-or-null). It is
rendered on the SHARED counterview card in place of the user's raw anchor_text —
old rows stay NULL and simply omit that line. No changes to counterview_responses
or counterview_turns.
"""
from alembic import op

revision = '044_counterview_title'
down_revision = '043_future_self_prediction'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE counterviews ADD COLUMN title TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE counterviews DROP COLUMN IF EXISTS title")
