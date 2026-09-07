"""Allow 'failed' as a weekly_letters.status

Revision ID: 058_letter_failed_status
Revises: 057_memory_conv_fk_set_null
Create Date: 2026-09-07

Both letter generators already WRITE status='failed' — arq_worker.py:1712
(weekly) and :2096 (monthly) — when the model's reply and its one retry are
both unparseable JSON. The CHECK created by 022 permits only
('generated', 'empty', 'suppressed') and no migration has widened it since, so
that INSERT raises CheckViolation on commit, the logger.error immediately after
it never runs, and the failure surfaces as a generic task error.

The comment above that write reads "Write the failure down: silence is what cost
us four days last time." It has been silent since it shipped. This migration is
what makes it work.

TWO CONSEQUENCES THIS UNBLOCKS, both already coded and inert today:
  - the generators' dedup excludes status='failed' so a lost letter does not
    permanently block a re-run for that period (arq_worker.py:1427, :1826);
  - the list endpoint filters status != 'failed' so an operator-visible failure
    row never reaches a reader (routers/weekly_letters.py; the compiled-SQL
    assertion at tests/routers/test_weekly_letters.py:204 has pinned this all
    along, against a value the schema made impossible).
Neither is changed here. They simply begin to mean something.

022 declared the constraint INLINE on the column rather than at table level.
Postgres stores that as an ordinary named table constraint, so the ALTER below
is the plain drop-and-re-add — no special handling, noted only so a reader
comparing this to 022 does not have to wonder.

The drop is bare, without IF EXISTS, following 024 and 057: a wrong constraint
name must fail loudly here rather than silently leave the old CHECK in place,
which is the one outcome this migration exists to prevent.

DOWNGRADE CAVEAT, exactly as 024 records for saved_lines: if any
weekly_letters.status='failed' rows exist, the downgrade's narrower CHECK will
fail to validate. That is intentional — a downgrade past this revision must
first reconcile those rows.

No table is created here, so C-05 (enable RLS on new public tables) does not
apply — 052 already enabled RLS on weekly_letters, and this migration only
alters a constraint on it.
"""
from alembic import op

revision = '058_letter_failed_status'
down_revision = '057_memory_conv_fk_set_null'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE weekly_letters DROP CONSTRAINT ck_weekly_letters_status")
    op.execute("""
        ALTER TABLE weekly_letters
          ADD CONSTRAINT ck_weekly_letters_status
          CHECK (status IN ('generated', 'empty', 'suppressed', 'failed'))
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE weekly_letters DROP CONSTRAINT ck_weekly_letters_status")
    op.execute("""
        ALTER TABLE weekly_letters
          ADD CONSTRAINT ck_weekly_letters_status
          CHECK (status IN ('generated', 'empty', 'suppressed'))
    """)
