"""The OTP retention purge, and the arithmetic that makes it honour the policy.

WHAT WAS WRONG. Privacy Policy §6 publishes "OTP codes: up to 1 hour". Nothing
enforced it. OTP_EXPIRY_MINUTES = 10 decides whether a code still VERIFIES; no
process deleted the row, so retention was unbounded and otp_codes went on
holding an email address, a salted hash and timestamps indefinitely. A published
retention window with nothing behind it is the #588 defect class — a legal
document describing behaviour nobody built.

THE ASSERTION THAT MATTERS MOST is test_the_retention_arithmetic_honours_the
_published_hour. Honouring "up to 1 hour" bounds the maximum AGE of a surviving
row, so it constrains cutoff + interval, not the cutoff alone. The obvious
shape — hourly, deleting rows older than an hour — is wrong by nearly 2x and
looks right, which is exactly the kind of mistake a test has to hold.

NOT covered here: whether the cron actually fires in production. That is the
worker's own behaviour and no unit test can see it. What this file can do is
pin the schedule the worker is configured with, and the property that makes the
schedule correct.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.otp_service import OTP_EXPIRY_MINUTES
from workers.arq_worker import (
    OTP_PURGE_CUTOFF_MINUTES,
    OTP_PURGE_INTERVAL_MINUTES,
    WorkerSettings,
    purge_expired_otp_codes,
)

# The number the Privacy Policy §6 publishes, in minutes. Not a config value —
# it is a promise made to users in a legal document, and it is the ceiling every
# assertion below is measured against.
PUBLISHED_RETENTION_MINUTES = 60


def _fake_session(rowcount=0, raises=None):
    """An AsyncSession context manager that records the statement it was given."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.statements = []

    async def execute(stmt, *a, **kw):
        db.statements.append(stmt)
        if raises is not None:
            raise raises
        result = MagicMock()
        result.rowcount = rowcount
        return result

    db.execute = AsyncMock(side_effect=execute)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    ctx.db = db
    return ctx


def _cutoff_bound(stmt) -> datetime:
    """The datetime the WHERE clause compares against."""
    params = stmt.compile().params
    values = [v for v in params.values() if isinstance(v, datetime)]
    assert len(values) == 1, params
    return values[0]


# ── The purge does what it says ───────────────────────────────────────────────

async def test_the_purge_deletes_otp_codes_and_returns_the_count():
    session = _fake_session(rowcount=7)
    with patch("db.session.AsyncSessionLocal", return_value=session):
        deleted = await purge_expired_otp_codes({})

    assert deleted == 7
    assert len(session.db.statements) == 1
    assert str(session.db.statements[0]).startswith("DELETE FROM otp_codes")
    session.db.commit.assert_awaited_once()


async def test_the_predicate_is_created_at_not_expires_at():
    """A retention claim is about how long a row is KEPT, so the predicate says
    that in the policy's own terms. expires_at would express the same boundary
    indirectly through the validity offset, and would change meaning silently if
    OTP_EXPIRY_MINUTES ever moved."""
    session = _fake_session()
    with patch("db.session.AsyncSessionLocal", return_value=session):
        await purge_expired_otp_codes({})

    sql = str(session.db.statements[0])
    assert "created_at" in sql, sql
    assert "expires_at" not in sql, sql


async def test_the_cutoff_is_the_configured_window_behind_now():
    session = _fake_session()
    before = datetime.now(timezone.utc)
    with patch("db.session.AsyncSessionLocal", return_value=session):
        await purge_expired_otp_codes({})
    after = datetime.now(timezone.utc)

    cutoff = _cutoff_bound(session.db.statements[0])
    assert before - timedelta(minutes=OTP_PURGE_CUTOFF_MINUTES) <= cutoff
    assert cutoff <= after - timedelta(minutes=OTP_PURGE_CUTOFF_MINUTES)


async def test_a_row_inside_the_window_is_out_of_reach():
    """An over-broad purge is the one way this feature causes harm: deleting a
    code mid-sign-in would turn a working login into 'Invalid code.'"""
    session = _fake_session()
    with patch("db.session.AsyncSessionLocal", return_value=session):
        await purge_expired_otp_codes({})

    cutoff = _cutoff_bound(session.db.statements[0])
    just_issued = datetime.now(timezone.utc)
    mid_verification = just_issued - timedelta(minutes=OTP_EXPIRY_MINUTES)

    assert just_issued > cutoff, "a code issued now must not be in reach"
    assert mid_verification > cutoff, (
        "a code at the very end of its validity window must not be in reach"
    )


