"""Catch-up against live Postgres: the gap query, the floor, and the reclaim.

WHY THESE NEED A REAL SERVER. The reclaim path exists BECAUSE of a unique index:
_open_job_run's INSERT collides on uq_job_run_name_key (059), and the reclaim is
what happens after that collision. A fake can be told to raise IntegrityError —
tests/workers/test_letter_catch_up.py does exactly that, and asserts the four
branches — but only Postgres can prove that the collision actually happens, that
the UPDATE lands on the row the index pointed at, and that the row is readable
back with the counts reset.

The other half is the letter-level dedup: re-dispatching a period that already
produced a letter must not produce a second one. That is enforced by
uq_weekly_letters_user_period (022/029) plus the generator's own predicate, and
neither is assertable against a mock.

WHAT IS NOT HERE. The schedule, the key arithmetic and the one-period lookback
are pure functions and live in the unit file. Duplicating them here would add
runtime without adding evidence.

WHY THREE OF THESE TESTS SEED THROUGH A SECOND, COMMITTING SESSION.
CODE UNDER TEST THAT CALLS session.rollback() CANNOT RUN INSIDE THE
ROLLBACK-ISOLATED FIXTURE WITHOUT A SAVEPOINT; THESE THREE TESTS SEED THROUGH A
COMMITTED SIDE SESSION INSTEAD.

The `db` fixture hands every test one outer transaction and rolls it back at
teardown (conftest.py). _open_job_run's collision path calls db.rollback(), which
under that fixture rolls back the OUTER transaction — erasing a row the test had
only flushed, so _reclaim_job_run then reads nothing and reports "no row could be
read". That is a harness limitation, not a product defect: in production
_open_job_run runs on its own fresh session and the colliding row was committed
by an earlier process, which is exactly the state these tests must reproduce.

This was predicted and written down before it happened. The PR-A investigation
recorded it as "ONE CONSEQUENCE OF THE ROLLBACK FIXTURE, flagged because it will
bite: a constraint violation ABORTS the surrounding transaction, and the db
fixture hands every test a transaction that is rolled back whole" — and noted
that test_letter_failed_status.py sidesteps it by making the raise the last
statement in its test. That sidestep is unavailable here, because the whole point
of the reclaim is what happens AFTER the collision.

So the colliding row is seeded through a separate engine and session that really
COMMITS, and the state is read back through that same session — what another
process would see, which is the only reading that means anything for a row this
code expects to find already committed. Each seeded row is deleted in a `finally`
through the same committed session, so nothing leaks into another test or another
run, and each test uses its own run_key so ordering cannot matter.

The other ten tests in this file are unaffected: none of them drives a code path
that rolls back, so the ordinary fixture expresses them correctly.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import workers.letter_dispatch as ld

WEEK_KEY = "2026-W37"
MONTH_KEY = "2026-09"

# One key per committed-seed test, outside the range every other test in this
# file and in test_job_run.py uses (W30-W37, W40, W99). Distinct so the three
# committed rows can never collide with each other or with anything else,
# whatever order the suite runs in.
RECLAIM_FAILED_KEY = "2026-W41"
RECLAIM_SUCCEEDED_KEY = "2026-W42"
LIVE_NO_RECLAIM_KEY = "2026-W43"


async def _insert_run(db, *, job_name=ld.JOB_WEEKLY, run_key=WEEK_KEY, status="succeeded",
                      started_at=None, error=None, counts=(7, 3, 3)):
    """One job_run row, written the way dispatch writes it."""
    run_id = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO job_run (id, job_name, run_key, status, started_at, error,"
            "                     candidate_count, selected_count, enqueued_count) "
            "VALUES (:id, :job, :key, :st, :started, :err, :c, :s, :e)"
        ),
        {
            "id": run_id, "job": job_name, "key": run_key, "st": status,
            "started": started_at or datetime.now(timezone.utc) - timedelta(days=1),
            "err": error, "c": counts[0], "s": counts[1], "e": counts[2],
        },
    )
    await db.flush()
    return run_id


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


# ── The committed side session ───────────────────────────────────────────────

class CommittedRows:
    """Rows written by "an earlier process" — committed, and cleaned up after.

    Bound to the ENGINE rather than to a connection with an open transaction
    (which is what conftest's `db` does), so commit() here is a real commit and
    survives the code under test rolling its own session back.

    Every read drops this session's transaction first. Postgres is READ COMMITTED,
    so a statement in a fresh transaction sees whatever the code under test
    committed; a statement in a transaction opened BEFORE that commit might not.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._seeded: list[tuple[str, str]] = []

    async def seed(self, run_key: str, status: str, *, job_name: str = ld.JOB_WEEKLY,
                   error: str | None = None, counts=(7, 3, 3),
                   started_at: datetime | None = None) -> None:
        await self._session.execute(
            text(
                "INSERT INTO job_run (id, job_name, run_key, status, started_at, error,"
                "                     candidate_count, selected_count, enqueued_count) "
                "VALUES (:id, :job, :key, :st, :started, :err, :c, :s, :e)"
            ),
            {
                "id": str(uuid.uuid4()), "job": job_name, "key": run_key, "st": status,
                "started": started_at or datetime.now(timezone.utc) - timedelta(days=1),
                "err": error, "c": counts[0], "s": counts[1], "e": counts[2],
            },
        )
        await self._session.commit()
        self._seeded.append((job_name, run_key))

    def track(self, run_key: str, *, job_name: str = ld.JOB_WEEKLY) -> None:
        """Register a key for cleanup WITHOUT writing anything.

        For the one test whose row is committed by the CODE UNDER TEST rather
        than seeded here: _open_job_run calls db.commit(), and the `db` fixture
        rolls back a transaction that no longer owns the row. Something has to
        delete it, and seeding it first would defeat the test — the whole point
        is that the insert does NOT collide.

        Call this BEFORE the code under test runs, so the row is removed even if
        an assertion after it fails. Deleting a key that was never written is a
        no-op, so registering early costs nothing.
        """
        self._seeded.append((job_name, run_key))

    async def fetch(self, run_key: str, *, job_name: str = ld.JOB_WEEKLY):
        await self._session.rollback()
        return (await self._session.execute(
            text(
                "SELECT status, error, finished_at, candidate_count, selected_count,"
                "       enqueued_count "
                "  FROM job_run WHERE job_name = :j AND run_key = :k"
            ),
            {"j": job_name, "k": run_key},
        )).one_or_none()

    async def count(self, run_key: str, *, job_name: str = ld.JOB_WEEKLY) -> int:
        await self._session.rollback()
        return (await self._session.execute(
            text("SELECT count(*) FROM job_run WHERE job_name = :j AND run_key = :k"),
            {"j": job_name, "k": run_key},
        )).scalar_one()

    async def cleanup(self) -> None:
        """Explicit DELETE, because these rows are COMMITTED — and so is anything
        the code under test committed on top of them. Nothing else removes them."""
        await self._session.rollback()
        for job_name, run_key in self._seeded:
            await self._session.execute(
                text("DELETE FROM job_run WHERE job_name = :j AND run_key = :k"),
                {"j": job_name, "k": run_key},
            )
        await self._session.commit()


@pytest_asyncio.fixture
async def committed(schema: str):
    """A session that commits, built from the same URL conftest's `schema` returns."""
    engine = create_async_engine(schema, poolclass=None)
    session = AsyncSession(bind=engine, expire_on_commit=False)
    rows = CommittedRows(session)
    try:
        yield rows
    finally:
        await rows.cleanup()
        await session.close()
        await engine.dispose()


# ── 1. The gap query ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_succeeded_period_is_not_missed(db):
    await _insert_run(db, status="succeeded")
    assert await ld._period_succeeded(db, ld.JOB_WEEKLY, WEEK_KEY) is True


@pytest.mark.asyncio
async def test_a_period_with_no_row_at_all_is_missed(db):
    assert await ld._period_succeeded(db, ld.JOB_WEEKLY, "2026-W99") is False


@pytest.mark.asyncio
async def test_a_failed_period_is_missed(db):
    """The row exists, so a naive EXISTS check would call this done. Only
    'succeeded' is done — which is the entire reason 058 made 'failed' writable."""
    await _insert_run(db, status="failed", error="boom")
    assert await ld._period_succeeded(db, ld.JOB_WEEKLY, WEEK_KEY) is False


@pytest.mark.asyncio
async def test_a_run_that_never_finished_is_missed(db):
    """finished_at NULL with status='running' is the crash signature. It must read
    as missed, or a dispatch that died mid-flight is never repaired."""
    await _insert_run(db, status="running", counts=(None, None, None))
    assert await ld._period_succeeded(db, ld.JOB_WEEKLY, WEEK_KEY) is False


@pytest.mark.asyncio
async def test_the_gap_query_is_scoped_to_one_job_name(db):
    """weekly and monthly carry independent key series, and '2026-09' means
    something in one and nothing in the other."""
    await _insert_run(db, job_name=ld.JOB_MONTHLY, run_key=MONTH_KEY, status="succeeded")
    assert await ld._period_succeeded(db, ld.JOB_MONTHLY, MONTH_KEY) is True
    assert await ld._period_succeeded(db, ld.JOB_WEEKLY, MONTH_KEY) is False


# ── 2. The floor ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_with_no_history_the_floor_is_none(db):
    """No job_run row predates PR-B. Without this, the first catch-up after deploy
    would call every earlier week missed and re-dispatch one the old APScheduler
    path had already delivered."""
    assert await ld._history_floor(db, ld.JOB_WEEKLY) is None


@pytest.mark.asyncio
async def test_the_floor_is_the_earliest_run_for_that_job(db):
    oldest = datetime.now(timezone.utc) - timedelta(days=30)
    await _insert_run(db, run_key="2026-W33", started_at=oldest)
    await _insert_run(db, run_key="2026-W35", started_at=oldest + timedelta(days=14))
    await _insert_run(db, job_name=ld.JOB_MONTHLY, run_key="2026-08",
                      started_at=oldest - timedelta(days=60))

    floor = await ld._history_floor(db, ld.JOB_WEEKLY)

    assert floor is not None
    # Seconds, not exact equality: the column is TIMESTAMPTZ and the driver
    # round-trips microseconds, which is not what this asserts.
    assert abs((floor - oldest).total_seconds()) < 1
    # The monthly row is older and must NOT lower the weekly floor.
    assert floor > oldest - timedelta(days=1)


# ── 3. The reclaim, against the real unique index ────────────────────────────

@pytest.mark.asyncio
async def test_a_failed_run_is_reclaimed_through_a_real_collision(db, committed):
    """THE REPAIR THAT WOULD OTHERWISE NOT HAPPEN, proven end to end: the INSERT
    really does violate uq_job_run_name_key, the reclaim really does find and
    update that row, and the counts really are reset.

    The failed row is COMMITTED first — see the module docstring. That is not a
    convenience: the reclaim only means anything against a row an earlier process
    left behind, and a row merely flushed inside this test's transaction is erased
    by the very rollback the code under test performs."""
    await committed.seed(RECLAIM_FAILED_KEY, "failed", error="boom", counts=(9, 4, 4))

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, RECLAIM_FAILED_KEY, reclaim=True)

    assert run is not None
    assert run.status == "running"
    assert run.finished_at is None
    assert run.error is None
    assert (run.candidate_count, run.selected_count, run.enqueued_count) == (None, None, None)

    # Read back through the COMMITTED session: what another process would see.
    row = await committed.fetch(RECLAIM_FAILED_KEY)
    assert row is not None
    assert row.status == "running"
    assert row.finished_at is None
    assert row.error is None
    assert (row.candidate_count, row.selected_count, row.enqueued_count) == (None, None, None)

    # And exactly ONE row still exists for the key — the reclaim updated, it did
    # not insert alongside.
    assert await committed.count(RECLAIM_FAILED_KEY) == 1


