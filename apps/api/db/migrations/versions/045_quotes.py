"""Add quotes table (The Wise Room authenticated-quotes corpus)

Revision ID: 045_quotes
Revises: 044_counterview_title
Create Date: 2026-07-10

Additive, new table only. Stores the verbatim authenticated-quote corpus (88 rows,
8 per persona × 11 personas) seeded from apps/api/data/quotes_seed.json by
db/seed_quotes.py. `discuss_count`/`story_count` are engagement counters owned by
later slices (never written by the seed); `is_active` gates visibility. The UNIQUE
(persona_slug, source_locator, text_en) is the idempotent upsert key used by the
seed. No changes to any existing table.
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision = '045_quotes'
down_revision = '044_counterview_title'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'quotes',
        sa.Column('id',               UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('persona_slug',     sa.Text, nullable=False),
        sa.Column('text_en',          sa.Text, nullable=False),
        sa.Column('text_original',    sa.Text, nullable=True),
        sa.Column('source_locator',   sa.Text, nullable=False),
        sa.Column('translation_note', sa.Text, nullable=True),
        sa.Column('confidence',       sa.Text, nullable=False),
        sa.Column('context',          sa.Text, nullable=False),
        sa.Column('discuss_count',    sa.Integer, nullable=False, server_default='0'),
        sa.Column('story_count',      sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active',        sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at',       sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('persona_slug', 'source_locator', 'text_en', name='uq_quotes_persona_locator_text'),
    )
    op.create_index('idx_quotes_persona_slug', 'quotes', ['persona_slug'])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS quotes")
