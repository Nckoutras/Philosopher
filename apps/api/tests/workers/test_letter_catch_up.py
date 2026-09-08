"""PR-C: the explicit period (D-2), and the catch-up pass that repairs a miss.

WHAT THIS PINS.

  1. week_period / month_period round-trip with run_key, which is what makes R7
     literally true — run_key is DERIVED from period_start, not merely correlated
     with it. Before PR-C the weekly key named W36 while period_start sat in W35.
  2. Dispatch computes the period once and passes it to the generator, so the
     eligibility window and the letter's window are the same window.
  3. The catch-up key is the period that just ended, on both cadences.
  4. THE RECLAIM RULES. The gap query counts 'failed' and crashed-'running' rows
     as missed, but the unique index would otherwise make _open_job_run answer
     "already ran" and the catch-up would repair nothing. All four branches are
     asserted, plus the rule that the LIVE cron never reclaims.
  5. One period of lookback (R8a), and the history floor.

NO DATABASE HERE. Pure functions and plain fake classes; the real unique index,
the status CHECK and the reclaim UPDATE are asserted against live Postgres in
tests/db_live/test_letter_catch_up.py.

FAKES, NOT MagicMock (C-06). "Was this row reclaimed, with the counts reset?" is
unassertable against a MagicMock — it answers yes to every read whether or not
the code wrote anything.
"""
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

import workers.letter_dispatch as ld
from workers.arq_worker import WorkerSettings

NOW = datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc)  # a Monday


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeRun:
    """A job_run row with real attributes, so a missed write stays visible."""

    def __init__(self, job_name=ld.JOB_WEEKLY, run_key="2026-W37", status="failed",
                 started_at=None, error="boom", counts=(3, 2, 2)):
        self.job_name = job_name
        self.run_key = run_key
        self.status = status
        self.started_at = started_at or (NOW - timedelta(days=1))
        self.finished_at = NOW - timedelta(days=1)
        self.error = error
        self.candidate_count, self.selected_count, self.enqueued_count = counts


class FakeDB:
    """Session double. `existing` is what a SELECT returns after a collision."""

    def __init__(self, commit_raises=None, existing=None):
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self._commit_raises = commit_raises
        self._existing = existing

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self._commit_raises is not None:
            exc, self._commit_raises = self._commit_raises, None
            raise exc
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def execute(self, *_args, **_kwargs):
        existing = self._existing

        class _Result:
            def scalar_one_or_none(self):
                return existing

        return _Result()


def _integrity_error() -> IntegrityError:
    return IntegrityError(
        "INSERT INTO job_run ...", {},
        Exception('duplicate key value violates unique constraint "uq_job_run_name_key"'),
    )


def _frozen(now: datetime):
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    return _Frozen


# ── 1. The period is the key, and the key is the period (R7) ─────────────────

@pytest.mark.parametrize("key", ["2026-W36", "2026-W01", "2026-W53", "2027-W01"])
def test_a_weekly_period_round_trips_to_its_own_run_key(key):
    """THE PROPERTY R7 RESTS ON. The awkward keys are the point: 2026-W01 starts
    2025-12-29 — in the previous calendar YEAR — and 2026-W53 ends 2027-01-03.
    A naive "January 1st plus 7*n days" would get both wrong."""
    start, end = ld.week_period(key)
    assert ld.weekly_run_key(start) == key
    assert start.weekday() == 0          # Monday
    assert end.weekday() == 6            # Sunday
    assert end - start == timedelta(days=6, hours=23, minutes=59, seconds=59)


def test_the_weekly_period_is_the_week_the_sunday_run_names():
    """Sunday 18:00 falls on the LAST day of its own ISO week, so the live run's
    key names the week that is ending. Before PR-C period_start was the PREVIOUS
    Sunday, i.e. W35 for a run keyed W36 — the misalignment PR-C removes."""
    sunday = datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)
    key = ld.weekly_run_key(sunday)
    start, _ = ld.week_period(key)
    assert key == "2026-W36"
    assert start == datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc)
    assert start <= sunday


