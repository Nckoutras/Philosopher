"""Add insights.theme (optional life-theme captured at signal-write for quote-nudge 3a)

Revision ID: 047_insight_theme
Revises: 046_quotes_themes
Create Date: 2026-07-11

Additive, nullable. The extraction prompt may emit an OPTIONAL "theme" slug on a
dilemma/belief signal; the signal->Insight write validates it against THEME_VALUES and
stores it here. Existing rows stay NULL — pure no-op for current behaviour. Theme
populates going forward as new signals fire. No index (queried per-user with a
created_at filter; low volume).
"""
import sqlalchemy as sa
from alembic import op

revision = '047_insight_theme'
down_revision = '046_quotes_themes'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('insights', sa.Column('theme', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('insights', 'theme')
