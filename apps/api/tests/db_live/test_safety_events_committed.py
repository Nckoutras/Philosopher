"""SAFETY-004 — every path that shows a crisis response COMMITS its safety_events row.

Measured, not read from code. The OPS-020 smoke (2026-09-28) showed the crisis text on
Council and You-vs-You and wrote ZERO safety_events rows. The production history then
showed zero rows for ANY stage but 'pre_generation', ever. A statement about what a path
writes is measured, so every path is driven here through the REAL app — the real routers,
the real get_db with its real teardown, real sessions against real Postgres — and the row
is read back afterwards with a fresh session. It is either committed or it is not there.

WHY NOT THE `db` FIXTURE. conftest's `db` wraps each test in a transaction that is always
rolled back, so a commit inside it is not a commit. These tests let the app open and
commit its own sessions (db.session.AsyncSessionLocal and the chat router's copy both
point at the test database), and clean up after themselves by user.

WHAT IS FAKED, AND ONLY THAT. Authentication (a real user row, returned by the three auth
dependencies), the LLM (it replies with a sentence the real output gate flags), memory
recall, retrieval and embeddings (network). The safety checks, the logging, the routers
and every session are real.

THE MECHANISM (SAFETY-004). With FastAPI 0.115.0, get_db's teardown — commit, then
close — runs BEFORE a StreamingResponse body. A stream that uses get_db is therefore on a
session its own teardown has already committed; a row it only flushes is lost.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_safety_events_committed.py -v
"""
import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

CRISIS = "I want to kill myself"
# The real output gate flags this: "lethal dose" is on OUTPUT_RISK_PHRASES.
HARMFUL_REPLY = "Some would speak of a lethal dose; the Stoic would not."
QUESTION = "What does it mean to live well?"


# ── The real app, on the test database, with real commits ─────────────────────

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

    user_id = str(uuid.uuid4())
    async with Session() as s:
        await s.execute(
            text("INSERT INTO users (id, email, is_admin) VALUES (:id, :e, true)"),
            {"id": user_id, "e": f"{user_id}@example.test"},
        )
        await s.commit()
        user = await s.get(User, user_id)   # detached after close; its scalar fields stay readable

    async def as_user_plan():
        return (user, "pro")

    async def as_user():
        return user

    app.dependency_overrides[get_current_user_plan] = as_user_plan
    app.dependency_overrides[get_user_plan_streaming] = as_user_plan
    app.dependency_overrides[get_current_user] = as_user

    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    try:
        yield SimpleNamespace(client=client, Session=Session, user_id=user_id, user=user)
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        # A stream that flushed a row and never committed it (SAFETY-004) leaves its
        # transaction open, holding locks on the user's rows. Let it be collected, and
        # bound the cleanup so such a leak FAILS the teardown instead of hanging it.
        import gc
        gc.collect()
        async with Session() as s:
            await s.execute(text("SET LOCAL lock_timeout = '5s'"))
            # safety_events.user_id is ON DELETE SET NULL, so they go first (C-07).
            await s.execute(text("DELETE FROM safety_events WHERE user_id = :u"), {"u": user_id})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": user_id})
            await s.commit()
        await engine.dispose()


async def _stages(live) -> list[str]:
    """Read back with a FRESH session: only committed rows are visible."""
    async with live.Session() as s:
        rows = await s.execute(
            text("SELECT trigger_stage FROM safety_events WHERE user_id = :u ORDER BY created_at"),
            {"u": live.user_id},
        )
        return [r[0] for r in rows]


def _events(resp) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in resp.text.splitlines() if line.startswith("data: ")]


def _fake_llm(reply):
    async def stream(*a, **kw):
        yield reply
    return stream


