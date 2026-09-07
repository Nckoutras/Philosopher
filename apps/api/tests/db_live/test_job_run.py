"""job_run exists, constrains what it should, and the model agrees with it.

Migration 059. The table records one row per scheduled run — which job, which
period, how it ended — so that a dispatch which never fires leaves evidence
behind. Nothing writes it yet (PR-B does); everything asserted here is a property
of the SCHEMA, which is exactly why it needs a live server.

WHY A LIVE DATABASE. Three of the four rules under test are enforced by Postgres
and by nothing else: a UNIQUE index, a CHECK constraint, and the RLS flag. A
mocked session accepts every one of them silently. The fourth — the "unfinished
run" query — is a claim about what SQL returns, and the query result IS the
behaviour.

FIRST RLS ASSERTION IN THIS SUITE. 052_enable_rls and 055_billing_lifecycle both
state a verified RLS posture (enabled, zero policies, no FORCE) and nothing in
CI has ever checked one; `grep -rn relrowsecurity apps/api/tests` returned
nothing before this file. C-05 makes that posture a rule for every new public
table, so it gets an assertion here rather than another prose claim.

ONE VIOLATION PER TEST, AND THE RAISE IS LAST. A constraint violation aborts the
surrounding transaction, and the db fixture hands every test a transaction that
is rolled back whole. So nothing can be asserted against the database after an
expected raise — each violation gets its own test function, following the shape
test_letter_failed_status.py established.
"""
import re
import uuid

import pytest
from sqlalchemy import text

from models import JobRun

CONSTRAINT = "ck_job_run_status"
UNIQUE_INDEX = "uq_job_run_name_key"

# The vocabulary 059 creates. Written out rather than derived from either the
# model or the live constraint — an assertion that computed its expectation from
# the thing under test could not fail. Third independent statement of the rule.
EXPECTED_STATUSES = {"running", "succeeded", "failed"}


def _literals(sql_text: str) -> set[str]:
    """Every single-quoted literal in a CHECK expression, however it is rendered."""
    return set(re.findall(r"'([^']*)'", sql_text))


async def _open_run(db, job_name: str, run_key: str, status: str = "running") -> str:
    """Open a run the way PR-B will: started, unfinished, counts not yet known."""
    run_id = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO job_run (id, job_name, run_key, status) "
            "VALUES (:id, :job, :key, :st)"
        ),
        {"id": run_id, "job": job_name, "key": run_key, "st": status},
    )
    return run_id


# ── 1. The idempotency key ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_runs_of_the_same_job_for_the_same_period_collide(db):
    """THE POINT OF THE TABLE. (job_name, run_key) is unique, so a second
    dispatch for a period already covered is a constraint violation rather than
    a judgement call at the call site. PR-C's catch-up is invoked with an
    explicit run_key (R8); this index is what makes running it twice safe."""
    await _open_run(db, "weekly_letter", "2026-W36")
    await db.flush()

    with pytest.raises(Exception) as excinfo:
        await _open_run(db, "weekly_letter", "2026-W36")
        await db.flush()

    assert UNIQUE_INDEX in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_same_period_under_a_different_job_is_allowed(db):
    """The key is (job, period), not period alone. A monthly run and a weekly run
    can legitimately carry keys for overlapping calendar time, and two different
    jobs must never block each other."""
    await _open_run(db, "weekly_letter", "2026-W36")
    await _open_run(db, "monthly_letter", "2026-W36")
    await db.flush()

    got = (await db.execute(
        text("SELECT count(*) FROM job_run WHERE run_key = :key"), {"key": "2026-W36"},
    )).scalar_one()
    assert got == 2


# ── 2. The status vocabulary ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_three_statuses_write(db):
    for i, status in enumerate(sorted(EXPECTED_STATUSES)):
        await _open_run(db, "weekly_letter", f"2026-W{30 + i}", status=status)
    await db.flush()

    got = (await db.execute(
        text("SELECT count(DISTINCT status) FROM job_run"),
    )).scalar_one()
    assert got == len(EXPECTED_STATUSES)


@pytest.mark.asyncio
async def test_the_status_check_rejects_done(db):
    """'done' is the plausible wrong word — near-synonymous with 'succeeded' and
    the one a future caller is most likely to reach for. Without this assertion,
    "the CHECK permits three values" and "there is no CHECK" would look identical
    to this file."""
    with pytest.raises(Exception) as excinfo:
        await _open_run(db, "weekly_letter", "2026-W36", status="done")
        await db.flush()

    assert CONSTRAINT in str(excinfo.value)


# ── 3. The crash signature ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_unfinished_run_query_finds_the_crashed_row_only(db):
    """finished_at IS NULL AND status='running' is the query an operator runs to
    find a run that died mid-flight. It must return the run nobody closed and
    NOT the one that completed — which is why finished_at carries no default: a
    default would close every row at insert and erase the only evidence."""
    crashed = await _open_run(db, "weekly_letter", "2026-W35")
    finished = await _open_run(db, "weekly_letter", "2026-W36")
    await db.execute(
        text(
            "UPDATE job_run SET status = 'succeeded', finished_at = now(), "
            "candidate_count = 12, selected_count = 9, enqueued_count = 9 "
            "WHERE id = :id"
        ),
        {"id": finished},
    )
    await db.flush()

    # asyncpg decodes uuid columns to uuid.UUID and _open_run hands back str, so
    # normalize here or the comparison fails on type rather than on content
    # (test_memory_recall_and_cascades.py:701).
    rows = [str(r) for r in (await db.execute(
        text(
            "SELECT id FROM job_run "
            "WHERE finished_at IS NULL AND status = 'running'"
        ),
    )).scalars().all()]

    assert rows == [crashed]


