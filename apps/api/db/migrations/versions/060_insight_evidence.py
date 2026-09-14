"""Add insights.evidence JSONB — the rows a recurrence insight was derived from

Revision ID: 060_insight_evidence
Revises: 059_job_run
Create Date: 2026-09-14

WHAT THIS CLOSES. `detect_recurrence` finds the memory rows that echo what the
person just raised, then throws them away: `source_count = len({...}) + 1`
reduced the whole match set to an integer, and the shift classifier's two-sided
comparison survived only as its verdict. The rows that justified the card were
unrecoverable the moment it was written.

It was worse than discarding. The detector's SELECT fetched `content`,
`conversation_id` and `score` — never `id` — so it did not know the identities
it was collapsing. This is the column those identities land in.

WHY ONE COLUMN AND NOT TWO. The "earlier" side of the shift comparison IS the
match set (`prior_text` is built from `prior_matches[:5]`), and the "now" side is
the entry that triggered detection. They are one fact rendered twice, so storing
them in two columns would duplicate and then drift.

NO FOREIGN KEYS, DELIBERATELY, and the payload carries a text snippet beside each
id. An insight is a HISTORICAL RECORD: a memory row can be deactivated, and
migration 057 lets a conversation be deleted out from under one. A citation that
vanished when its source did would defeat the point of citing. The snippet means
the card still renders what it was built on; `insights.user_id` is ON DELETE
CASCADE, so an erasure still takes the whole thing and the snippet adds no new
surface.

SHAPE (written by services/memory_service.py:detect_recurrence):

    {
      "recurring_entry": {"memory_entry_id": …, "text": …, "conversation_id": …},
      "prior_matches": [
        {"memory_entry_id": …, "text": …, "conversation_id": …, "score": 0.83}
      ],
      "shown_to_classifier": 5,
      "detector": {"threshold": 0.75, "limit": 20, "window": null}
    }

`prior_matches` holds EVERY match above the bar; `shown_to_classifier` records
how many of them the classifier actually saw. Both facts matter and one field
recovers neither. `detector` freezes the bar at write time because
RECURRENCE_SIM_THRESHOLD is a ship-and-tune value — a citation whose threshold is
unrecoverable is uninterpretable. `"window": null` is reserved for the
period-filtered caller; the shape will not change again when it arrives.

NULL MEANS TWO DIFFERENT THINGS, and the second is the one that will be
forgotten:

  1. Written before this migration. Those insights have no evidence and CANNOT BE
     GIVEN ANY. The embedding neighbourhood moves as new memories land, so
     re-deriving a match set would return a different answer than the one that
     actually justified the card — a fabricated citation, which is worse than an
     absent one. There is no backfill and there cannot be.

  2. Not a recurrence insight at all, and NULL is correct for it forever. The
     signal path (memory_service.py, `source_count=None`) has no match set by
     construction. So `evidence IS NULL` never means "old row" on its own, and
     any reader or test must scope on the recurrence path rather than on the
     column being populated.

ONE BLIND SPOT INHERITED FROM THE DETECTOR, recorded here so it is not
rediscovered from a db_live test. The recurrence query excludes the current
thread with `AND conversation_id != :cid`; for an ORPHANED memory (NULL
conversation_id, possible since 057) that predicate is NULL rather than TRUE, so
SQL's three-valued logic drops the row. Orphans are invisible as recurrence
evidence, which is the safe direction and is what keeps `source_count` honest —
and it means `prior_matches` inherits the same absence. Asserted in
tests/db_live/test_memory_recall_and_cascades.py::
test_an_orphaned_memory_is_not_counted_as_a_prior_conversation.

C-05 (RLS on new tables) does not apply here: this migration creates NO table. It
adds a column to `insights`, which already has ROW LEVEL SECURITY enabled by
052_enable_rls. Nothing extra is needed, and nothing about the RLS posture
changes.

DOWNGRADE drops the column. The evidence is not recoverable afterwards — see
NULL meaning 1 — so a downgrade is a one-way loss of citations for every insight
written while this was live. Additive and safe to apply; not free to revert.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '060_insight_evidence'
down_revision = '059_job_run'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('insights', sa.Column('evidence', JSONB, nullable=True))


def downgrade():
    op.drop_column('insights', 'evidence')
