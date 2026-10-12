"""UAT-TOPIC-001 — an auto-sent daily topic is marked, and never becomes a memory.

THE DEFECT. Quick start with an empty textarea seeds the day's topic itself
(TodaysTopicCard: `trimmedTopic || dailyQuestion`). It was stored as an ordinary
role=user message, so extract_memory_task attributed the topic's claim to the person:
91 memory rows in production came from turns in which the person said nothing.

WHY LIVE. The decision is a query against daily_questions, and the consequence is a
job that is or is not enqueued after the reply commits. Both are driven here through
the REAL route, the real stream_response and real Postgres — the producer itself, not
a mock of it (lesson of PHILOSOPHER-API-F, 2026-10-05). Only the LLM, recall and
embeddings are faked, and the ARQ queue is a recorder.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_daily_topic_live.py -v
"""
import json
import random
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# INACTIVE on purpose: a stale tab can send yesterday's topic, so the match must not
# depend on `active`.
TOPIC = ("The Test Topic Nobody Typed — Why a seeded prompt is not the person's "
         "own claim about themselves.")
REPLY = "Consider what is in your power, and what is not."
SISTER = "My younger sister calls me first when something goes wrong."


@pytest_asyncio.fixture
async def live(schema, monkeypatch):
    import db.session as db_session
    import routers.conversations as conversations_router
    from auth import get_current_user, get_current_user_plan, get_user_plan_streaming
    from main import app
    from models import User

    engine = create_async_engine(schema)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "AsyncSessionLocal", Session)
    monkeypatch.setattr(conversations_router, "AsyncSessionLocal", Session)

    queue = AsyncMock()
    monkeypatch.setattr(app.state, "arq_queue", queue, raising=False)

    user_id = str(uuid.uuid4())
    question_id = str(uuid.uuid4())
    async with Session() as s:
        await s.execute(
            text("INSERT INTO users (id, email, is_admin) VALUES (:id, :e, true)"),
            {"id": user_id, "e": f"{user_id}@example.test"},
        )
        # display_order is UNIQUE; a value far above the seeded rows avoids them.
        await s.execute(
            text("INSERT INTO daily_questions (id, question_text, display_order, active) "
                 "VALUES (:id, :q, :o, false)"),
            {"id": question_id, "q": TOPIC, "o": random.randint(10_000_000, 99_999_999)},
        )
        await s.commit()
        user = await s.get(User, user_id)

    async def as_user_plan():
        return (user, "pro")

    async def as_user():
        return user

    app.dependency_overrides[get_current_user_plan] = as_user_plan
    app.dependency_overrides[get_user_plan_streaming] = as_user_plan
    app.dependency_overrides[get_current_user] = as_user

    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    try:
        yield SimpleNamespace(client=client, Session=Session, user_id=user_id, queue=queue)
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        async with Session() as s:
            await s.execute(text("SET LOCAL lock_timeout = '5s'"))
            await s.execute(text("DELETE FROM safety_events WHERE user_id = :u"), {"u": user_id})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
            await s.execute(text("DELETE FROM daily_questions WHERE id = :q"), {"q": question_id})
            await s.commit()
        await engine.dispose()


def _offline():
    async def stream(*a, **kw):
        yield REPLY
    return [
        patch("services.conversation_service.llm_client.stream", stream),
        patch("services.memory_service.memory_service.recall", AsyncMock(return_value=[])),
        patch("services.embedding_client.embedding_client.embed", AsyncMock(side_effect=RuntimeError("no network"))),
        patch("services.analytics_service.analytics_service.track", lambda *a, **kw: None),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
    ]


class _Patched:
    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.start()

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()


async def _conversation(live, *, with_history=False) -> str:
    cid = str(uuid.uuid4())
    async with live.Session() as s:
        pid = (await s.execute(text(
            "SELECT id::text FROM personas WHERE is_active ORDER BY slug LIMIT 1"
        ))).scalar_one()
        await s.execute(
            text("INSERT INTO conversations (id, user_id, persona_id) VALUES (:c, :u, :p)"),
            {"c": cid, "u": live.user_id, "p": pid},
        )
        if with_history:
            for role, content in (("user", "What does it mean to live well?"), ("assistant", REPLY)):
                await s.execute(
                    text("INSERT INTO messages (id, conversation_id, user_id, role, content, safety_level, persona_id) "
                         "VALUES (:id, :c, :u, :r, :t, 'none', :p)"),
                    {"id": str(uuid.uuid4()), "c": cid, "u": live.user_id, "r": role, "t": content, "p": pid},
                )
        await s.commit()
    return cid


async def _send(live, cid, content, *, seeded):
    with _Patched(_offline()):
        r = await live.client.post(f"/api/v1/conversations/{cid}/messages",
                                   json={"content": content, "seeded_opening": seeded})
    assert r.status_code == 200, r.text
    events = [json.loads(l[len("data: "):]) for l in r.text.splitlines() if l.startswith("data: ")]
    assert "done" in [e["type"] for e in events], events


async def _kinds(live, cid) -> list[tuple[str, str]]:
    """Read back with a FRESH session: only committed rows are visible."""
    async with live.Session() as s:
        rows = await s.execute(
            text("SELECT role, message_kind FROM messages WHERE conversation_id = :c ORDER BY created_at"),
            {"c": cid},
        )
        return [tuple(r) for r in rows]


def _extractions(live) -> list:
    return [c for c in live.queue.enqueue_job.call_args_list if c.args[0] == "extract_memory_task"]


@pytest.mark.asyncio
async def test_a_seeded_daily_topic_is_marked_and_never_extracted(live):
    cid = await _conversation(live)
    await _send(live, cid, TOPIC, seeded=True)

    assert await _kinds(live, cid) == [("user", "daily_topic"), ("assistant", "standard")]
    assert _extractions(live) == []
    # Only extraction is skipped: the thread is still titled from its first exchange.
    jobs = [c.args[0] for c in live.queue.enqueue_job.call_args_list]
    assert "generate_conversation_title" in jobs


@pytest.mark.asyncio
async def test_the_persons_reply_to_the_topic_extracts_normally_and_without_it(live):
    cid = await _conversation(live)
    await _send(live, cid, TOPIC, seeded=True)
    await _send(live, cid, SISTER, seeded=False)

    assert await _kinds(live, cid) == [
        ("user", "daily_topic"), ("assistant", "standard"),
        ("user", "standard"), ("assistant", "standard"),
    ]
    calls = _extractions(live)
    assert len(calls) == 1
    # args: job name, user_id, conversation_id, persona_id, user_text, assistant_text, ...
    assert calls[0].args[4] == SISTER
    assert TOPIC not in calls[0].args


@pytest.mark.asyncio
async def test_a_topic_the_person_typed_is_seeded_but_stays_their_words(live):
    cid = await _conversation(live)
    await _send(live, cid, SISTER, seeded=True)

    assert await _kinds(live, cid) == [("user", "standard"), ("assistant", "standard")]
    assert len(_extractions(live)) == 1


@pytest.mark.asyncio
async def test_the_marker_applies_to_the_first_turn_only(live):
    # Same text, seeded, but the thread already has an exchange: not the card's seed.
    cid = await _conversation(live, with_history=True)
    await _send(live, cid, TOPIC, seeded=True)

    assert (await _kinds(live, cid))[-2:] == [("user", "standard"), ("assistant", "standard")]
    assert len(_extractions(live)) == 1
