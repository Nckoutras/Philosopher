"""Letter dispatch moved to ARQ: the schedule, the run_key, the last-day guard,
and the job_run row.

WHAT THIS PINS. PR-B moves weekly_letter and monthly_letter out of APScheduler
(API process) into ARQ cron_jobs (worker process), and makes each run leave a
job_run row behind. The parts worth testing are the ones a reader cannot verify
by eye:

  - the two APScheduler ids are GONE and the other five are untouched (R4);
  - the ARQ schedule says what the old CronTrigger said, including the
    day={28,29,30,31} reconstruction of day='last', which arq cannot express;
  - run_key names the PERIOD, not the execution moment (R7);
  - the last-day guard returns before touching the database;
  - _open_job_run treats a unique-index collision as "already ran", not as a
    failure;
  - the counts keep 059's NULL-vs-0 distinction.

NO DATABASE HERE. Everything below is either a pure function or runs against
plain fake classes. The job_run row's real constraints — the unique index, the
status CHECK, RLS — are asserted against live Postgres in
tests/db_live/test_job_run.py, which is where they belong; a fake cannot enforce
an index and pretending otherwise would be theatre.

FAKES, NOT MagicMock (C-06). A MagicMock accepts every attribute write and
answers every read, so "did the run get closed with these counts?" would be
unassertable against one — it would answer yes either way.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

import workers.letter_dispatch as ld
from workers.arq_worker import WorkerSettings


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeDB:
    """A session that records what happened to it.

    commit_raises is consumed ONCE, so a caller that rolls back and continues
    sees the second commit succeed — which is what the IntegrityError path does.
    """

    def __init__(self, commit_raises=None):
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self._commit_raises = commit_raises

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self._commit_raises is not None:
            exc, self._commit_raises = self._commit_raises, None
            raise exc
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def _frozen(now: datetime):
    """A stand-in for the module's `datetime` whose now() is fixed."""

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    return _Frozen


def _integrity_error() -> IntegrityError:
    """What asyncpg raises through SQLAlchemy on uq_job_run_name_key."""
    return IntegrityError(
        "INSERT INTO job_run ...",
        {},
        Exception('duplicate key value violates unique constraint "uq_job_run_name_key"'),
    )


# ── 1. R4 — the APScheduler ids are gone ─────────────────────────────────────

def _registered_ids() -> set[str]:
    """Every job id setup_cron registers, using the harness the two existing
    cron tests established (test_cron_stripe_reconcile.py:62)."""
    from unittest.mock import MagicMock

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    import workers.cron as cron_mod
    from workers.cron import setup_cron

    scheduler = AsyncIOScheduler()
    original = cron_mod.scheduler
    cron_mod.scheduler = scheduler
    try:
        setup_cron(MagicMock())
        ids = {job.id for job in scheduler.get_jobs()}
        scheduler.shutdown(wait=False)
    finally:
        cron_mod.scheduler = original
    return ids


def test_the_two_letter_jobs_are_no_longer_scheduled_in_the_api_process():
    """R4. They run in the ARQ worker now. If both schedules were live at once,
    every Sunday would dispatch twice — and before 059's unique index that would
    have meant two letters per user, not one collision."""
    ids = _registered_ids()
    assert "weekly_letter" not in ids
    assert "monthly_letter" not in ids


def test_the_other_five_cron_jobs_are_untouched():
    """R4 scope: only the two letter jobs move. The other three dispatch jobs
    follow later, in one PR, after a Sunday run proves the pattern — so a
    disappearance here would be this PR reaching past its brief."""
    assert _registered_ids() == {
        "daily_rituals",
        "stripe_reconcile",
        "future_self_emails",
        "weekly_mirror",
        "preview_mirror",
    }


# ── 2. The ARQ schedule says what the APScheduler one said ───────────────────

def _cron_job(name: str):
    return next(c for c in WorkerSettings.cron_jobs if c.coroutine.__name__ == name)


def test_the_weekly_schedule_is_still_sunday_1800():
    job = _cron_job("dispatch_weekly_letters")
    assert (job.weekday, job.hour, job.minute) == ("sun", 18, 0)


def test_the_monthly_schedule_reconstructs_day_last():
    """arq's cron matches a field against an int or a set and raises on anything
    else (arq/cron.py:_get_next_dt), so APScheduler's day='last' has NO
    equivalent. The schedule fires on the four possible last days and
    dispatch_monthly_letters discards the ones that are not."""
    job = _cron_job("dispatch_monthly_letters")
    assert job.day == {28, 29, 30, 31}
    assert (job.hour, job.minute) == (17, 0)


def test_cron_defaults_are_the_ones_this_design_relies_on():
    """unique so N workers enqueue one job; max_tries=1 so a half-finished
    dispatch does not silently re-run; run_at_startup False so a deploy does not
    dispatch letters."""
    for name in ("dispatch_weekly_letters", "dispatch_monthly_letters"):
        job = _cron_job(name)
        assert job.unique is True
        assert job.max_tries == 1
        assert job.run_at_startup is False


