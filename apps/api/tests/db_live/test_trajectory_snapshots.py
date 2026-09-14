"""trajectory_snapshots exists, constrains what it should, and the prior-snapshot
lookup returns what the code assumes.

Migration 061. Two kinds of claim need a live server and nothing else can carry
them:

  THE SCHEMA RULES — a UNIQUE index, a CHECK constraint, an ON DELETE CASCADE
  and the RLS flag. A mocked session accepts every one of them silently, which
  is exactly why the mocked-layer file (tests/workers/test_trajectory_snapshot.py)
  asserts the model's DDL metadata instead and leaves the enforcement here.

  THE PRIOR-SNAPSHOT WHERE CLAUSE — "the most recent snapshot strictly before
  this period, ignoring failed ones". The query result IS the behaviour: a fake
  returns whatever the test author put in it, so it can only ever agree.
  changes_since_prior is built on top of this row, so picking the wrong one
  would produce a diff that is well-formed and false.

TIMESTAMPTZ PARAMS ARE BOUND FROM datetime OBJECTS, NEVER FROM ISO STRINGS
(TD-76 / #645). asyncpg rejects a string for a timestamptz parameter, and the
period columns here are the ones that would take one — the whole file is bounds
arithmetic. Every inserted value below is a tz-aware datetime.

EVERY NOT NULL COLUMN IS SET ON EVERY INSERT. user_id, period_start, period_end,
kind, status and created_at are all NOT NULL; created_at and kind carry server
defaults and the rest do not. The helper sets all of them it must, so a failure
here is about the rule under test rather than about a column nobody listed.

ONE VIOLATION PER TEST, AND THE RAISE IS LAST. A constraint violation aborts the
surrounding transaction and the db fixture hands every test a transaction that
is rolled back whole, so nothing can be asserted after an expected raise. Shape
follows test_job_run.py.
"""
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from models import TrajectorySnapshot

CONSTRAINT = "ck_trajectory_snapshots_status"
UNIQUE_INDEX = "uq_trajectory_snapshots_user_period_kind"

# The vocabulary 061 creates. Written out rather than derived from the model or
# from the live constraint — an assertion that computed its expectation from the
# thing under test could not fail. Third independent statement of the rule.
EXPECTED_STATUSES = {"generated", "empty", "failed"}

# Mondays. period_start is always an ISO week's Monday 00:00Z, because
# letter_dispatch.week_period puts it there.
W36 = datetime(2026, 8, 31, tzinfo=timezone.utc)
W37 = datetime(2026, 9, 7, tzinfo=timezone.utc)
W38 = datetime(2026, 9, 14, tzinfo=timezone.utc)


def _literals(sql_text: str) -> set[str]:
    """Every single-quoted literal in a CHECK expression, however it is rendered."""
    return set(re.findall(r"'([^']*)'", sql_text))


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _snapshot(db, user_id: str, period_start: datetime, *,
                    status: str = "generated", kind: str = "weekly",
                    anchors=()) -> str:
    """Write one snapshot the way the job writes it.

    period_start / period_end are datetime OBJECTS. They are the timestamptz
    parameters this file exists to bind correctly.
    """
    sid = str(uuid.uuid4())
    payload = {
        "version": 1,
        "recurring_questions": [
            {
                "memory_entry_id": str(uuid.uuid4()),
                "text": "I keep circling the same decision",
                "conversation_id": None,
                "match_count": len(anchors),
                "top_score": 0.9,
                "prior_matches": [
                    {"memory_entry_id": a, "text": "earlier",
                     "conversation_id": None, "score": 0.9}
                    for a in anchors
                ],
            }
        ] if anchors else [],
        "changes_since_prior": None,
        "changes_since_prior_reason": "no_prior_snapshot",
    }
    await db.execute(
        text(
            "INSERT INTO trajectory_snapshots "
            "(id, user_id, period_start, period_end, kind, status, payload) "
            "VALUES (:id, :uid, :ps, :pe, :kind, :st, CAST(:payload AS jsonb))"
        ),
        {
            "id": sid, "uid": user_id,
            "ps": period_start,
            "pe": period_start + timedelta(days=6, hours=23, minutes=59, seconds=59),
            "kind": kind, "st": status,
            "payload": json.dumps(payload),
        },
    )
    return sid