def _no_network():
    """Memory recall, retrieval and embeddings reach the network; nothing here needs them."""
    return [
        patch("services.memory_service.memory_service.recall", AsyncMock(return_value=[])),
        patch("services.embedding_client.embedding_client.embed", AsyncMock(side_effect=RuntimeError("no network"))),
        patch("services.analytics_service.analytics_service.track", lambda *a, **kw: None),
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


async def _persona_ids(live, n=2) -> list[tuple[str, str]]:
    async with live.Session() as s:
        rows = await s.execute(text(
            "SELECT id::text, slug FROM personas WHERE is_active ORDER BY slug LIMIT :n"
        ), {"n": n})
        return [(r[0], r[1]) for r in rows]


async def _conversation(live, *, with_history=True) -> tuple[str, str, str]:
    """A conversation owned by the user, with one real exchange so another-mind and
    go-deeper have something to answer. Returns (conversation_id, home_slug, guest_slug)."""
    (home_id, home_slug), (_, guest_slug) = await _persona_ids(live, 2)
    cid = str(uuid.uuid4())
    async with live.Session() as s:
        await s.execute(
            text("INSERT INTO conversations (id, user_id, persona_id) VALUES (:c, :u, :p)"),
            {"c": cid, "u": live.user_id, "p": home_id},
        )
        if with_history:
            for role, content in (("user", QUESTION), ("assistant", "Consider what is in your power.")):
                await s.execute(
                    text("INSERT INTO messages (id, conversation_id, user_id, role, content, safety_level, persona_id) "
                         "VALUES (:id, :c, :u, :r, :t, 'none', :p)"),
                    {"id": str(uuid.uuid4()), "c": cid, "u": live.user_id, "r": role, "t": content, "p": home_id},
                )
        await s.commit()
    return cid, home_slug, guest_slug


# ── INPUT paths ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_pre_generation_event_is_committed(live):
    """Control: production has 17 'pre_generation' rows, so this path is known to commit."""
    cid, _, _ = await _conversation(live, with_history=False)
    with _Patched(_no_network() + [
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
    ]):
        r = await live.client.post(f"/api/v1/conversations/{cid}/messages", json={"content": CRISIS})
    assert r.status_code == 200, r.text
    assert "safety" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["pre_generation"]


@pytest.mark.asyncio
async def test_council_input_event_is_committed(live):
    with _Patched(_no_network()):
        r = await live.client.post("/api/v1/council", json={"matter": CRISIS, "source": "direct"})
    assert r.status_code == 200, r.text
    assert "safety" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["council_input"]


@pytest.mark.asyncio
async def test_you_vs_you_input_event_is_committed(live):
    with _Patched(_no_network()):
        r = await live.client.post("/api/v1/self-comparison", json={"prompt": CRISIS})
    assert r.status_code == 200, r.text
    assert "safety" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["self_comparison_input"]


# ── OUTPUT paths: the reply is flagged after it streamed ───────────────────────

@pytest.mark.asyncio
async def test_chat_send_post_generation_event_is_committed(live):
    cid, _, _ = await _conversation(live, with_history=False)
    with _Patched(_no_network() + [
        patch("services.conversation_service.llm_client.stream", _fake_llm(HARMFUL_REPLY)),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
    ]):
        r = await live.client.post(f"/api/v1/conversations/{cid}/messages", json={"content": QUESTION})
    assert r.status_code == 200, r.text
    assert "safety_override" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["post_generation"]


@pytest.mark.asyncio
async def test_another_mind_post_generation_event_is_committed(live):
    cid, _, guest = await _conversation(live)
    with _Patched(_no_network() + [
        patch("services.conversation_service.llm_client.stream", _fake_llm(HARMFUL_REPLY)),
    ]):
        r = await live.client.post(f"/api/v1/conversations/{cid}/another-mind",
                                   json={"target_persona_slug": guest})
    assert r.status_code == 200, r.text
    assert "safety_override" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["post_generation"]


@pytest.mark.asyncio
async def test_go_deeper_post_generation_event_is_committed(live):
    cid, _, _ = await _conversation(live)
    with _Patched(_no_network() + [
        patch("services.conversation_service.llm_client.stream", _fake_llm(HARMFUL_REPLY)),
    ]):
        r = await live.client.post(f"/api/v1/conversations/{cid}/go-deeper")
    assert r.status_code == 200, r.text
    assert "safety_override" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["post_generation"]


@pytest.mark.asyncio
async def test_council_member_output_event_is_committed(live):
    with _Patched(_no_network() + [
        patch("services.council_service.llm_client.stream", _fake_llm(HARMFUL_REPLY)),
        patch("services.council_service.llm_client.complete", AsyncMock(return_value="")),
    ]):
        r = await live.client.post("/api/v1/council",
                                   json={"matter": "Should I leave my job this year?", "source": "direct"})
    assert r.status_code == 200, r.text
    assert "safety_override" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["council_member_output"]


@pytest.mark.asyncio
async def test_you_vs_you_output_event_is_committed(live):
    from datetime import datetime, timezone

    window = {"start": datetime(2026, 6, 1, tzinfo=timezone.utc), "end": datetime(2026, 7, 1, tzinfo=timezone.utc),
              "by_type": {"struggle": ["keeps postponing one decision"]}}
    closing = json.dumps({"observation": "Then… now…", "question": "Fair?", "then_quote_id": None,
                          "now_quote_id": None, "hidden_continuity": None, "sentence_owed": None})
    with _Patched(_no_network() + [
        patch("services.self_comparison_service.llm_client.stream", _fake_llm(HARMFUL_REPLY)),
        patch("services.self_comparison_service.llm_client.complete", AsyncMock(return_value=closing)),
        patch("services.self_comparison_service.self_model_service.build", AsyncMock(return_value={
            "unlocked": True, "total_signals": 30, "reason": None, "forming_preview": [],
            "then": window, "now": window,
        })),
    ]):
        r = await live.client.post("/api/v1/self-comparison", json={"prompt": QUESTION})
    assert r.status_code == 200, r.text
    assert "safety_override" in [e["type"] for e in _events(r)]
    assert await _stages(live) == ["self_comparison_output"]


# ── SAFETY-006: at the weekly limit, a crisis is answered, not refused ─────────
#
# The live user is an admin, and admins skip both weekly limits. These run as a
# NON-admin whose weekly_remaining is 0. A crisis message must get the crisis text
# and a COMMITTED row, and must create no case row (so no allowance is spent). An
# ordinary message at the same limit must still be refused with the 429.

async def _count(live, table) -> int:
    async with live.Session() as s:
        return (await s.execute(text(f"SELECT count(*) FROM {table} WHERE user_id = :u"),
                                {"u": live.user_id})).scalar_one()


def _at_limit(target):
    return patch(target, AsyncMock(return_value=0))


@pytest.mark.asyncio
async def test_council_crisis_at_the_weekly_limit_is_answered_and_committed(live):
    live.user.is_admin = False
    with _Patched(_no_network() + [_at_limit("routers.council.council_service.weekly_remaining")]):
        r = await live.client.post("/api/v1/council", json={"matter": CRISIS, "source": "direct"})
    assert r.status_code == 200, r.text
    safety = [e for e in _events(r) if e["type"] == "safety"]
    assert safety and safety[0]["text"], _events(r)
    assert await _stages(live) == ["council_input"]
    assert await _count(live, "council_cases") == 0


@pytest.mark.asyncio
async def test_council_ordinary_matter_at_the_weekly_limit_is_still_refused(live):
    live.user.is_admin = False
    with _Patched(_no_network() + [_at_limit("routers.council.council_service.weekly_remaining")]):
        r = await live.client.post("/api/v1/council", json={"matter": QUESTION, "source": "direct"})
    assert r.status_code == 429, r.text
    assert r.json()["error_code"] == "council_weekly_limit"
    assert await _stages(live) == []


@pytest.mark.asyncio
async def test_you_vs_you_crisis_at_the_weekly_limit_is_answered_and_committed(live):
    live.user.is_admin = False
    with _Patched(_no_network() + [_at_limit("routers.self_comparison.self_comparison_service.weekly_remaining")]):
        r = await live.client.post("/api/v1/self-comparison", json={"prompt": CRISIS})
    assert r.status_code == 200, r.text
    safety = [e for e in _events(r) if e["type"] == "safety"]
    assert safety and safety[0]["text"], _events(r)
    assert await _stages(live) == ["self_comparison_input"]
    assert await _count(live, "self_comparisons") == 0


@pytest.mark.asyncio
async def test_you_vs_you_ordinary_prompt_at_the_weekly_limit_is_still_refused(live):
    live.user.is_admin = False
    with _Patched(_no_network() + [_at_limit("routers.self_comparison.self_comparison_service.weekly_remaining")]):
        r = await live.client.post("/api/v1/self-comparison", json={"prompt": QUESTION})
    assert r.status_code == 429, r.text
    assert r.json()["error_code"] == "weekly_limit"
    assert await _stages(live) == []


# ── SAFETY-002: a RELEASED message is committed, and it costs what it should ───
#
# The judge is supplied (patched); everything else is real. A released message
# writes ONE row — the lexicon level, action_taken 'released', the judge record and
# no reason — and that row must be COMMITTED on the get_db streams (SAFETY-004). A
# released chat message is an ordinary turn: it is answered, stored as 'low', and
# consumes the daily allowance.

RELEASABLE = "What did the Stoics think about suicide as a rational choice?"   # B:HIGH, no keys
CLEAN_REPLY = "Consider what is in your power, and what is not."


def _released():
    from services.safety_judge import JudgeVerdict
    return patch("services.safety_judge.judge", AsyncMock(return_value=JudgeVerdict(
        verdict="DISCUSSING", failed=False, fail_kind=None,
        model="claude-haiku-4-5-20251001", latency_ms=900, input_tokens=1200, output_tokens=30)))


async def _rows(live):
    async with live.Session() as s:
        rows = await s.execute(
            text("SELECT trigger_stage, risk_level, action_taken, raw_flags FROM safety_events "
                 "WHERE user_id = :u ORDER BY created_at"),
            {"u": live.user_id},
        )
        return [tuple(r) for r in rows]


def _assert_one_released_row(rows, stage):
    assert [(r[0], r[1], r[2]) for r in rows] == [(stage, "high", "released")], rows
    judge = rows[0][3]["judge"]
    assert judge["outcome"] == "DISCUSSING" and "reason" not in judge


@pytest.mark.asyncio
async def test_a_released_council_matter_is_committed_and_convenes(live):
    with _Patched(_no_network() + [
        _released(),
        patch("services.council_service.llm_client.stream", _fake_llm(CLEAN_REPLY)),
        patch("services.council_service.llm_client.complete", AsyncMock(return_value="")),
    ]):
        r = await live.client.post("/api/v1/council", json={"matter": RELEASABLE, "source": "direct"})
    assert r.status_code == 200, r.text
    assert "safety" not in [e["type"] for e in _events(r)]
    _assert_one_released_row(await _rows(live), "council_input")
    assert await _count(live, "council_cases") == 1


@pytest.mark.asyncio
async def test_a_released_you_vs_you_prompt_is_committed_and_runs(live):
    from datetime import datetime, timezone

    window = {"start": datetime(2026, 6, 1, tzinfo=timezone.utc), "end": datetime(2026, 7, 1, tzinfo=timezone.utc),
              "by_type": {"struggle": ["keeps postponing one decision"]}}
    closing = json.dumps({"observation": "Then… now…", "question": "Fair?", "then_quote_id": None,
                          "now_quote_id": None, "hidden_continuity": None, "sentence_owed": None})
    with _Patched(_no_network() + [
        _released(),
        patch("services.self_comparison_service.llm_client.stream", _fake_llm(CLEAN_REPLY)),
        patch("services.self_comparison_service.llm_client.complete", AsyncMock(return_value=closing)),
        patch("services.self_comparison_service.self_model_service.build", AsyncMock(return_value={
            "unlocked": True, "total_signals": 30, "reason": None, "forming_preview": [],
            "then": window, "now": window,
        })),
    ]):
        r = await live.client.post("/api/v1/self-comparison", json={"prompt": RELEASABLE})
    assert r.status_code == 200, r.text
    assert "safety" not in [e["type"] for e in _events(r)]
    _assert_one_released_row(await _rows(live), "self_comparison_input")
    assert await _count(live, "self_comparisons") == 1


@pytest.mark.asyncio
async def test_a_released_chat_message_is_answered_stored_low_and_consumes_the_allowance(live):
    live.user.is_admin = False            # admins never consume an allowance
    cid, _, _ = await _conversation(live, with_history=False)
    with _Patched(_no_network() + [
        _released(),
        patch("services.conversation_service.llm_client.stream", _fake_llm(CLEAN_REPLY)),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
    ]):
        r = await live.client.post(f"/api/v1/conversations/{cid}/messages", json={"content": RELEASABLE})
    assert r.status_code == 200, r.text
    assert "safety" not in [e["type"] for e in _events(r)]
    _assert_one_released_row(await _rows(live), "pre_generation")
    async with live.Session() as s:
        level = (await s.execute(text(
            "SELECT safety_level FROM messages WHERE conversation_id = :c AND role = 'user'"),
            {"c": cid})).scalar_one()
        used = (await s.execute(text(
            "SELECT coalesce(sum(message_count), 0) FROM daily_usage WHERE user_id = :u"),
            {"u": live.user_id})).scalar_one()
    assert level == "low"
    assert used == 1