@pytest.mark.asyncio
async def test_the_counts_distinguish_never_counted_from_counted_none(db):
    """NULL is "the run never got that far"; 0 is "it counted, and there were
    none". Collapsing them would make "nobody qualified this week" and "dispatch
    died before it looked" read identically — the distinction the three nullable
    counts exist for (R3)."""
    never = await _open_run(db, "weekly_letter", "2026-W35")
    counted = await _open_run(db, "weekly_letter", "2026-W36")
    await db.execute(
        text(
            "UPDATE job_run SET status = 'succeeded', finished_at = now(), "
            "candidate_count = 0, selected_count = 0, enqueued_count = 0 "
            "WHERE id = :id"
        ),
        {"id": counted},
    )
    await db.flush()

    # str() on the key: asyncpg decodes uuid columns to uuid.UUID, so a dict
    # keyed by the raw value would not answer to the str ids _open_run returned
    # (test_memory_recall_and_cascades.py:701).
    got = {str(k): v for k, v in (await db.execute(
        text("SELECT id, candidate_count FROM job_run"),
    )).all()}

    assert got[never] is None
    assert got[counted] == 0


# ── 4. RLS (C-05) ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_row_level_security_is_enabled_on_job_run(db):
    """C-05: a migration that creates a public table enables RLS in the SAME
    migration. The API connects as the table owner and owners bypass RLS, so
    this never gates the API; what it closes is the PostgREST
    anon/authenticated surface, where an unauthenticated caller would otherwise
    read every row of a new table."""
    enabled = (await db.execute(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'job_run'"),
    )).scalar_one()
    assert enabled is True


@pytest.mark.asyncio
async def test_job_run_has_no_rls_policies(db):
    """ZERO POLICIES IS THE POSTURE, not an omission. 052_enable_rls reproduces
    production exactly — enabled, no policies, no FORCE — under which the owner
    still sees everything and every non-owner role sees nothing. Adding policies
    is a separate decision requiring its own review. Asserted so that a
    well-meaning later `CREATE POLICY` has to argue with a test first."""
    policies = (await db.execute(
        text("SELECT count(*) FROM pg_policies WHERE tablename = 'job_run'"),
    )).scalar_one()
    assert policies == 0


# ── 5. The model agrees with the database ───────────────────────────────────

@pytest.mark.asyncio
async def test_the_model_constraint_matches_the_live_constraint(db):
    """MODEL/MIGRATION DRIFT GUARD, the same shape as
    test_letter_failed_status.py.

    Every test above proves the MIGRATION and nothing else: a CheckConstraint in
    __table_args__ is DDL metadata, not an ORM-enforced rule, so 059 applied
    against an unchanged models/__init__.py would leave them all green while the
    two halves disagreed.

    Compared as SETS OF LITERALS. Postgres rewrites CHECK text on storage into
    something like
        CHECK (((status)::text = ANY ((ARRAY['running'::character varying, ...])::text[])))
    while the model declares
        status IN ('running', 'succeeded', 'failed')
    Those never match textually. The rule they encode is the set of permitted
    values, and that is what is compared.
    """
    live_def = (await db.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = :name AND conrelid = 'job_run'::regclass"
        ),
        {"name": CONSTRAINT},
    )).scalar_one()

    model_constraint = next(
        c for c in JobRun.__table__.constraints
        if getattr(c, "name", None) == CONSTRAINT
    )
    model_def = str(model_constraint.sqltext)

    live_values = _literals(live_def)
    model_values = _literals(model_def)

    assert live_values == EXPECTED_STATUSES, f"live constraint: {live_def}"
    assert model_values == EXPECTED_STATUSES, f"model constraint: {model_def}"
    assert live_values == model_values


# ── 6. weekly_letters.email_suppressed_reason ───────────────────────────────

@pytest.mark.asyncio
async def test_email_suppressed_reason_is_nullable_and_holds_a_reason(db):
    """Additive and nullable, no backfill: NULL means the email was sent, or that
    the row predates the column. Both states must be writable, and a 32-char
    value must fit — the longest reason PR-B writes is 'already_sent' (12), so
    the width has a wide margin, but the boundary is asserted rather than
    assumed.

    NO CHECK IS ASSERTED HERE, deliberately (R2a). The five reasons are an
    application vocabulary, pinned in PR-B's test where the guard that writes
    them lives, so that adding a sixth stays a code change and never becomes a
    production migration. If this column ever grows a CHECK, that is a decision
    that should break this comment first.
    """
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )

    null_letter, reason_letter = str(uuid.uuid4()), str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO weekly_letters "
            "  (id, user_id, period_start, period_end, status, kind) "
            "VALUES (:id, :uid, now() - interval '7 days', now(), 'generated', 'weekly')"
        ),
        {"id": null_letter, "uid": uid},
    )
    await db.execute(
        text(
            "INSERT INTO weekly_letters "
            "  (id, user_id, period_start, period_end, status, kind, "
            "   email_suppressed_reason) "
            "VALUES (:id, :uid, now() - interval '14 days', now(), 'generated', "
            "        'weekly', :reason)"
        ),
        {"id": reason_letter, "uid": uid, "reason": "x" * 32},
    )
    await db.flush()

    # str() on the key, as above: asyncpg decodes uuid columns to uuid.UUID and
    # the ids here are str (test_memory_recall_and_cascades.py:701).
    got = {str(k): v for k, v in (await db.execute(
        text("SELECT id, email_suppressed_reason FROM weekly_letters WHERE user_id = :uid"),
        {"uid": uid},
    )).all()}

    assert got[null_letter] is None
    assert got[reason_letter] == "x" * 32