# ── 1. The idempotency key ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_snapshots_for_the_same_user_period_and_kind_collide(db):
    """IDEMPOTENCY LAYER 2's backstop. The task's dedup select can lose a race;
    this index is what makes losing it harmless instead of duplicating the row."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38)

    with pytest.raises(Exception) as exc:
        await _snapshot(db, user_id, W38)
    assert UNIQUE_INDEX in str(exc.value)


@pytest.mark.asyncio
async def test_the_same_period_under_a_different_kind_is_allowed(db):
    """Why `kind` is in the index at all: a later monthly cadence whose
    period_start lands on a Monday that is also a week start must not be
    rejected as a duplicate of the weekly row."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38, kind="weekly")
    await _snapshot(db, user_id, W38, kind="monthly")

    count = (await db.execute(
        text("SELECT count(*) FROM trajectory_snapshots WHERE user_id = :u"),
        {"u": user_id},
    )).scalar_one()
    assert count == 2


@pytest.mark.asyncio
async def test_two_users_may_share_a_period(db):
    """The obvious other direction — every eligible user gets a row for the same
    week, so a unique index that ignored user_id would let one user's snapshot
    block everyone else's."""
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _snapshot(db, mine, W38)
    await _snapshot(db, theirs, W38)

    count = (await db.execute(
        text("SELECT count(*) FROM trajectory_snapshots WHERE period_start = :ps"),
        {"ps": W38},
    )).scalar_one()
    assert count == 2


# ── 2. The status vocabulary ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_three_statuses_write(db):
    user_id = await _make_user(db)
    for period, status in ((W36, "generated"), (W37, "empty"), (W38, "failed")):
        await _snapshot(db, user_id, period, status=status)

    rows = (await db.execute(
        text("SELECT status FROM trajectory_snapshots WHERE user_id = :u"),
        {"u": user_id},
    )).all()
    assert {r[0] for r in rows} == EXPECTED_STATUSES


@pytest.mark.asyncio
async def test_the_status_check_rejects_suppressed(db):
    """'suppressed' is a MIRROR status, and the near-miss is the point: this
    table is column-for-column the shape of `mirrors`, so the one place the two
    vocabularies differ is the one a copy-paste would get wrong."""
    user_id = await _make_user(db)

    with pytest.raises(Exception) as exc:
        await _snapshot(db, user_id, W38, status="suppressed")
    assert CONSTRAINT in str(exc.value)


@pytest.mark.asyncio
async def test_the_model_constraint_matches_the_live_constraint(db):
    """The ORM does not evaluate a CheckConstraint on insert, so the model's copy
    could drift from the migration's and nothing would notice."""
    live = (await db.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = :name"
        ),
        {"name": CONSTRAINT},
    )).scalar_one()

    model = next(
        c for c in TrajectorySnapshot.__table__.constraints
        if getattr(c, "name", None) == CONSTRAINT
    )
    assert _literals(live) == _literals(str(model.sqltext)) == EXPECTED_STATUSES


# ── 3. RLS (C-05) ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_row_level_security_is_enabled_on_trajectory_snapshots(db):
    """C-05: a migration that creates a public table enables RLS in the same
    migration. What it closes is the PostgREST anon surface — the API connects
    as the table owner and owners bypass RLS, so it never gates the API."""
    enabled = (await db.execute(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'trajectory_snapshots'"),
    )).scalar_one()
    assert enabled is True


@pytest.mark.asyncio
async def test_trajectory_snapshots_has_no_rls_policies(db):
    """052's verified posture, and the half that is easy to lose: ENABLED with
    ZERO POLICIES denies non-owners everything. Adding a policy is a separate
    decision requiring its own review."""
    policies = (await db.execute(
        text("SELECT count(*) FROM pg_policies WHERE tablename = 'trajectory_snapshots'"),
    )).scalar_one()
    assert policies == 0


