"""release_on_exit: the borrowed stream session goes back to the pool on EVERY exit (OBS-002).

No Postgres: the thing under test is control flow, not SQL. A FakeSession records
whether close() RAN TO COMPLETION — it awaits twice inside close(), so a close that
is itself cancelled half-way records nothing. That is the property the shield()
buys, and the cancellation test fails if the shield is removed.

The disconnect is reproduced the way Starlette does it (StreamingResponse.__call__
in starlette 0.38): the consumer runs inside an anyio task group whose cancel scope
is cancelled while the body is suspended at an await.
"""
import asyncio
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import anyio
import pytest

from db.session import release_on_exit


class FakeSession:
    def __init__(self):
        self.close_started = 0
        self.closed = 0

    async def close(self):
        self.close_started += 1
        # Two checkpoints, like the greenlet hops asyncpg's checkin needs. Under a
        # cancelled anyio scope an UNSHIELDED await here raises CancelledError and
        # `closed` never increments.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.closed += 1


async def _three_items():
    for i in range(3):
        yield i


async def _raises_after_one():
    yield 1
    raise RuntimeError("llm fell over")


async def _hangs_after_one(started: asyncio.Event):
    yield 1
    started.set()
    await asyncio.sleep(60)  # the LLM call the reader walks away from
    yield 2  # pragma: no cover


@pytest.mark.asyncio
async def test_items_pass_through_and_the_session_is_closed_once():
    db = FakeSession()
    out = [i async for i in release_on_exit(_three_items(), db)]
    assert out == [0, 1, 2]
    assert db.closed == 1


@pytest.mark.asyncio
async def test_a_body_that_raises_still_releases_then_propagates():
    db = FakeSession()
    with pytest.raises(RuntimeError, match="llm fell over"):
        async for _ in release_on_exit(_raises_after_one(), db):
            pass
    assert db.closed == 1


@pytest.mark.asyncio
async def test_a_consumer_that_stops_early_releases_on_aclose():
    """Dropped at a yield: the path the async-generator finalizer takes."""
    db = FakeSession()
    gen = release_on_exit(_three_items(), db)
    assert await gen.__anext__() == 0
    await gen.aclose()
    assert db.closed == 1


@pytest.mark.asyncio
async def test_a_client_disconnect_mid_stream_still_returns_the_connection():
    """The OBS-002 shape: cancelled through an anyio cancel scope while the body
    awaits. Remove asyncio.shield from release_on_exit and `closed` stays 0,
    because the close itself is cancelled at its first checkpoint."""
    db = FakeSession()
    started = asyncio.Event()
    received = []

    async def consume():
        async for item in release_on_exit(_hangs_after_one(started), db):
            received.append(item)

    async with anyio.create_task_group() as tg:
        tg.start_soon(consume)
        await started.wait()
        tg.cancel_scope.cancel()  # what StreamingResponse does on disconnect

    # The shielded close finishes on the loop after the cancelled frame is gone.
    for _ in range(5):
        await asyncio.sleep(0)

    assert received == [1]
    assert db.close_started == 1
    assert db.closed == 1, "close() was cancelled before it finished — the shield is gone"


def test_every_stream_that_borrows_the_request_session_is_wrapped():
    """The four routes, pinned by source. The main chat stream (send_message) is
    NOT in this list on purpose: it uses get_user_plan_streaming and its own
    per-phase sessions (auth.py, the §5 pool-leak fix) and borrows nothing."""
    api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    expected = {
        "routers/conversations.py": 2,   # another_mind, go_deeper
        "routers/council.py": 1,
        "routers/self_comparison.py": 1,
    }
    for rel, n in expected.items():
        src = open(os.path.join(api_dir, rel), encoding="utf-8").read()
        assert src.count("release_on_exit(") == n, rel
        # Every StreamingResponse call in these files is wrapped, except send_message's.
        unwrapped = src.count("StreamingResponse(") - n
        assert unwrapped == (1 if rel == "routers/conversations.py" else 0), rel
