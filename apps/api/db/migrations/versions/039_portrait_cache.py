"""Add user_preferences.portrait_cache JSONB (Self-Portrait payoff summary cache)

Revision ID: 039_portrait_cache
Revises: 038_counterview_turns
Create Date: 2026-06-29

Additive, schema-only. `portrait_cache` JSONB is NULLABLE: NULL means "no cached
portrait yet" and the GET /preferences/self-portrait/portrait endpoint serves the
forming preview. Holds the derived (server-generated, NOT user-authored) Self-
Portrait summary cache, kept separate from the user-authored `profile` blob:
  {"text": str, "best_fit": [...], "answer_count_watermark": int,
   "generated_at": iso8601}
The summary itself is written in a later slice (5b); this column only reserves the
storage. All existing rows default to NULL, so this migration is a pure no-op for
current behaviour. Mirrors the additive nullable-column pattern of 037.
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = '039_portrait_cache'
down_revision = '038_counterview_turns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_preferences', sa.Column('portrait_cache', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('user_preferences', 'portrait_cache')