@pytest.mark.asyncio
async def test_row_level_security_is_not_forced(db):
    """NO FORCE, also part of the posture: FORCE would apply RLS to the owner
    too, and with zero policies that would lock the API out of its own table."""
    forced = (await db.execute(
        text("SELECT relforcerowsecurity FROM pg_class WHERE relname = 'trajectory_snapshots'"),
    )).scalar_one()
    assert forced is False


# ── 4. Erasure ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deleting_the_user_takes_the_snapshots(db):
    """The payload keeps denormalised snippets of the person's own words with NO
    foreign keys of its own — that is deliberate (060's reasoning) and it makes
    this CASCADE the only thing that removes them."""
    doomed = await _make_user(db)
    await _snapshot(db, doomed, W38, anchors=[str(uuid.uuid4())])

    await db.execute(text("DELETE FROM users WHERE id = :u"), {"u": doomed})

    left = (await db.execute(
        text("SELECT count(*) FROM trajectory_snapshots WHERE user_id = :u"),
        {"u": doomed},
    )).scalar_one()
    assert left == 0


# ── 5. The prior-snapshot lookup — the WHERE clause that needs live proof ────

async def _prior(db, user_id: str, period_start: datetime):
    from workers.trajectory_snapshot import _prior_snapshot

    return await _prior_snapshot(db, user_id, period_start)


@pytest.mark.asyncio
async def test_the_prior_lookup_finds_the_most_recent_earlier_week(db):
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W36)
    await _snapshot(db, user_id, W37)

    prior = await _prior(db, user_id, W38)
    assert prior is not None
    assert prior.period_start == W37


@pytest.mark.asyncio
async def test_the_prior_lookup_is_strictly_before_the_period(db):
    """The row for THIS period is not its own prior. Without the strict
    inequality a re-run over a 'failed' row would diff the week against itself
    and report zero change as fact."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38)

    assert await _prior(db, user_id, W38) is None


@pytest.mark.asyncio
async def test_the_prior_lookup_reaches_past_a_failed_week(db):
    """A 'failed' row records that we do NOT know what that week held, so
    diffing against it would compare this week to an unknown. The comparison
    reaches back to the last week we actually looked at — and the payload names
    which week that was rather than letting a reader assume it was last one."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W36, status="generated")
    await _snapshot(db, user_id, W37, status="failed")

    prior = await _prior(db, user_id, W38)
    assert prior is not None
    assert prior.period_start == W36


@pytest.mark.asyncio
async def test_an_empty_week_is_a_valid_prior(db):
    """'empty' means we looked and found nothing — a real observation, and the
    right thing to diff against. Only 'failed' is skipped."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W37, status="empty")

    prior = await _prior(db, user_id, W38)
    assert prior is not None
    assert prior.status == "empty"


@pytest.mark.asyncio
async def test_the_prior_lookup_does_not_cross_users(db):
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _snapshot(db, theirs, W37)

    assert await _prior(db, mine, W38) is None


@pytest.mark.asyncio
async def test_the_prior_lookup_does_not_cross_kinds(db):
    """A monthly snapshot is not a weekly one's predecessor; diffing across
    cadences would compare a month of anchors against a week of them."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W37, kind="monthly")

    assert await _prior(db, user_id, W38) is None


# ── 6. The payload survives the round trip ───────────────────────────────────

@pytest.mark.asyncio
async def test_the_payload_comes_back_as_a_dict_with_its_anchors(db):
    """JSONB, not text: step D reads this back as structure. And the anchors are
    plain ids with snippets beside them — no foreign key, so nothing here can be
    broken by a memory row being deactivated or a conversation deleted (057)."""
    user_id = await _make_user(db)
    anchor = str(uuid.uuid4())
    await _snapshot(db, user_id, W38, anchors=[anchor])

    row = (await db.execute(
        text("SELECT payload FROM trajectory_snapshots WHERE user_id = :u"),
        {"u": user_id},
    )).scalar_one()

    assert isinstance(row, dict)
    assert row["version"] == 1
    got = row["recurring_questions"][0]["prior_matches"][0]
    assert got["memory_entry_id"] == anchor
    assert got["text"] == "earlier"