def test_the_worker_evaluates_cron_in_utc_explicitly():
    """arq defaults to the worker's SYSTEM timezone (arq/worker.py:305), which
    made 'Sunday 18:00 UTC' a property of the Render container rather than of the
    code. Pinned so a local worker and production agree."""
    assert WorkerSettings.timezone == timezone.utc


def test_only_the_two_letter_tasks_carry_the_longer_timeout():
    """R5. A per-function timeout REPLACES job_timeout for that function
    (arq/worker.py:574); everything else stays on the 90s default."""
    with_timeout = {
        f.coroutine.__name__: f.timeout_s
        for f in WorkerSettings.functions if hasattr(f, "timeout_s")
    }
    assert with_timeout == {
        "generate_weekly_letter_task": 300,
        "generate_monthly_letter_task": 300,
    }
    assert WorkerSettings.job_timeout == 90


# ── 3. run_key names the period, not the execution moment (R7) ───────────────

def test_the_sunday_run_names_the_week_that_is_ending():
    """ISO weeks start MONDAY, so a Sunday-18:00 run falls on the LAST day of its
    own ISO week — %G-W%V therefore names the week the letter covers. Correct,
    and the only reason weekly_run_key exists instead of an inline strftime."""
    sunday = datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)
    assert sunday.weekday() == 6  # Sunday
    assert ld.weekly_run_key(sunday) == "2026-W36"
    # The Monday that starts the SAME ISO week carries the same key, which is
    # what makes the key a period rather than a timestamp.
    assert ld.weekly_run_key(sunday - timedelta(days=6)) == "2026-W36"


def test_the_next_sunday_is_a_different_week():
    a = datetime(2026, 9, 6, 18, 0, tzinfo=timezone.utc)
    assert ld.weekly_run_key(a) != ld.weekly_run_key(a + timedelta(days=7))


def test_the_monthly_key_is_the_calendar_month():
    assert ld.monthly_run_key(datetime(2026, 9, 30, 17, 0, tzinfo=timezone.utc)) == "2026-09"
    assert ld.monthly_run_key(datetime(2026, 12, 31, 17, 0, tzinfo=timezone.utc)) == "2026-12"


# ── 4. The last-day guard ────────────────────────────────────────────────────

@pytest.mark.parametrize("d, expected", [
    (datetime(2026, 9, 30, tzinfo=timezone.utc), True),    # 30-day month
    (datetime(2026, 9, 29, tzinfo=timezone.utc), False),
    (datetime(2026, 10, 31, tzinfo=timezone.utc), True),   # 31-day month
    (datetime(2026, 10, 30, tzinfo=timezone.utc), False),
    (datetime(2026, 2, 28, tzinfo=timezone.utc), True),    # non-leap February
    (datetime(2024, 2, 28, tzinfo=timezone.utc), False),   # leap February
    (datetime(2024, 2, 29, tzinfo=timezone.utc), True),
    (datetime(2026, 12, 31, tzinfo=timezone.utc), True),   # year boundary
])
def test_is_last_day_of_month(d, expected):
    """February is why the schedule cannot simply be day=31, and the leap pair is
    why it cannot be day=28 either."""
    assert ld.is_last_day_of_month(d) is expected


@pytest.mark.asyncio
async def test_a_non_last_day_returns_before_opening_a_run(monkeypatch):
    """The guard runs BEFORE any database access and before the job_run row, so
    the 0-3 wasted wakeups a month cost nothing and leave no trace. If it ran
    after _open_job_run, every month would hold up to four rows for one dispatch
    and the first would win the unique index — silently making the 28th the
    monthly letter day."""
    opened = []

    async def _never(*args, **kwargs):
        opened.append(args)
        raise AssertionError("_open_job_run must not be reached on a non-last day")

    monkeypatch.setattr(ld, "_open_job_run", _never)
    monkeypatch.setattr(ld, "datetime", _frozen(datetime(2026, 9, 15, 17, 0, tzinfo=timezone.utc)))

    await ld.dispatch_monthly_letters({"redis": None})

    assert opened == []


# ── 5. job_run open / close ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_opening_a_run_writes_a_running_row_with_the_period_key():
    db = FakeDB()
    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W36")

    assert run is not None
    assert (run.job_name, run.run_key, run.status) == ("weekly_letter", "2026-W36", "running")
    assert db.added == [run]
    assert db.commits == 1
    # finished_at stays NULL until the run closes: that NULL, with
    # status='running', is the crash signature 059 exists to record.
    assert run.finished_at is None


