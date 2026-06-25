"""Add user_preferences.profile JSONB (onboarding profile pills)

Revision ID: 037_user_preferences_profile
Revises: 036_weekly_letters_write_back
Create Date: 2026-06-25

Additive, schema-only. `profile` JSONB is NULLABLE: NULL means "no profile" and
everything behaves exactly as today (the persona <what_we_know> block hides, no
seeded memories, no instant reflection). Holds the tappable-pill answers, e.g.
  {"values": ["honesty", "freedom"], "disagreement_style": "probe_their_view"}
All existing rows default to NULL, so this migration is a pure no-op for current
behaviour. Mirrors the additive column pattern of 036.
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = '037_user_preferences_profile'
down_revision = '036_weekly_letters_write_back'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user_preferences', sa.Column('profile', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('user_preferences', 'profile')