@pytest.mark.asyncio
async def test_a_succeeded_run_survives_a_reclaim_attempt(db, committed):
    """Re-dispatching a delivered week is the one outcome worse than not repairing
    a miss, so this is the assertion that matters most in the file."""
    await committed.seed(RECLAIM_SUCCEEDED_KEY, "succeeded", counts=(9, 4, 4))

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, RECLAIM_SUCCEEDED_KEY, reclaim=True)

    assert run is None

    row = await committed.fetch(RECLAIM_SUCCEEDED_KEY)
    assert row is not None
    assert row.status == "succeeded"
    assert row.candidate_count == 9
    assert await committed.count(RECLAIM_SUCCEEDED_KEY) == 1


@pytest.mark.asyncio
async def test_the_live_path_does_not_reclaim_a_failed_run(db, committed):
    """reclaim=False is the live cron and PR-C did not change it. If the Sunday run
    could reclaim, a redeploy that re-fired the schedule would re-dispatch a week
    that was already in flight."""
    await committed.seed(LIVE_NO_RECLAIM_KEY, "failed", error="boom")

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, LIVE_NO_RECLAIM_KEY)

    assert run is None

    row = await committed.fetch(LIVE_NO_RECLAIM_KEY)
    assert row is not None
    assert row.status == "failed"
    assert row.error == "boom"
    assert await committed.count(LIVE_NO_RECLAIM_KEY) == 1