@pytest.mark.asyncio
async def test_a_collision_on_the_unique_index_means_already_ran_not_failed(caplog):
    """uq_job_run_name_key (059) is what decides, not a check-then-act read — so
    two workers waking together, a redeploy re-firing a schedule, and a wrong
    last-day guard all collapse into the same harmless outcome."""
    db = FakeDB(commit_raises=_integrity_error())

    with caplog.at_level("INFO"):
        run = await ld._open_job_run(db, ld.JOB_MONTHLY, "2026-09")

    assert run is None
    assert db.rollbacks == 1
    assert "2026-09" in caplog.text


@pytest.mark.asyncio
async def test_closing_a_run_leaves_uncounted_fields_null():
    """059's rule: NULL is "never got that far", 0 is "counted, and there were
    none". A close that passes no counts must not write zeros — that would make a
    dispatch which died before the eligibility query indistinguishable from a
    week where nobody qualified, which is the distinction the columns exist for."""
    db = FakeDB()
    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W36")

    await ld._close_job_run(db, run, status="failed", error="boom")

    assert run.status == "failed"
    assert run.error == "boom"
    assert run.finished_at is not None
    assert run.candidate_count is None
    assert run.selected_count is None
    assert run.enqueued_count is None


@pytest.mark.asyncio
async def test_a_run_that_counted_nobody_records_zero_not_null():
    """The other half of the same distinction: the query ran, and the answer was
    none. dispatch writes 0 here deliberately."""
    db = FakeDB()
    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W36")

    await ld._close_job_run(db, run, status="succeeded", selected=0, enqueued=0)

    assert run.status == "succeeded"
    assert (run.selected_count, run.enqueued_count) == (0, 0)


@pytest.mark.asyncio
async def test_a_long_error_is_truncated_rather_than_dropped():
    """The column is TEXT, but a driver traceback can be enormous and this field
    is an operator hint, not a log. The full trace goes to Render and Sentry."""
    db = FakeDB()
    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W36")

    await ld._close_job_run(db, run, status="failed", error="x" * 5000)

    assert len(run.error) == 2000


@pytest.mark.asyncio
async def test_closing_never_raises_out_of_its_own_bookkeeping(caplog):
    """_close_job_run runs on the failure path too. A letter run that already
    failed must not also raise from the code that records the failure."""
    db = FakeDB()
    run = await ld._open_job_run(db, ld.JOB_WEEKLY, "2026-W36")
    db._commit_raises = RuntimeError("connection gone")

    with caplog.at_level("ERROR"):
        await ld._close_job_run(db, run, status="failed", error="boom")

    assert "connection gone" in caplog.text


@pytest.mark.asyncio
async def test_closing_a_run_that_was_never_opened_is_a_no_op():
    """_open_job_run returns None on a collision, and the callers pass whatever
    they got straight through."""
    await ld._close_job_run(FakeDB(), None, status="failed", error="boom")


# ── 6. R9a — no explicit capture_exception in this module ────────────────────

def test_the_failure_path_relies_on_logging_not_on_capture_exception():
    """R9a. Sentry's LoggingIntegration turns every logger.error into an event at
    event_level=ERROR (observability.py:37-46, pinned by test_observability), so
    an explicit capture_exception alongside it would report the same failure
    TWICE. The durable record is the job_run row, not the Sentry event.

    Asserted against the source because the alternative — asserting that Sentry
    received exactly one event — would test the SDK rather than this decision.
    """
    import inspect

    source = inspect.getsource(ld)
    # The CALL, not the word: the module explains in a comment why it does not
    # make one, and a bare substring check would flag its own rationale.
    assert re.search(r"capture_exception\s*\(", source) is None
    assert "sentry_sdk" not in source
    assert source.count('logger.error(f"Cron weekly letters failed') == 1
    assert source.count('logger.error(f"Cron monthly letters failed') == 1
    assert source.count("exc_info=True") >= 2


# ── 7. The dispatch bodies moved verbatim ────────────────────────────────────

def test_the_eligibility_thresholds_did_not_move_with_the_code():
    """A move is only a move if the arithmetic survives it. The weekly bar is the
    literal 5 the old body used; the monthly bar is still the shared constant, not
    a copy of its value."""
    import inspect

    source = inspect.getsource(ld.dispatch_weekly_letters)
    assert "if total < 5:" in source

    monthly = inspect.getsource(ld.dispatch_monthly_letters)
    assert "if total < MONTHLY_MIN_MESSAGES:" in monthly


def test_arq_worker_is_imported_only_inside_the_function_bodies():
    """arq_worker imports THIS module at module level, so a top-level
    `from workers.arq_worker import ...` here would be a cycle. The bodies already
    imported that way in cron.py, which is why the move needed no rewrite — this
    pins the property rather than trusting it to survive a tidy-up."""
    import inspect

    source = inspect.getsource(ld)
    module_level = [
        line for line in source.splitlines()
        if line.startswith("from workers.arq_worker") or line.startswith("import workers.arq_worker")
    ]
    assert module_level == []
    assert re.search(r"^\s{12}from workers\.arq_worker import", source, re.MULTILINE)