@pytest.mark.parametrize("key, start, end", [
    ("2026-09", datetime(2026, 9, 1, tzinfo=timezone.utc),
     datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)),
    ("2026-02", datetime(2026, 2, 1, tzinfo=timezone.utc),
     datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc)),
    ("2024-02", datetime(2024, 2, 1, tzinfo=timezone.utc),
     datetime(2024, 2, 29, 23, 59, 59, tzinfo=timezone.utc)),
    ("2026-12", datetime(2026, 12, 1, tzinfo=timezone.utc),
     datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
])
def test_a_monthly_period_round_trips(key, start, end):
    """The monthly period ALREADY satisfied R7 before PR-C; it only moved out of
    the generator. February in both flavours because monthrange is the whole
    reason this is not `day=30`."""
    assert ld.month_period(key) == (start, end)
    assert ld.monthly_run_key(start) == key


# ── 2. The catch-up key is the period that just ended ────────────────────────

def test_the_monday_catch_up_checks_the_week_that_just_ended(monkeypatch):
    """Monday 09:00 is 15 hours after the Sunday 18:00 dispatch, and `now` is in
    the NEW ISO week — so the key must come from YESTERDAY, not from today."""
    monday = datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc)
    sunday = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
    assert monday.weekday() == 0 and sunday.weekday() == 6
    assert ld.weekly_run_key(monday) != ld.weekly_run_key(sunday)
    assert ld.weekly_run_key(monday - timedelta(days=1)) == ld.weekly_run_key(sunday)


@pytest.mark.parametrize("second_of, expected", [
    (datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc), "2026-09"),
    (datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc), "2025-12"),   # year boundary
    (datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc), "2026-02"),
])
def test_the_monthly_catch_up_steps_back_through_the_first(second_of, expected):
    """`now.month - 1` is wrong every January. Stepping back one day from the 1st
    is right in every month, which is why the code does that instead."""
    assert ld.monthly_run_key(second_of.replace(day=1) - timedelta(days=1)) == expected


# ── 3. THE RECLAIM RULES ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_failed_run_is_reclaimed_with_its_counts_reset():
    """THE REPAIR THAT WOULD OTHERWISE NOT HAPPEN. Without reclaim, the gap query
    would correctly report the period missed and _open_job_run would immediately
    answer "already ran" on the unique index — catch-up would repair nothing, for
    exactly the failure mode job_run exists to record.

    Counts reset to NULL rather than carried: 059's rule is that NULL means "never
    got that far", and a fresh attempt has not got anywhere yet. Keeping the failed
    attempt's numbers would describe the previous run while claiming to describe
    this one."""
    existing = FakeRun(status="failed", error="boom", counts=(9, 4, 4))
    db = FakeDB(commit_raises=_integrity_error(), existing=existing)

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37", reclaim=True)

    assert run is existing
    assert run.status == "running"
    assert run.finished_at is None
    assert run.error is None
    assert (run.candidate_count, run.selected_count, run.enqueued_count) == (None, None, None)
    assert db.rollbacks == 1


@pytest.mark.asyncio
async def test_a_stale_running_run_is_reclaimed(monkeypatch):
    """finished_at NULL with a stale start is the crash signature 059 records.
    Two hours is enormous slack for a dispatch that is a handful of queries — the
    300s letter GENERATION is a separate job and does not hold this row open.

    The clock is frozen because staleness is measured against `now`: without it
    this test would pass or fail depending on the date the suite runs, which is
    the runner-dependence CLAUDE.md's #578 entry is about."""
    monkeypatch.setattr(ld, "datetime", _frozen(NOW))
    existing = FakeRun(status="running", started_at=NOW - timedelta(hours=5))
    db = FakeDB(commit_raises=_integrity_error(), existing=existing)

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37", reclaim=True)

    assert run is existing
    assert run.status == "running"


@pytest.mark.asyncio
async def test_a_recently_started_running_run_is_left_alone(monkeypatch):
    """A run genuinely in flight. Two dispatches for one period is precisely what
    the unique index exists to prevent, so catch-up must not force past it."""
    monkeypatch.setattr(ld, "datetime", _frozen(NOW))
    existing = FakeRun(status="running", started_at=NOW - timedelta(minutes=5))
    db = FakeDB(commit_raises=_integrity_error(), existing=existing)

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37", reclaim=True)

    assert run is None
    assert existing.status == "running"      # untouched


