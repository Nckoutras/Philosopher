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
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

import workers.letter_dispatch as ld

WEEK_KEY = "2026-W37"
MONTH_KEY = "2026-09"


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
async def test_a_failed_run_is_reclaimed_through_a_real_collision(db):
    """THE REPAIR THAT WOULD OTHERWISE NOT HAPPEN, proven end to end: the INSERT
    really does violate uq_job_run_name_key, the reclaim really does find and
    update that row, and the counts really are reset."""
    await _insert_run(db, status="failed", error="boom", counts=(9, 4, 4))

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, WEEK_KEY, reclaim=True)

    assert run is not None
    assert run.status == "running"
    assert run.finished_at is None
    assert run.error is None
    assert (run.candidate_count, run.selected_count, run.enqueued_count) == (None, None, None)

    # And exactly ONE row still exists for the key — the reclaim updated, it did
    # not insert alongside.
    count = (await db.execute(
        text("SELECT count(*) FROM job_run WHERE job_name = :j AND run_key = :k"),
        {"j": ld.JOB_WEEKLY, "k": WEEK_KEY},
    )).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_a_succeeded_run_survives_a_reclaim_attempt(db):
    """Re-dispatching a delivered week is the one outcome worse than not repairing
    a miss, so this is the assertion that matters most in the file."""
    await _insert_run(db, status="succeeded", counts=(9, 4, 4))

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, WEEK_KEY, reclaim=True)

    assert run is None

    row = (await db.execute(
        text("SELECT status, candidate_count FROM job_run "
             " WHERE job_name = :j AND run_key = :k"),
        {"j": ld.JOB_WEEKLY, "k": WEEK_KEY},
    )).one()
    assert row.status == "succeeded"
    assert row.candidate_count == 9


@pytest.mark.asyncio
async def test_the_live_path_does_not_reclaim_a_failed_run(db):
    """reclaim=False is the live cron and PR-C did not change it. If the Sunday run
    could reclaim, a redeploy that re-fired the schedule would re-dispatch a week
    that was already in flight."""
    await _insert_run(db, status="failed", error="boom")

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, WEEK_KEY)

    assert run is None
    status = (await db.execute(
        text("SELECT status FROM job_run WHERE job_name = :j AND run_key = :k"),
        {"j": ld.JOB_WEEKLY, "k": WEEK_KEY},
    )).scalar_one()
    assert status == "failed"


@pytest.mark.asyncio
async def test_opening_a_fresh_period_still_inserts_normally(db):
    """The reclaim path must not have broken the ordinary case."""
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
