"""Deleting a conversation stops destroying what the room learned in it

Revision ID: 057_memory_conv_fk_set_null
Revises: 056_deletion_fks
Create Date: 2026-09-03

Memory-v2 Ruling #7c, as widened by O-3 (MEMORY_V2_DESIGN_2026-09-03 §0b, §4a).

WHAT CHANGES. `memory_entries.conversation_id` and `insights.conversation_id`
move from ON DELETE CASCADE to ON DELETE SET NULL. `DELETE /conversations/{id}`
is a hard delete (routers/conversations.py), so today tidying an old thread
silently destroys the memories extracted from it and the insights raised in it.
After this, the conversation goes and the derived rows survive with a NULL
conversation_id.

013 IS WHERE THE CATEGORIES COME FROM, and this migration moves two tables
between them. That migration set four conversation FKs at once and split them
in two, with the reasoning written into its comments:

    CASCADE  — "derived data, safe to lose with parent"
               memory_entries, insights
    SET NULL — "preserve audit trail row, null out the conversation ref"
               safety_events
             — "preserve activity log row, null out the conversation ref"
               user_ritual_completions

The CASCADE reasoning was sound for a subsystem whose only job was to help the
next turn in the same conversation. It is no longer what these rows are: memory
is the spine of chat recall, the weekly and monthly letters, You-vs-You and the
recurrence detector, and the insights are the "what the room noticed" block in
every letter. The explore copy tells the person the room carries what matters
into later conversations. So both tables belong in the SECOND category now, for
exactly the reason 013 gave for putting safety_events there: the row outlives
the thread it came from.

CONSTRAINT NAMES. 001 created both FKs inline and unnamed, so Postgres
auto-named them `<table>_<column>_fkey`; 013 then pinned those names explicitly
by dropping and re-adding them with an ADD CONSTRAINT clause. The names below
are therefore the ones that exist, on the evidence that 013's own DROPs have
already run against production. No IF EXISTS: a wrong name must fail loudly
here, not silently leave CASCADE in place, which is the one outcome this
migration exists to prevent.

Both columns are already nullable, so SET NULL needs no type change — the same
property 056 relied on for safety_events.

DOWN RESTORES THE CLAUSE, NOT THE DATA. Re-applying CASCADE does not re-attach
rows already orphaned by an UP-era conversation delete, and a later conversation
delete will not remove them either, because their conversation_id is NULL. The
downgrade is therefore honest about the schema and lossy in effect. That is
inherent to the change, not a defect in this file.

No table is created here, so C-05 (enable RLS on new public tables) does not
apply — 052 already enabled RLS on both memory_entries and insights, and this
migration only alters a constraint on each.

A KNOWN CONSEQUENCE, recorded so it is not discovered later: after this, no
code path in the product ever deactivates a memory row. The weekly stale-memory
cron was deleted in #599 (it could never match a row — its 0.6 confidence
cutoff sat below every writer's floor), and the conversation cascade was the
only forgetting mechanism that actually fired. Accepted for v1 per O-4, tracked
as a tech-debt candidate.
"""
from alembic import op

revision = '057_memory_conv_fk_set_null'
down_revision = '056_deletion_fks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # memory_entries.conversation_id — SET NULL: preserve what was learned,
    # null out the conversation ref.
    op.execute("ALTER TABLE memory_entries DROP CONSTRAINT memory_entries_conversation_id_fkey")
    op.execute(
        "ALTER TABLE memory_entries ADD CONSTRAINT memory_entries_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL"
    )

    # insights.conversation_id — SET NULL: preserve what the room noticed,
    # null out the conversation ref.
    op.execute("ALTER TABLE insights DROP CONSTRAINT insights_conversation_id_fkey")
    op.execute(
        "ALTER TABLE insights ADD CONSTRAINT insights_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Reverse order of upgrade(). Restores the CASCADE clause only — rows
    # orphaned while the SET NULL clause was live stay orphaned, and a later
    # conversation delete will not collect them, because their conversation_id
    # is already NULL.
    op.execute("ALTER TABLE insights DROP CONSTRAINT insights_conversation_id_fkey")
    op.execute(
        "ALTER TABLE insights ADD CONSTRAINT insights_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )

    op.execute("ALTER TABLE memory_entries DROP CONSTRAINT memory_entries_conversation_id_fkey")
    op.execute(
        "ALTER TABLE memory_entries ADD CONSTRAINT memory_entries_conversation_id_fkey "
        "FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE"
    )
