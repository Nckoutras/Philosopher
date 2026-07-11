"""Add quotes.themes (theme tags for The Wise Room themed surfacing)

Revision ID: 046_quotes_themes
Revises: 045_quotes
Create Date: 2026-07-11

Additive, nullable-safe. Each quote carries 1–3 theme slugs (THEME_VALUES) used by
PR-5b to surface quotes by theme. Existing rows default to '{}' (empty array); the
themed seed (db/seed_quotes.py) then populates all 88 rows via idempotent upsert.
The GIN index supports membership queries (:theme = ANY(themes)). No changes to any
existing column.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = '046_quotes_themes'
down_revision = '045_quotes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'quotes',
        sa.Column('themes', postgresql.ARRAY(sa.Text()), nullable=False,
                  server_default=sa.text("'{}'::text[]")),
    )
    op.create_index('idx_quotes_themes', 'quotes', ['themes'], postgresql_using='gin')


def downgrade() -> None:
    op.drop_index('idx_quotes_themes', table_name='quotes')
    op.drop_column('quotes', 'themes')