@pytest.mark.asyncio
async def test_created_at_and_kind_carry_server_defaults(db):
    """An insert that names neither still produces a complete row — the property
    059 relies on for its own id column, checked here for the two columns that
    have defaults rather than assumed."""
    user_id = await _make_user(db)
    await db.execute(
        text(
            "INSERT INTO trajectory_snapshots (user_id, period_start, period_end, status) "
            "VALUES (:uid, :ps, :pe, 'empty')"
        ),
        {"uid": user_id, "ps": W38, "pe": W38 + timedelta(days=6)},
    )

    row = (await db.execute(
        text("SELECT id, kind, created_at FROM trajectory_snapshots WHERE user_id = :u"),
        {"u": user_id},
    )).first()
    assert row.id is not None
    assert row.kind == "weekly"
    assert row.created_at is not None


# ── 7. The letter's read (PR-D) — the WHERE clause a fake cannot prove ───────
#
# generate_weekly_letter_task selects ONE snapshot by
# (user_id, period_start, kind='weekly', status='generated'). Two of those four
# predicates are the ones that can silently match the wrong thing, and both are
# query results rather than code paths — which is why they are here and not in
# tests/workers/test_letter_standing_memory.py, where the clause is only pinned
# as source text.
#
# The read is reproduced rather than imported: it is written inline inside a
# 400-line ARQ task and there is no seam to call. Reproduced from the source the
# source-level test pins, so the two cannot drift apart without one of them
# failing.


async def _letter_read(db, user_id: str, period_start: datetime):
    """The letter's snapshot lookup, exactly as generate_weekly_letter_task issues it."""
    from sqlalchemy import select

    return (await db.execute(
        select(TrajectorySnapshot).where(
            TrajectorySnapshot.user_id == user_id,
            TrajectorySnapshot.period_start == period_start,
            TrajectorySnapshot.kind == "weekly",
            TrajectorySnapshot.status == "generated",
        )
    )).scalars().first()


@pytest.mark.asyncio
async def test_the_letter_finds_this_weeks_generated_snapshot(db):
    """The precondition for every assertion below: the read works at all. A
    negative test whose positive twin was never written proves nothing."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38, anchors=[str(uuid.uuid4())])

    assert await _letter_read(db, user_id, W38) is not None


@pytest.mark.asyncio
async def test_a_misaligned_period_start_matches_nothing(db):
    """THE EQUALITY, PROVEN RATHER THAN ASSUMED. The letter's legacy branch floors
    to a SUNDAY and week_period floors to a MONDAY, so a legacy job's period_start
    is one day off and can never name a real snapshot. The task skips the read on
    that path — but the equality is what makes skipping it merely tidy rather than
    load-bearing, and an accidental range predicate here would turn a near miss
    into a wrong week's letter."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38)

    sunday_before = W38 - timedelta(days=1)
    assert await _letter_read(db, user_id, sunday_before) is None
    assert await _letter_read(db, user_id, W37) is None


@pytest.mark.asyncio
async def test_a_failed_snapshot_is_invisible_to_the_letter(db):
    """A 'failed' row records that we do not know what that week held; its payload
    carries an error and no recurring_questions. Reading it would hand the builder
    a payload it would have to defend against. The WHERE clause is what stops it
    arriving, and the letter falls back to composing exactly as it did before."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38, status="failed")

    assert await _letter_read(db, user_id, W38) is None


@pytest.mark.asyncio
async def test_an_empty_snapshot_is_invisible_too(db):
    """'empty' means we looked and nothing echoed — a real observation, and the
    right thing for _prior_snapshot to diff against next week (asserted above).
    But it carries no recurring_questions, so there is nothing for the letter to
    render and the row is excluded here. The two readers want different sets from
    the same table, deliberately."""
    user_id = await _make_user(db)
    await _snapshot(db, user_id, W38, status="empty")

    assert await _letter_read(db, user_id, W38) is None


@pytest.mark.asyncio
async def test_the_letter_never_reads_another_users_snapshot(db):
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _snapshot(db, theirs, W38)

    assert await _letter_read(db, mine, W38) is None