@pytest.mark.asyncio
async def test_a_succeeded_run_is_never_reclaimed():
    """The period is done. Reclaiming it would re-dispatch a week that was
    delivered, which is the one outcome worse than not repairing a miss."""
    existing = FakeRun(status="succeeded", error=None, counts=(9, 4, 4))
    db = FakeDB(commit_raises=_integrity_error(), existing=existing)

    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37", reclaim=True)

    assert run is None
    assert existing.status == "succeeded"
    assert existing.candidate_count == 9     # counts untouched


@pytest.mark.asyncio
async def test_a_vanished_row_declines_rather_than_guesses(caplog):
    """The colliding row could not be read back. Nothing sane deletes job_run
    rows, so this means something unusual is happening; declining beats guessing."""
    db = FakeDB(commit_raises=_integrity_error(), existing=None)

    with caplog.at_level("WARNING"):
        run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37", reclaim=True)

    assert run is None
    assert "not reclaiming" in caplog.text


@pytest.mark.asyncio
async def test_the_live_path_never_reclaims_even_a_failed_row(caplog):
    """reclaim=False is the LIVE cron and its behaviour is unchanged by PR-C: a
    collision means the period already ran, full stop. If the live Sunday run
    could reclaim, a redeploy that re-fired the schedule would re-dispatch a week
    mid-flight."""
    existing = FakeRun(status="failed")
    db = FakeDB(commit_raises=_integrity_error(), existing=existing)

    with caplog.at_level("INFO"):
        run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W37")

    assert run is None
    assert existing.status == "failed"       # untouched
    assert "already ran" in caplog.text


def test_dispatch_asks_for_reclaim_only_when_given_a_run_key():
    """The live/catch-up distinction is one expression, so it is pinned as one:
    reclaim is the same boolean as "was a run_key handed to me". Asserted on the
    source because driving both dispatch paths would need the whole DB surface."""
    for fn in (ld.dispatch_weekly_letters, ld.dispatch_monthly_letters):
        source = inspect.getsource(fn)
        assert "catch_up = run_key is not None" in source
        assert "reclaim=catch_up" in source


# ── 4. The gap query, the floor, and one period of lookback (R8a) ────────────

@pytest.mark.asyncio
async def test_no_history_means_nothing_can_be_missed(monkeypatch, caplog):
    """THE FLOOR. No job_run row predates PR-B, so without this the first catch-up
    after deploy would call every earlier week "missed" and re-dispatch a week the
    old APScheduler path had already delivered."""
    calls = []

    async def _floor(db, job_name):
        return None

    async def _dispatch(ctx, run_key=None):
        calls.append(run_key)

    monkeypatch.setattr(ld, "_history_floor", _floor)
    monkeypatch.setattr(ld, "dispatch_weekly_letters", _dispatch)

    with caplog.at_level("INFO"):
        await ld._catch_up(
            {}, job_name=ld.JOB_WEEKLY, run_key="2026-W37",
            period_end=NOW, dispatch=_dispatch,
        )

    assert calls == []
    assert "nothing can be missed" in caplog.text


@pytest.mark.asyncio
async def test_a_period_older_than_the_first_recorded_run_is_skipped(monkeypatch):
    """Same floor, the other side: history exists, but not far enough back to say
    anything about this period."""
    calls = []

    async def _floor(db, job_name):
        return NOW - timedelta(days=1)

    async def _dispatch(ctx, run_key=None):
        calls.append(run_key)

    monkeypatch.setattr(ld, "_history_floor", _floor)

    await ld._catch_up(
        {}, job_name=ld.JOB_WEEKLY, run_key="2020-W01",
        period_end=NOW - timedelta(days=400), dispatch=_dispatch,
    )

    assert calls == []


@pytest.mark.asyncio
async def test_a_succeeded_period_is_not_re_dispatched(monkeypatch):
    calls = []

    async def _floor(db, job_name):
        return NOW - timedelta(days=30)

    async def _succeeded(db, job_name, run_key):
        return True

    async def _dispatch(ctx, run_key=None):
        calls.append(run_key)

    monkeypatch.setattr(ld, "_history_floor", _floor)
    monkeypatch.setattr(ld, "_period_succeeded", _succeeded)

    await ld._catch_up(
        {}, job_name=ld.JOB_WEEKLY, run_key="2026-W37",
        period_end=NOW, dispatch=_dispatch,
    )

    assert calls == []


