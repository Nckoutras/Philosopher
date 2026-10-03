"""safe_enqueue: the two silences it ends, pinned (OBS-001, ruling 6).

Asserted on caplog records rather than on a mocked logger, because the LEVEL is
the contract: ERROR is what Sentry's LoggingIntegration turns into an event
(observability.py), WARNING is a breadcrumb. A test that only checked "something
was logged" would pass if every line were downgraded to DEBUG.
"""
import logging
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import AsyncMock

import pytest

from services import enqueue
from services.enqueue import reset_absent_reports, safe_enqueue


@pytest.fixture(autouse=True)
def _fresh_process():
    reset_absent_reports()
    yield
    reset_absent_reports()


def _records(caplog):
    return [r for r in caplog.records if r.name == enqueue.__name__]


@pytest.mark.asyncio
async def test_a_working_queue_is_called_with_the_job_and_its_args():
    queue = AsyncMock()
    ok = await safe_enqueue(queue, "generate_conversation_title", "conv-1", context="conv=conv-1")
    assert ok is True
    queue.enqueue_job.assert_awaited_once_with("generate_conversation_title", "conv-1")


@pytest.mark.asyncio
async def test_an_absent_queue_is_an_error_once_per_job_then_a_warning(caplog):
    """The first skip per job name is the Sentry event; the rest are breadcrumbs.
    Delete the `_absent_reported` bookkeeping and the second assert fails."""
    caplog.set_level(logging.DEBUG, logger=enqueue.__name__)

    assert await safe_enqueue(None, "extract_memory_task", "u", context="user=u") is False
    assert await safe_enqueue(None, "extract_memory_task", "u", context="user=u") is False
    assert await safe_enqueue(None, "assess_conclusion_task", "c", context="conv=c") is False

    levels = [(r.levelno, r.getMessage()) for r in _records(caplog)]
    assert [lvl for lvl, _ in levels] == [logging.ERROR, logging.WARNING, logging.ERROR]
    assert all("Enqueue skipped, no queue" in msg for _, msg in levels)
    assert "job=extract_memory_task" in levels[0][1]
    assert "job=assess_conclusion_task" in levels[2][1]


@pytest.mark.asyncio
async def test_the_absent_queue_message_is_one_template(caplog):
    """Sentry groups LoggingIntegration events on the record's TEMPLATE
    (workers/cron.py explains why its own alert is parameterised). All job
    names must share one `msg` so they land in one issue."""
    caplog.set_level(logging.DEBUG, logger=enqueue.__name__)
    await safe_enqueue(None, "a", context="")
    await safe_enqueue(None, "b", context="")
    assert len({r.msg for r in _records(caplog)}) == 1


@pytest.mark.asyncio
async def test_an_enqueue_failure_is_an_error_with_the_trace_and_does_not_raise(caplog):
    caplog.set_level(logging.DEBUG, logger=enqueue.__name__)
    queue = AsyncMock()
    queue.enqueue_job.side_effect = ConnectionError("redis is away")

    ok = await safe_enqueue(queue, "counterview_belief_task", "u", "belief", context="user=u")

    assert ok is False
    (record,) = _records(caplog)
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None and record.exc_info[0] is ConnectionError
    assert "job=counterview_belief_task" in record.getMessage()


@pytest.mark.asyncio
async def test_a_restart_reports_again():
    """The set is process memory on purpose: after reset (a new boot), the
    same job is an ERROR again rather than a WARNING."""
    await safe_enqueue(None, "x")
    assert "x" in enqueue._absent_reported
    reset_absent_reports()
    assert "x" not in enqueue._absent_reported
