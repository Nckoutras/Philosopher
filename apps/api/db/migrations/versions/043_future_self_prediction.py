"""Add scheduled_emails prediction + review columns (Future Self loop close)

Revision ID: 043_future_self_prediction
Revises: 042_council_synthesis_json
Create Date: 2026-07-09

Additive, nullable ×3. Closes the future-self loop:
- `prediction`  — an optional guess written at schedule time (never emailed;
  surfaced only on the in-app arrived screen).
- `review_text` — the reader's answer on open ("what happened"); one per letter,
  overwrite-editable (mirrors weekly_letters.write_back_text semantics).
- `review_at`   — when the review was last written; also the Reflections-feed
  sort key for the future_self_review source.

All three default NULL, so existing rows behave exactly as post-R5b-1. No index
needed — the feed filters `review_text IS NOT NULL` within a per-user scan.
"""
from alembic import op

revision = '043_future_self_prediction'
down_revision = '042_council_synthesis_json'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE scheduled_emails ADD COLUMN prediction TEXT")
    op.execute("ALTER TABLE scheduled_emails ADD COLUMN review_text TEXT")
    op.execute("ALTER TABLE scheduled_emails ADD COLUMN review_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE scheduled_emails DROP COLUMN IF EXISTS review_at")
    op.execute("ALTER TABLE scheduled_emails DROP COLUMN IF EXISTS review_text")
    op.execute("ALTER TABLE scheduled_emails DROP COLUMN IF EXISTS prediction")
