"""Layer A: the expectation table, the due-period arithmetic, and the miss rule.

WHY THIS FILE IS MOSTLY ABOUT STRINGS. `job_name` is the entire lookup key. An
expectation naming a job that no writer produces does not fail loudly -- it
reports that job missing on every tick, forever, from the hour it deploys. The
brief for this feature said "weekly_trajectory"; the live literal is
"weekly_trajectory_snapshot". That was caught by reading trajectory_snapshot.py,
not by anything that could have run, which is why the check now exists as a test.

THE DUPLICATION IS DELIBERATE AND THIS TEST IS ITS LICENCE. constants.py is
import-free from heavy dependencies by contract (its own file docstring), and
the worker modules are not, so JOB_EXPECTATIONS retypes the three names rather
than importing them. test_every_expectation_names_the_job_its_writer_writes is
what stops the two copies from drifting -- remove it and the retyping becomes
the defect it is currently guarded against.

THE ARITHMETIC TESTS USE FIXED INSTANTS, never datetime.now(). A due-period
calculation evaluated against the clock passes or fails depending on the day CI
runs, which is the 2026-09-01 lesson in miniature: a test that measures the
runner rather than the product.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from constants import JOB_EXPECTATIONS
from workers.heartbeat import (
    HEARTBEAT_EVERY_MINUTES,
    JOB_HEARTBEAT,
    heartbeat_run_key,
)
from workers.job_expectations import (
    due_run_key,
    interval_run_key,
    missed_expectations,
)
from workers.letter_dispatch import JOB_WEEKLY, weekly_run_key
from workers.trajectory_snapshot import JOB_WEEKLY_TRAJECTORY


def _by_name(name):
    return next(e for e in JOB_EXPECTATIONS if e["job_name"] == name)


def _utc(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


# ===========================================================================
# (1) The names, which are the whole lookup key
# ===========================================================================

def test_every_expectation_names_the_job_its_writer_writes():
    """The guard that licenses constants.py retyping these three literals.

    Compared against the CONSTANTS the writers use, not against a second list of
    strings: an assertion that restated the names would agree with itself while
    both drifted away from the code.
    """
    expected = {JOB_WEEKLY, JOB_WEEKLY_TRAJECTORY, JOB_HEARTBEAT}
    assert {e["job_name"] for e in JOB_EXPECTATIONS} == expected


def test_the_trajectory_job_is_named_with_its_suffix():
    """The specific mistake this feature's brief made, pinned on its own.

    'weekly_trajectory' is a plausible-looking name that appears in zero rows of
    job_run. The suffix is not decoration.
    """
    assert JOB_WEEKLY_TRAJECTORY == "weekly_trajectory_snapshot"
    assert _by_name("weekly_trajectory_snapshot")["cadence"] == "weekly"


def test_v1_covers_exactly_three_jobs():
    """Scope, pinned. monthly_letter, preview_mirror and the OTP purge are each
    out for a different stated reason (see JOB_EXPECTATIONS). A fourth entry
    arriving without a decision should fail here first.
    """
    assert len(JOB_EXPECTATIONS) == 3


def test_the_heartbeat_writer_and_its_expectation_share_one_cadence():
    """A writer on 10-minute buckets and a checker looking for 15-minute buckets
    never match a single row -- and report a perfectly healthy worker as dead
    forever. One number, asserted equal in both places.
    """
    assert _by_name(JOB_HEARTBEAT)["every_minutes"] == HEARTBEAT_EVERY_MINUTES


def test_the_heartbeat_grace_outlives_its_own_cadence():
    """Grace must exceed the interval, or a single late bucket reads as an
    outage. 20 against 10 leaves room for one missed fire before alerting.
    """
    exp = _by_name(JOB_HEARTBEAT)
    assert exp["grace_minutes"] > exp["every_minutes"]


# ===========================================================================
# (2) Weekly due periods
# ===========================================================================

def test_a_weekly_run_is_not_due_until_its_grace_has_elapsed():
    """Sunday 2026-09-13 18:00Z is the fire moment for ISO week 2026-W37 with a
    60-minute grace. At 18:30 the run in flight is not yet owed, so the period
    already OWED is the week before.
    """
    key, start = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-09-13T18:30:00"))
    assert key == "2026-W36"
    assert start == _utc("2026-09-06T18:00:00")


def test_a_weekly_run_becomes_due_once_grace_passes():
    key, start = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-09-13T19:01:00"))
    assert key == "2026-W37"
    assert start == _utc("2026-09-13T18:00:00")


def test_the_due_key_agrees_with_the_key_the_writer_uses():
    """R7 end to end: the checker's key for a period and the dispatcher's key for
    the same moment are the same string, or the lookup finds nothing.
    """
    _, start = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-09-13T19:01:00"))
    assert weekly_run_key(start) == "2026-W37"


def test_the_two_weekly_jobs_differ_only_in_their_hour():
    """The snapshot runs at 17:00 and the letter at 18:00, one hour apart so the
    snapshot's per-user fan-out drains first. At 18:05 the snapshot's own run is
    already past its grace while the letter's is not, so the snapshot is due for
    this week and the letter still owes the last one.
    """
    at = _utc("2026-09-13T18:05:00")
    assert due_run_key(_by_name(JOB_WEEKLY_TRAJECTORY), at)[0] == "2026-W37"
    assert due_run_key(_by_name(JOB_WEEKLY), at)[0] == "2026-W36"


def test_the_iso_year_boundary_does_not_break_the_key():
    """2026-W01 begins on 2025-12-29, in the previous calendar YEAR. %G-%V is
    ISO-correct where %Y-%V is not, and this is the week that shows the
    difference.
    """
    key, start = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-01-04T19:00:00"))
    assert key == "2026-W01"
    assert start == _utc("2026-01-04T18:00:00")
    # And one tick earlier it still owes the last week of 2025.
    earlier, _ = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-01-04T18:30:00"))
    assert earlier == "2025-W52"


def test_only_one_period_is_ever_reported_however_long_the_outage():
    """A job dead for six weeks yields the MOST RECENT miss, not six of them.
    Six alerts for one outage is the noise that gets an alert channel muted.
    """
    key, _ = due_run_key(_by_name(JOB_WEEKLY), _utc("2026-10-25T19:00:00"))
    assert key == "2026-W43"


# ===========================================================================
# (3) Interval due periods and bucket keys
# ===========================================================================

@pytest.mark.parametrize("moment,expected", [
    ("2026-09-17T09:10:00", "2026-09-17T09:10Z"),
    ("2026-09-17T09:19:59", "2026-09-17T09:10Z"),
    ("2026-09-17T09:20:00", "2026-09-17T09:20Z"),
    ("2026-09-17T00:00:00", "2026-09-17T00:00Z"),
    ("2026-09-17T23:59:59", "2026-09-17T23:50Z"),
])
def test_an_interval_key_floors_to_its_bucket(moment, expected):
    assert interval_run_key(_utc(moment), 10) == expected


def test_the_writer_and_the_checker_compute_the_same_bucket():
    """heartbeat_run_key is interval_run_key with the cadence filled in. Stated
    as an assertion because a second copy of the flooring arithmetic anywhere
    would read as a permanently missing job rather than as a bug.
    """
    at = _utc("2026-09-17T09:17:43")
    assert heartbeat_run_key(at) == interval_run_key(at, HEARTBEAT_EVERY_MINUTES)


def test_an_interval_bucket_is_due_only_after_its_window_plus_grace():
    """A bucket starting at S is owed once S + 10 + 20 has passed. At 09:45 the
    newest fully-owed bucket is the one that started at 09:10.
    """
    key, start = due_run_key(_by_name(JOB_HEARTBEAT), _utc("2026-09-17T09:45:00"))
    assert key == "2026-09-17T09:10Z"
    assert start == _utc("2026-09-17T09:10:00")


def test_the_bucket_in_flight_is_never_due():
    """The current bucket has not finished; the one before it is still inside
    grace. Neither can be missing yet.
    """
    _, start = due_run_key(_by_name(JOB_HEARTBEAT), _utc("2026-09-17T09:45:00"))
    assert start < _utc("2026-09-17T09:35:00")


def test_an_interval_key_fits_the_column():
    """run_key is VARCHAR(32) (migration 059). 17 characters, but asserted
    rather than counted by eye.
    """
    assert len(heartbeat_run_key(_utc("2026-12-31T23:50:00"))) <= 32


# ===========================================================================
# (4) The miss rule, including the floor
# ===========================================================================
#
# _period_succeeded and _history_floor are patched at their SOURCE module,
# because missed_expectations imports them inside its body. Substituting two
# functions with known return types rather than mocking a session: a MagicMock
# session would answer every query with a Mock, and "did this run succeed?"
# would be neither True nor False but truthy (C-06).

NOW = _utc("2026-09-17T09:45:00")
LONG_AGO = _utc("2026-01-01T00:00:00")


def _patched(succeeded, floor=LONG_AGO):
    return (
        patch("workers.letter_dispatch._period_succeeded",
              new=AsyncMock(side_effect=succeeded)),
        patch("workers.letter_dispatch._history_floor",
              new=AsyncMock(return_value=floor)),
    )


@pytest.mark.asyncio
async def test_nothing_is_reported_when_every_due_run_succeeded():
    async def succeeded(db, job_name, run_key):
        return True

    p1, p2 = _patched(succeeded)
    with p1, p2:
        assert await missed_expectations(object(), NOW) == []


@pytest.mark.asyncio
async def test_a_job_with_no_successful_due_run_is_reported():
    async def succeeded(db, job_name, run_key):
        return job_name != JOB_HEARTBEAT

    p1, p2 = _patched(succeeded)
    with p1, p2:
        missed = await missed_expectations(object(), NOW)

    assert [m["job_name"] for m in missed] == [JOB_HEARTBEAT]
    assert missed[0]["run_key"] == "2026-09-17T09:10Z"
    assert missed[0]["overdue_minutes"] == 35


@pytest.mark.asyncio
async def test_a_job_that_has_never_run_at_all_is_not_reported():
    """ABSENCE OF HISTORY IS NOT EVIDENCE OF A MISS -- the rule _history_floor
    exists for, applied here unchanged. Without it, deploying a NEW expectation
    would announce a backlog of outages that never happened.

    The cost is named in workers/job_expectations.py and covered by Layer C: a
    worker that has never once written a heartbeat is invisible HERE, and is
    exactly what the GitHub Actions check asks about in absolute terms.
    """
    async def succeeded(db, job_name, run_key):
        return False

    p1, p2 = _patched(succeeded, floor=None)
    with p1, p2:
        assert await missed_expectations(object(), NOW) == []


@pytest.mark.asyncio
async def test_a_period_older_than_the_jobs_first_run_is_not_reported():
    """The floor is a timestamp comparison, not merely a None check: a job whose
    history begins AFTER the due period was not expected to have covered it.
    """
    async def succeeded(db, job_name, run_key):
        return False

    p1, p2 = _patched(succeeded, floor=NOW)
    with p1, p2:
        assert await missed_expectations(object(), NOW) == []


@pytest.mark.asyncio
async def test_a_dead_worker_reports_every_expectation_at_once():
    """The September shape: the worker holds a wrong DATABASE_URL, so nothing it
    owns writes anything. All three expectations are missed together, and each
    is reported once.
    """
    async def succeeded(db, job_name, run_key):
        return False

    p1, p2 = _patched(succeeded)
    with p1, p2:
        missed = await missed_expectations(object(), NOW)

    assert len(missed) == 3
    assert {m["job_name"] for m in missed} == {
        JOB_WEEKLY, JOB_WEEKLY_TRAJECTORY, JOB_HEARTBEAT,
    }
