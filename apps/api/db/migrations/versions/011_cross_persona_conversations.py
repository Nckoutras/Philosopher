"""Cross-persona conversations — source_saved_line_id and source_persona_slug

Revision ID: 011_cross_persona_conversations
Revises: 010_daily_questions
Create Date: 2026-05-19
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision = '011_cross_persona_conversations'
down_revision = '010_daily_questions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column(
        'source_saved_line_id',
        UUID(as_uuid=False),
        sa.ForeignKey('saved_lines.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.add_column('conversations', sa.Column(
        'source_persona_slug',
        sa.String(100),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('conversations', 'source_persona_slug')
    op.drop_column('conversations', 'source_saved_line_id')