@pytest.mark.asyncio
async def test_opening_a_fresh_period_still_inserts_normally(db, committed):
    """The reclaim path must not have broken the ordinary case.

    THIS TEST COMMITS, AND MUST CLEAN UP AFTER ITSELF (TD-64). It is the only
    _open_job_run call in this file that does NOT collide, so it is the only one
    whose db.commit() actually inserts — and a committed row outlives the `db`
    fixture's rollback. On CI that is invisible, because each run gets a fresh
    Postgres container. On any PERSISTENT database the row is permanent, and the
    second run would hit uq_job_run_name_key, take the IntegrityError path and
    reclaim the leftover row instead of inserting. The assertions below would
    still pass — status "running", finished_at NULL are true of a reclaimed row
    too — so the test would go on reporting green while exercising the RECLAIM
    branch under a name that says "inserts normally". That is worse than a
    failure: a test that quietly stops testing what it claims.

    `committed.track` registers the key before the insert rather than seeding
    it, because seeding would create the very collision this test exists to
    avoid. The fixture's cleanup() then deletes it in a finally.
    """
    committed.track("2026-W40")

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W40", reclaim=True)

    assert run is not None
    assert run.status == "running"
    assert run.finished_at is None


# ── 4. Re-dispatching a period that already produced a letter ────────────────

