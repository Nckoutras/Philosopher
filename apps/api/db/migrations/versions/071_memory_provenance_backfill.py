"""Backfill 070's columns on the rows that predate it

Revision ID: 071_memory_provenance_backfill
Revises: 070_memory_epistemic_core
Create Date: 2026-10-02

MEM2-A. A DATA migration, kept separate from 070's schema change. Every statement
is guarded by `IS NULL`, so a second run changes nothing and a row a writer
already stamped after 070 is never overwritten.

WHY A MIGRATION AND NOT A SCRIPT. A script is a manual step against production,
and a manual step is a habit with a person in it (CLAUDE.md, 2026-09-14). A
migration also runs on CI's database and on any database rebuilt from migrations,
so a rebuilt database comes up with the same provenance production has.

THE MAPPING, from entry_type, which is the only evidence these rows carry:

  provenance
    stated, counterview_belief        -> user_stated      (the person's own words)
    self_portrait, onboarding_profile -> user_selected    (the person's tap/answer)
    EVERYTHING ELSE                   -> system_inferred
  The last line is a CATCH-ALL, deliberately, for the reason memory_service gives
  for its recall lanes: entry_type is not validated on write, and production holds
  'goal', 'concern' and 'grief' rows that no prompt ever asked for. Every such row
  came from the chat extractor, so it is system-inferred by construction; an
  allow-list would leave them NULL. self_portrait_shift is in the catch-all by
  founder ruling: provenance records whose claim the row asserts, not whose
  grammar, and a shift is a claim the system composed about two taps. `stated`
  rows are third-person rewrites that preserve the person's own claim, so they
  stay user_stated.

  source_surface
    self_portrait, self_portrait_shift -> 'self_portrait'
    onboarding_profile                 -> 'onboarding'
    counterview_belief                 -> 'counterview_belief'
    stated                             -> left NULL. Five surfaces write `stated`
                                          and the distill task logged which one
                                          without storing it. Not recoverable, and
                                          a guess would be a fabricated record.
    everything else                    -> 'chat' (the extractor is its only writer)

  inactive_reason
    every inactive row -> 'superseded'. Verified against production on 2026-10-02
    before writing this: 22 inactive rows (17 onboarding_profile, 4 self_portrait,
    1 self_portrait_shift), every one with an active successor of the same type,
    and the same question key for the portrait rows. The only writers that set
    is_active=false before 070 were the two re-seed tasks and DELETE /memory, and
    DELETE /memory has never had a web caller (TD-111).

  supersedes_memory_id
    self_portrait and self_portrait_shift only: within (user, entry_type,
    source_turn) — source_turn is the per-question key for these two types — each
    row supersedes the row immediately before it by (created_at, id). A question
    answered three times becomes a chain r3 -> r2 -> r1, which is what the
    re-seed task now writes going forward. onboarding_profile stays NULL: a
    re-seed replaces a set with a set and has no one-for-one pairing.

source_message_ids is NOT backfilled (MEM2 ruling R9). Legacy chat rows carry a
conversation and a pair count, not message ids, and an approximation from those
would be a guess stored as a fact.

DOWNGRADE IS A NO-OP. After this has run, writers stamp the same columns at
write time, so a downgrade could not tell backfilled values from written ones,
and clearing them would destroy real records. 070's downgrade drops the columns,
which is the reversal that is actually safe.

Self-contained per C-01: no application import.
"""
from alembic import op

revision = '071_memory_provenance_backfill'
down_revision = '070_memory_epistemic_core'
branch_labels = None
depends_on = None


# Module-level so tests/db_live/test_memory_epistemic_core.py runs THESE statements,
# twice, rather than a copy that could drift from them (the RECALL_SQL / T-9
# precedent). Order matters only in that each is independent of the others.
BACKFILL_STATEMENTS = (
    """
        UPDATE memory_entries
        SET provenance = CASE
            WHEN entry_type IN ('stated', 'counterview_belief') THEN 'user_stated'
            WHEN entry_type IN ('self_portrait', 'onboarding_profile') THEN 'user_selected'
            ELSE 'system_inferred'
        END
        WHERE provenance IS NULL
    """,
    """
        UPDATE memory_entries
        SET source_surface = CASE
            WHEN entry_type IN ('self_portrait', 'self_portrait_shift') THEN 'self_portrait'
            WHEN entry_type = 'onboarding_profile' THEN 'onboarding'
            WHEN entry_type = 'counterview_belief' THEN 'counterview_belief'
            ELSE 'chat'
        END
        WHERE source_surface IS NULL
          AND entry_type <> 'stated'
    """,
    """
        UPDATE memory_entries
        SET inactive_reason = 'superseded'
        WHERE is_active = FALSE
          AND inactive_reason IS NULL
    """,
    """
        WITH chain AS (
            SELECT id,
                   LAG(id) OVER (
                       PARTITION BY user_id, entry_type, source_turn
                       ORDER BY created_at, id
                   ) AS prev_id
            FROM memory_entries
            WHERE entry_type IN ('self_portrait', 'self_portrait_shift')
              AND source_turn IS NOT NULL
        )
        UPDATE memory_entries m
        SET supersedes_memory_id = chain.prev_id
        FROM chain
        WHERE m.id = chain.id
          AND chain.prev_id IS NOT NULL
          AND m.supersedes_memory_id IS NULL
    """,
)


def upgrade():
    for statement in BACKFILL_STATEMENTS:
        op.execute(statement)


def downgrade():
    pass