# ── The arithmetic ────────────────────────────────────────────────────────────

def test_the_retention_arithmetic_honours_the_published_hour():
    """THE ONE THAT MATTERS. Maximum surviving age is cutoff + interval, because a
    row created just after a run survives until the NEXT one.

    Hourly with a 1-hour cutoff — the shape this obviously wants to be tidied
    into — gives 120 minutes, not 60: a row created at 10:01 is younger than the
    11:00 cutoff, survives that run, and dies at 12:00 aged 119 minutes.
    """
    worst_case = OTP_PURGE_CUTOFF_MINUTES + OTP_PURGE_INTERVAL_MINUTES

    assert worst_case <= PUBLISHED_RETENTION_MINUTES, (
        f"cutoff ({OTP_PURGE_CUTOFF_MINUTES}m) + interval "
        f"({OTP_PURGE_INTERVAL_MINUTES}m) = {worst_case}m exceeds the "
        f"{PUBLISHED_RETENTION_MINUTES}m the Privacy Policy §6 publishes. Either "
        "lower these numbers, or amend §6 and re-date the policy."
    )
    assert worst_case == 40


def test_two_consecutive_missed_runs_still_land_inside_the_hour():
    """The margin, stated as a property rather than left implicit. One skipped run
    costs one interval; the design is only honest if a plausible number of them
    still fits inside the published window."""
    two_missed = OTP_PURGE_CUTOFF_MINUTES + (3 * OTP_PURGE_INTERVAL_MINUTES)

    assert two_missed <= PUBLISHED_RETENTION_MINUTES
    assert two_missed == 60


def test_the_cutoff_never_reaches_a_usable_code():
    """The cutoff must sit well clear of the validity window, so clock skew can
    never make the purge race a live sign-in."""
    assert OTP_PURGE_CUTOFF_MINUTES >= 3 * OTP_EXPIRY_MINUTES
    assert OTP_EXPIRY_MINUTES == 10


# ── The schedule the worker is actually configured with ──────────────────────

def _purge_cron():
    return next(
        c for c in WorkerSettings.cron_jobs
        if c.coroutine.__name__ == "purge_expired_otp_codes"
    )


def test_the_cron_is_registered_at_the_interval_the_arithmetic_assumes():
    """The schedule and the constant must agree. If the minute set is edited and
    OTP_PURGE_INTERVAL_MINUTES is not, the arithmetic test above goes on passing
    while the deployed worst case changes."""
    job = _purge_cron()
    expected = {m for m in range(0, 60, OTP_PURGE_INTERVAL_MINUTES)}

    assert job.minute == expected, job.minute
    assert len(expected) * OTP_PURGE_INTERVAL_MINUTES == 60
    # Every hour, every day — a retention window does not keep office hours.
    assert job.hour is None
    assert job.weekday is None


def test_the_purge_inherits_the_default_timeout():
    """A per-function timeout REPLACES job_timeout and raises the worker's
    in-progress key TTL to max(all timeouts) + 10 for EVERY job. One bounded
    DELETE has no claim on that, so the purge stays on the 90s default."""
    with_timeout = {
        f.coroutine.__name__ for f in WorkerSettings.functions
        if hasattr(f, "timeout_s")
    }
    assert "purge_expired_otp_codes" not in with_timeout
    assert WorkerSettings.job_timeout == 90


# ── Failure ───────────────────────────────────────────────────────────────────

async def test_the_purge_never_raises():
    """A failed purge must not take the worker down. The next run retries by
    construction, and the rows it failed to delete are still there to find."""
    session = _fake_session(raises=RuntimeError("connection reset"))

    with patch("db.session.AsyncSessionLocal", return_value=session):
        deleted = await purge_expired_otp_codes({})

    assert deleted == 0


async def test_a_failure_is_logged_with_the_cutoff(caplog):
    """The cutoff is the one value that makes a failed run diagnosable — it says
    which rows were meant to go."""
    session = _fake_session(raises=RuntimeError("connection reset"))

    with caplog.at_level("ERROR", logger="workers.arq_worker"):
        with patch("db.session.AsyncSessionLocal", return_value=session):
            await purge_expired_otp_codes({})

    rendered = [r.getMessage() for r in caplog.records]
    assert any("OTP purge FAILED" in m for m in rendered), rendered
    assert any("cutoff=" in m for m in rendered), rendered
