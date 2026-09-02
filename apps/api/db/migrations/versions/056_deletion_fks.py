"""Make account deletion possible at the database level

Revision ID: 056_deletion_fks
Revises: 055_billing_lifecycle
Create Date: 2026-09-02

The privacy policy promises erasure (GDPR Art. 17), and until now
`DELETE FROM users` could not run: four foreign keys pointing at users and
messages carried no ON DELETE clause, so Postgres defaulted them to NO ACTION
and the delete aborted. Twenty-one other user-owned tables already CASCADE;
these four were simply never given a clause.

The invariant belongs in the DATABASE, not in one service function that has to
remember the right order. After this, deletion is a single statement and the
schema enforces what happens to every dependent row.

  messages.user_id                  -> CASCADE
      The user's own messages. They already cascade through
      conversations.user_id; this closes the direct path so the outcome does
      not depend on every message belonging to a conversation.

  user_ritual_completions.user_id   -> CASCADE
      Personal activity log. 013 set this table's conversation_id to SET NULL
      to preserve the row when a conversation goes; the row does not survive
      its USER, because without a user it logs nothing about anybody.

  safety_events.user_id             -> SET NULL
  safety_events.message_id          -> SET NULL
      NOT deleted, deliberately. These are the self-harm and crisis audit
      trail, and 013 already established the intent for this table by choosing
      SET NULL for conversation_id: "preserve audit trail row, null out the
      conversation ref". A row whose user_id, conversation_id and message_id
      are all NULL is no longer personal data, so Art. 17 is satisfied by
      anonymisation rather than destruction, and the safety record survives.

      This holds ONLY because raw_flags carries no user text. Audited at
      2026-09-02: services/safety_service.py stores the MATCHER phrase from its
      own module-level constants (RISK_HIGH 23, RISK_MEDIUM 15,
      OUTPUT_RISK_PHRASES 13, and an inline low-signal list) — never the user's
      sentence, never a surrounding excerpt or match span. safety_event_log.py
      writes {"flags": [...those constants...], "trigger": <one constant|None>}.
      If that ever changes, these rows stop being anonymous and this decision
      has to be revisited; tests/test_account_deletion.py pins the property.

Both columns are already nullable, so SET NULL needs no type change.

No table is created here, so C-05 (enable RLS on new public tables) does not
apply — every table touched already has RLS from 052.
"""
from alembic import op

revision = '056_deletion_fks'
down_revision = '055_billing_lifecycle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # messages.user_id — CASCADE
    op.execute("ALTER TABLE messages DROP CONSTRAINT messages_user_id_fkey")
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    )

    # user_ritual_completions.user_id — CASCADE
    op.execute(
        "ALTER TABLE user_ritual_completions "
        "DROP CONSTRAINT user_ritual_completions_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE user_ritual_completions ADD CONSTRAINT "
        "user_ritual_completions_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
    )

    # safety_events.user_id — SET NULL (anonymise, do not delete)
    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_user_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"
    )

    # safety_events.message_id — SET NULL. This one is why the delete failed even
    # for a user with no ritual completions: the messages being cascade-deleted
    # were referenced here under NO ACTION.
    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_message_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_message_id_fkey "
        "FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Restores the NO ACTION default, which is the state in which account
    # deletion is impossible. Reverse order of upgrade().
    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_message_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_message_id_fkey "
        "FOREIGN KEY (message_id) REFERENCES messages(id)"
    )

    op.execute("ALTER TABLE safety_events DROP CONSTRAINT safety_events_user_id_fkey")
    op.execute(
        "ALTER TABLE safety_events ADD CONSTRAINT safety_events_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id)"
    )

    op.execute(
        "ALTER TABLE user_ritual_completions "
        "DROP CONSTRAINT user_ritual_completions_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE user_ritual_completions ADD CONSTRAINT "
        "user_ritual_completions_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id)"
    )

    op.execute("ALTER TABLE messages DROP CONSTRAINT messages_user_id_fkey")
    op.execute(
        "ALTER TABLE messages ADD CONSTRAINT messages_user_id_fkey "
        "FOREIGN KEY (user_id) REFERENCES users(id)"
    )