@pytest.mark.asyncio
async def test_a_missed_period_is_re_dispatched_with_its_key(monkeypatch, caplog):
    """The whole point. The key is threaded through, not a period pair, because
    under the aligned arithmetic the key IS the period."""
    calls = []

    async def _floor(db, job_name):
        return NOW - timedelta(days=30)

    async def _succeeded(db, job_name, run_key):
        return False

    async def _dispatch(ctx, run_key=None):
        calls.append(run_key)

    monkeypatch.setattr(ld, "_history_floor", _floor)
    monkeypatch.setattr(ld, "_period_succeeded", _succeeded)

    with caplog.at_level("INFO"):
        await ld._catch_up(
            {}, job_name=ld.JOB_WEEKLY, run_key="2026-W37",
            period_end=NOW, dispatch=_dispatch,
        )

    assert calls == ["2026-W37"]
    assert "was missed" in caplog.text


def test_catch_up_looks_back_exactly_one_period(caplog):
    """R8a. Both passes derive a SINGLE key and hand it to _catch_up — no loop, no
    range, no configurable depth. Three backdated letters arriving together reads
    as a broken product rather than as a repair, and older gaps are repaired by
    hand with an explicit run_key (R8).

    Asserted structurally: a future 'while gaps remain' refactor has to delete
    this test to land, which is the point of it."""
    for fn in (ld.catch_up_weekly_letters, ld.catch_up_monthly_letters):
        source = inspect.getsource(fn)
        assert source.count("_catch_up(") == 1
        assert "for " not in source
        assert "while " not in source


# ── 5. The schedule ──────────────────────────────────────────────────────────

def _cron_job(name: str):
    return next(c for c in WorkerSettings.cron_jobs if c.coroutine.__name__ == name)


def test_the_catch_up_passes_are_scheduled_the_morning_after():
    """Fifteen hours after the Sunday dispatch, and before the reader's Monday."""
    weekly = _cron_job("catch_up_weekly_letters")
    assert (weekly.weekday, weekly.hour, weekly.minute) == ("mon", 9, 0)

    monthly = _cron_job("catch_up_monthly_letters")
    assert (monthly.day, monthly.hour, monthly.minute) == (2, 9, 0)


def test_all_four_cron_jobs_are_registered():
    names = [c.coroutine.__name__ for c in WorkerSettings.cron_jobs]
    assert names == [
        "dispatch_weekly_letters",
        "dispatch_monthly_letters",
        "catch_up_weekly_letters",
        "catch_up_monthly_letters",
    ]


# ── 6. The period reaches the generator (D-2) ────────────────────────────────

def test_dispatch_passes_the_period_to_the_generator():
    """D-2 closed. The generator no longer recomputes a window from `now`, so the
    eligibility window and the letter's window cannot drift apart."""
    weekly = inspect.getsource(ld.dispatch_weekly_letters)
    assert 'enqueue_job(\n                        "generate_weekly_letter_task", uid, slug,\n' in weekly
    assert "period_start.isoformat(), period_end.isoformat()," in weekly

    monthly = inspect.getsource(ld.dispatch_monthly_letters)
    assert "period_start.isoformat(), period_end.isoformat()," in monthly


def test_both_generators_accept_a_period_and_default_it_to_none():
    """Defaulted so a job enqueued by pre-PR-C code, still sitting in Redis across
    the deploy, runs on the old arithmetic instead of raising on the signature."""
    from workers.arq_worker import generate_monthly_letter_task, generate_weekly_letter_task

    for fn in (generate_weekly_letter_task, generate_monthly_letter_task):
        params = inspect.signature(fn).parameters
        assert params["period_start"].default is None
        assert params["period_end"].default is None


def test_the_eligibility_window_is_bounded_at_both_ends():
    """A catch-up runs days after its period ended, so an unbounded `created_at >=
    period_start` would sweep in everything since. The upper bound is what makes a
    past period mean the same thing on Monday as it did on Sunday."""
    for fn in (ld.dispatch_weekly_letters, ld.dispatch_monthly_letters):
        source = inspect.getsource(fn)
        assert "Message.created_at >= period_start," in source
        assert "Message.created_at <= period_end," in source
        assert "ritual_counts_by_user(db, period_start, period_end)" in source
