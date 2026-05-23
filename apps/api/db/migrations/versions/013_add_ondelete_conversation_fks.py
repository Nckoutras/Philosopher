"""Add ondelete clauses to conversation FK references

Revision ID: 013_add_ondelete_conversation_fks
Revises: 012_scheduled_emails
Create Date: 2026-05-23
"""
from alembic import op

revision = '013_add_ondelete_conversation_fks'
down_revision = '012_scheduled_emails'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # memory_entries — CASCADE: derived data, safe to lose with parent
    op.execute("ALTER TABLE memory_entries DROP CONSTRAINT memory_entries_conversation_id_fkey")
    op.execute(
        "ALTER TABLE memory_entries ADD CONSTRAINT memory_entries_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )

    # insights — CASCADE: derived data, safe to lose with parent
    op.execute("ALTER TABLE insights DROP CONSTRAINT insights_conversation_id_fkey")
    op.execute(
        "ALTER TABLE insights ADD CONSTRAINT insights_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )

    # safety_events — SET NULL: preserve audit trail row, null out the conversation ref
    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_conversation_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL"
    )

    # user_ritual_completions — SET NULL: preserve activity log row, null out the conversation ref
    op.execute(
        "ALTER TABLE user_ritual_completions DROP CONSTRAINT user_ritual_completions_conversation_id_fkey"
    )
    op.execute(
        "ALTER TABLE user_ritual_completions ADD CONSTRAINT user_ritual_completions_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_ritual_completions DROP CONSTRAINT user_ritual_completions_conversation_id_fkey"
    )
    op.execute(
        "ALTER TABLE user_ritual_completions ADD CONSTRAINT user_ritual_completions_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id)"
    )

    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_conversation_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id)"
    )

    op.execute("ALTER TABLE insights DROP CONSTRAINT insights_conversation_id_fkey")
    op.execute(
        "ALTER TABLE insights ADD CONSTRAINT insights_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id)"
    )

    op.execute(
        "ALTER TABLE memory_entries DROP CONSTRAINT memory_entries_conversation_id_fkey"
    )
    op.execute(
        "ALTER TABLE memory_entries ADD CONSTRAINT memory_entries_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id)"
    )
