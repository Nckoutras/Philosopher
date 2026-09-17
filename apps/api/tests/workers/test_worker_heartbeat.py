"""Layer B: the worker says it is alive, and what happens when it cannot.

WHAT THIS CAN AND CANNOT SEE. No unit test can prove the worker process fires a
cron in production -- that is the worker's own behaviour, and it is precisely
what Layers A and C exist to observe from outside. What this file pins is the
SCHEDULE the worker is configured with and the BEHAVIOUR of the job body, which
is the same division test_otp_purge.py draws for the retention purge.

THE COUPLING WORTH PINNING. The heartbeat writes a run_key on a 10-minute
bucket; constants.JOB_EXPECTATIONS looks for rows on a 10-minute bucket. If
those two numbers ever disagree, the checker finds nothing, every tick, and
reports a perfectly healthy worker as permanently dead -- an alert that is
indistinguishable from the outage it was built to catch. The registration below
DERIVES its minute set from HEARTBEAT_EVERY_MINUTES so there is one number, and
tests/test_job_expectations.py asserts the expectation carries the same one.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from workers.arq_worker import WorkerSettings
from workers.heartbeat import (
    HEARTBEAT_EVERY_MINUTES,
    JOB_HEARTBEAT,
    worker_heartbeat,
)


def _heartbeat_cron():
    return next(
        c for c in WorkerSettings.cron_jobs if c.name.endswith(JOB_HEARTBEAT)
    )


# ===========================================================================
# (1) The schedule the worker is actually configured with
# ===========================================================================

def test_the_heartbeat_is_registered_on_the_worker():
    """It must be an ARQ cron job, not an APScheduler one. A heartbeat running
    in the API process would report the API's health under the worker's name --
    which is the failure mode inverted, not a signal.
    """
    assert _heartbeat_cron() is not None


def test_the_schedule_is_derived_from_the_cadence_constant():
    """Every HEARTBEAT_EVERY_MINUTES minutes, expressed as the minute set arq
    matches against. Derived rather than typed, so the writer's cadence and the
    expectation's cannot drift apart.
    """
    assert _heartbeat_cron().minute == set(range(0, 60, HEARTBEAT_EVERY_MINUTES))


def test_it_runs_at_startup_unlike_the_letter_dispatches():
    """The opposite call from the letters, for a reason that does not transfer:
    run_at_startup=True there would send LETTERS on every deploy. Here it writes
    one inert row, so a fresh worker proves itself within seconds of boot rather
    than up to ten minutes later.
    """
    assert _heartbeat_cron().run_at_startup is True


def test_a_failed_heartbeat_is_not_retried():
    """arq's max_tries default, wanted here rather than merely accepted: the
    next fire is ten minutes away and retries by construction. A retry storm
    against a database that is refusing connections helps nobody.
    """
    assert _heartbeat_cron().max_tries == 1


# ===========================================================================
# (2) The job body
# ===========================================================================
#
# _open_job_run and _close_job_run are patched at their source module, because
# worker_heartbeat imports them inside its body. Real function substitutes
# rather than a MagicMock session: a mocked session would accept every call and
# answer every read, leaving "was a row opened, and closed as succeeded?"
# unassertable (C-06).

@asynccontextmanager
async def _session():
    yield object()


def _patched(open_result=None, open_raises=None):
    opened = AsyncMock(return_value=open_result)
    if open_raises is not None:
        opened.side_effect = open_raises
    closed = AsyncMock()
    return opened, closed, (
        patch("db.session.AsyncSessionLocal", new=_session),
        patch("workers.letter_dispatch._open_job_run", new=opened),
        patch("workers.letter_dispatch._close_job_run", new=closed),
    )


@pytest.mark.asyncio
async def test_it_opens_and_closes_one_row_as_succeeded():
    """OPENED AND CLOSED IN ONE BREATH, unlike a dispatch. A dispatch opens its
    row before the work so a crash leaves finished_at NULL as evidence; there is
    no work here to crash between the two calls, and a heartbeat left in
    'running' would imitate the very crash signature it helps diagnose.
    """
    row = object()
    opened, closed, patches = _patched(open_result=row)
    with patches[0], patches[1], patches[2]:
        await worker_heartbeat({})

    assert opened.await_count == 1
    job_name, run_key = opened.await_args.args[1], opened.await_args.args[2]
    assert job_name == JOB_HEARTBEAT
    # The bucket key, not an execution timestamp (059's R7).
    assert run_key.endswith("Z") and len(run_key) <= 32

    assert closed.await_count == 1
    assert closed.await_args.kwargs["status"] == "succeeded"


@pytest.mark.asyncio
async def test_the_counts_stay_null():
    """059's rule: NULL is "never got that far", 0 is "counted, and there were
    none". A heartbeat counts nothing, so claiming zero candidates would be a
    small lie in a table an operator reads to tell those two apart.
    """
    opened, closed, patches = _patched(open_result=object())
    with patches[0], patches[1], patches[2]:
        await worker_heartbeat({})

    for field in ("candidate", "selected", "enqueued"):
        assert field not in closed.await_args.kwargs


@pytest.mark.asyncio
async def test_a_bucket_already_written_is_a_no_op():
    """_open_job_run returns None when uq_job_run_name_key already holds this
    (job, bucket) -- two workers awake together, or a restart landing inside a
    bucket run_at_startup already wrote. The row that is there says exactly what
    this one would have said, so nothing is closed and nothing is logged.
    """
    opened, closed, patches = _patched(open_result=None)
    with patches[0], patches[1], patches[2]:
        await worker_heartbeat({})

    assert opened.await_count == 1
    assert closed.await_count == 0


@pytest.mark.asyncio
async def test_it_never_raises_when_the_database_is_unreachable():
    """THE SEPTEMBER CONDITION, exactly: the worker cannot reach the database.
    The heartbeat must not take the worker down with it -- the same rule
    purge_expired_otp_codes states for itself, and for the same reason: the next
    run is ten minutes away and retries by construction.
    """
    opened, closed, patches = _patched(open_raises=OSError("connection refused"))
    with patches[0], patches[1], patches[2]:
        await worker_heartbeat({})  # must not raise

    assert closed.await_count == 0


@pytest.mark.asyncio
async def test_an_unreachable_database_is_logged_at_error():
    """ERROR, not warning, and the level is the point: observability.py wires
    Sentry's LoggingIntegration at event_level=ERROR, so this line IS an event.
    A heartbeat that cannot write is the outage reporting itself one layer
    earlier than the API-side checker would notice the silence.
    """
    opened, closed, patches = _patched(open_raises=OSError("connection refused"))
    with patches[0], patches[1], patches[2]:
        with patch("workers.heartbeat.logger") as log:
            await worker_heartbeat({})

    assert log.error.call_count == 1
    assert log.error.call_args.kwargs.get("exc_info") is True