@pytest.mark.asyncio
async def test_a_second_letter_for_the_same_period_is_refused_by_the_index(db):
    """R2 (i) holds by construction rather than by a new check: the generator's
    per-user dedup runs before any LLM call or email, and beneath it
    uq_weekly_letters_user_period (022/029) makes a duplicate impossible even if
    the predicate were wrong.

    The period here is the ALIGNED one — Monday 00:00 of the run_key's ISO week —
    which is what a catch-up would compute from the key alone."""
    user_id = await _make_user(db)
    period_start, period_end = ld.week_period(WEEK_KEY)

    await db.execute(
        text(
            "INSERT INTO weekly_letters "
            "  (id, user_id, period_start, period_end, status, kind) "
            "VALUES (:id, :uid, :ps, :pe, 'generated', 'weekly')"
        ),
        {"id": str(uuid.uuid4()), "uid": user_id, "ps": period_start, "pe": period_end},
    )
    await db.flush()

    with pytest.raises(Exception) as excinfo:
        await db.execute(
            text(
                "INSERT INTO weekly_letters "
                "  (id, user_id, period_start, period_end, status, kind) "
                "VALUES (:id, :uid, :ps, :pe, 'generated', 'weekly')"
            ),
            {"id": str(uuid.uuid4()), "uid": user_id, "ps": period_start, "pe": period_end},
        )
        await db.flush()

    assert "uq_weekly_letters_user_period" in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_aligned_period_does_not_collide_with_a_pre_pr_c_row(db):
    """THE TRANSITION, asserted rather than argued. PR-C moved period_start by one
    day, and the dedup predicate is an equality — so the last pre-PR-C letter
    (period_start Sun 2026-08-30) and the first aligned one (Mon 2026-09-07) are
    different rows and neither suppresses the other. The six-hour seam between
    them, 2026-09-06 18:00 to 2026-09-07 00:00, is covered by neither letter and
    is the whole one-off cost of the alignment.

    The catch-up floor is what stops a catch-up from ever reaching back across
    that boundary; this test only pins that the two values do not collide."""
    user_id = await _make_user(db)
    old_start = datetime(2026, 8, 30, tzinfo=timezone.utc)          # pre-PR-C, a Sunday
    new_start, new_end = ld.week_period("2026-W37")                 # aligned, a Monday

    assert new_start == datetime(2026, 9, 7, tzinfo=timezone.utc)
    assert old_start.weekday() == 6 and new_start.weekday() == 0

    for ps, pe in ((old_start, old_start + timedelta(days=7)), (new_start, new_end)):
        await db.execute(
            text(
                "INSERT INTO weekly_letters "
                "  (id, user_id, period_start, period_end, status, kind) "
                "VALUES (:id, :uid, :ps, :pe, 'generated', 'weekly')"
            ),
            {"id": str(uuid.uuid4()), "uid": user_id, "ps": ps, "pe": pe},
        )
    await db.flush()

    count = (await db.execute(
        text("SELECT count(*) FROM weekly_letters WHERE user_id = :uid"),
        {"uid": user_id},
    )).scalar_one()
    assert count == 2
