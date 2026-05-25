"""Add missing FK indexes for query performance

Revision ID: 015_add_fk_indexes
Revises: 014_user_oauth_cols
Create Date: 2026-05-25
"""
from alembic import op


revision = '015_add_fk_indexes'
down_revision = '014_user_oauth_cols'
branch_labels = None
depends_on = None


# (table, column) tuples — all FK columns in user-facing tables that
# lacked a supporting index as of audit 2026-05-25. Excludes storage.*
# (Supabase internal) and any FK already covered by a composite index.
_FK_INDEXES = [
    ('subscriptions', 'user_id'),
    ('conversations', 'persona_id'),
    ('conversations', 'source_saved_line_id'),
    ('messages', 'user_id'),
    ('memory_entries', 'conversation_id'),
    ('memory_entries', 'persona_id'),
    ('insights', 'conversation_id'),
    ('insights', 'persona_id'),
    ('insights', 'user_id'),
    ('rituals', 'persona_id'),
    ('user_ritual_completions', 'conversation_id'),
    ('user_ritual_completions', 'ritual_id'),
    ('user_ritual_completions', 'user_id'),
    ('safety_events', 'conversation_id'),
    ('safety_events', 'message_id'),
    ('safety_events', 'user_id'),
    ('saved_lines', 'persona_id'),
    ('scheduled_emails', 'persona_id'),
    ('scheduled_emails', 'saved_line_id'),
    ('scheduled_emails', 'user_id'),
]


def upgrade() -> None:
    for table, column in _FK_INDEXES:
        op.create_index(
            f'ix_{table}_{column}',
            table,
            [column],
            if_not_exists=True,
        )


def downgrade() -> None:
    for table, column in _FK_INDEXES:
        op.drop_index(
            f'ix_{table}_{column}',
            table_name=table,
            if_exists=True,
        )
