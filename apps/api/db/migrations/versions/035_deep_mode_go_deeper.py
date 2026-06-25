"""Add conversations.deep_mode + daily_usage.go_deeper_count (go-deeper depth)

Revision ID: 035_deep_mode_go_deeper
Revises: 034_conversation_active_persona
Create Date: 2026-06-25

Additive, schema-only. Two independent columns:

- conversations.deep_mode (BOOL NOT NULL DEFAULT false): Pro-only sticky "deep
  mode". A SEPARATE flag from active_persona_id. When true AND the sender is
  Pro/premium, every normal reply is deep. All existing rows default false ⇒ no
  behavioural change; the read site is also Pro-gated so a stale true on a
  downgraded account is inert.
- daily_usage.go_deeper_count (INT NOT NULL DEFAULT 0): per-(user, persona, day)
  count of go-deepers, mirroring message_count. Drives the free 3/day go-deeper
  limit (Pro/premium unlimited).
"""
import sqlalchemy as sa
from alembic import op

revision = '035_deep_mode_go_deeper'
down_revision = '034_conversation_active_persona'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column(
        'deep_mode', sa.Boolean(), nullable=False, server_default=sa.false(),
    ))
    op.add_column('daily_usage', sa.Column(
        'go_deeper_count', sa.Integer(), nullable=False, server_default='0',
    ))


def downgrade() -> None:
    op.drop_column('daily_usage', 'go_deeper_count')
    op.drop_column('conversations', 'deep_mode')
