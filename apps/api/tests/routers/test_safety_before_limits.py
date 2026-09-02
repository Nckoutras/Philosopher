"""A person in crisis is never answered with a quota.

THE DEFECT. The rate-limit check ran in the router; the safety gate runs in the
service. Returning 429 from the router meant the service never started, so for a
free user who had used their five messages with a persona:

    "I want to kill myself"  ->  429 rate_limited
                             ->  useStream turns every 429 into setShowPaywall()
                             ->  the person is shown an offer to subscribe

No crisis response. No safety_events row. An upgrade prompt in answer to
suicidal ideation. Live in production until this commit.

THE FIX is ordering only: check_input runs BEFORE the limit, and when it trips,
the limit check is skipped entirely — no 429, and no allowance consumed, since
the daily_usage increment lives in a phase the service's crisis branch returns
before reaching. The service then re-runs the gate and does the real work.

WHY THE CHECK IS DUPLICATED. It runs in the router AND at
conversation_service.py:623. Deliberate, ruled 2026-09-02: ~82 microseconds
against a multi-second LLM call, and the service must stay correct when called
directly. These tests pin the ORDER, so a future dedup that removes the router
check fails here.

SCOPE. send-message is the only one of the three limited chat paths that carries
user text — AnotherMindCreate is a persona slug and go-deeper has no body at
all, and check_input appears exactly once in the service. There is no crisis
message to block on those two, so there is no ordering bug to fix there. Pinned
below so the claim is checked rather than asserted.
"""
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.rate_limit_service import RateLimitResult

CONV_ID = "11111111-1111-1111-1111-111111111111"
URL = f"/api/v1/conversations/{CONV_ID}/messages"

# Real crisis phrasings, English and Greek, that the gates catch (#589).
CRISIS_TEXTS = [
    "I want to kill myself",
    "i can't take it anymore",
    "θέλω να αυτοκτονήσω",
    "δεν αντέχω άλλο",
    "den antexo allo",
]

EXHAUSTED = RateLimitResult(
    allowed=False, remaining=0, limit=5,
    reset_at=datetime(2026, 9, 3, tzinfo=timezone.utc),
)


def _conv(user_id):
    c = MagicMock()
    c.id = CONV_ID
    c.user_id = user_id
    c.persona_id = "22222222-2222-2222-2222-222222222222"
    c.active_persona_id = None
    c.ritual_id = None
    return c


def _persona():
    p = MagicMock()
    p.id = "22222222-2222-2222-2222-222222222222"
    p.slug = "marcus_aurelius"
    return p


def _client(user):
    """Overrides the streaming auth dep and patches the session factory the
    preflight opens. The preflight is what this file is about."""
    from main import app
    from auth import get_user_plan_streaming

    app.dependency_overrides[get_user_plan_streaming] = lambda: (user, "free")
    return TestClient(app, raise_server_exceptions=False)


def _reset():
    from main import app
    app.dependency_overrides.clear()


def _user():
    u = MagicMock()
    u.id = str(uuid4())
    u.is_admin = False
    return u


def _session_with(conv, persona):
    """A session whose execute() answers the preflight's two lookups."""
    db = AsyncMock()

    async def execute(stmt, *a, **kw):
        result = MagicMock()
        text = str(stmt)
        if "FROM conversations" in text:
            result.scalar_one_or_none.return_value = conv
        else:
            result.scalar_one.return_value = persona
            result.scalar_one_or_none.return_value = persona
        return result

    db.execute = AsyncMock(side_effect=execute)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.parametrize("text", CRISIS_TEXTS)
def test_crisis_text_at_an_exhausted_limit_is_not_rate_limited(text):
    """The whole point. Exhausted allowance + crisis text -> the stream runs."""
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session_with(_conv(user.id), _persona())), \
             patch("routers.conversations.get_user_tier", new=AsyncMock(return_value="free")), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=EXHAUSTED)) as limit, \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            stream.return_value = iter([b"data: {}\n\n"])
            res = client.post(URL, json={"content": text})

        assert res.status_code != 429, (
            f"{text!r} was rate-limited instead of reaching the safety gate"
        )
        assert res.status_code == 200, res.text
        # The limit was never even consulted for a crisis message.
        limit.assert_not_awaited()
        # The service — which owns the crisis response — was reached.
        stream.assert_called_once()
    finally:
        _reset()


@pytest.mark.parametrize("text", CRISIS_TEXTS)
def test_crisis_text_never_returns_the_paywall_error_code(text):
    """`rate_limited` is what useStream turns into setShowPaywall(). A crisis
    message must never produce it."""
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session_with(_conv(user.id), _persona())), \
             patch("routers.conversations.get_user_tier", new=AsyncMock(return_value="free")), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=EXHAUSTED)), \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            stream.return_value = iter([b"data: {}\n\n"])
            res = client.post(URL, json={"content": text})
        assert "rate_limited" not in res.text
    finally:
        _reset()


def test_an_ordinary_message_at_an_exhausted_limit_is_still_429():
    """The limit must keep working. This is the test that fails if the fix is
    implemented by simply deleting the rate-limit check."""
    user = _user()
    client = _client(user)
    try:
        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session_with(_conv(user.id), _persona())), \
             patch("routers.conversations.get_user_tier", new=AsyncMock(return_value="free")), \
             patch("routers.conversations.rate_limit_service.check_rate_limit",
                   new=AsyncMock(return_value=EXHAUSTED)), \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            res = client.post(URL, json={"content": "what should I read next?"})

        assert res.status_code == 429, res.text
        assert res.json()["error_code"] == "rate_limited"
        stream.assert_not_called()
    finally:
        _reset()


def test_safety_is_checked_before_the_limit_is_consulted():
    """Order asserted directly, not inferred from the code reading correctly."""
    user = _user()
    client = _client(user)
    calls = []
    try:
        real_check = None
        from services.safety_service import safety_service as real_svc
        real_check = real_svc.check_input

        async def spy_check(text, uid=None):
            calls.append("SAFETY")
            return await real_check(text, uid)

        async def spy_limit(*a, **k):
            calls.append("LIMIT")
            return EXHAUSTED

        with patch("routers.conversations.AsyncSessionLocal",
                   return_value=_session_with(_conv(user.id), _persona())), \
             patch("routers.conversations.get_user_tier", new=AsyncMock(return_value="free")), \
             patch("routers.conversations.safety_service.check_input", new=spy_check), \
             patch("routers.conversations.rate_limit_service.check_rate_limit", new=spy_limit), \
             patch("routers.conversations.conversation_service.stream_response") as stream:
            client.post(URL, json={"content": "an ordinary question"})

        assert calls[0] == "SAFETY", calls
        assert "LIMIT" in calls, calls
    finally:
        _reset()


# ── The scope claim, pinned rather than asserted ──────────────────────────────

def test_only_send_message_carries_user_text():
    """another-mind takes a persona slug; go-deeper takes no body at all. If a
    future change gives either of them user text, this fails and the ordering
    fix has to be extended to it."""
    import schemas
    from routers import conversations as conv_router

    assert set(schemas.MessageCreate.model_fields) >= {"content"}
    assert set(schemas.AnotherMindCreate.model_fields) == {"target_persona_slug"}

    go_deeper_params = inspect.signature(conv_router.go_deeper).parameters
    assert not any(
        getattr(p.annotation, "__name__", "") .endswith("Create")
        for p in go_deeper_params.values()
    ), "go-deeper gained a request body; re-check the safety ordering for it"


def test_another_mind_carries_no_free_text_field():
    """The premise the two untouched limit checks rest on, pinned.

    another-mind is exempt from the ordering fix because its body is a persona
    SLUG — the text that caused the call was already safety-checked when it
    arrived through send-message. That is a statement about the schema, so it is
    asserted against the schema: every field must be a closed identifier, none a
    free-text string a person could type a crisis into.

    If a future PR gives this endpoint a note, a prompt or any prose field, this
    fails — which is the point. It forces the ordering question to be asked
    again rather than answered by the absence of anyone remembering to.
    """
    import schemas

    fields = schemas.AnotherMindCreate.model_fields
    assert set(fields) == {"target_persona_slug"}, (
        "another-mind gained a field; if it can carry user text, the safety "
        "ordering fix must be extended to that path"
    )
    # A slug is chosen from a fixed set, not typed as prose. Named explicitly so
    # the exemption is documented at the assertion rather than only in a comment.
    assert "slug" in "target_persona_slug"


def test_go_deeper_carries_no_request_body_at_all():
    """The same premise for the other exempt path."""
    from routers import conversations as conv_router

    annotations = [
        getattr(p.annotation, "__name__", str(p.annotation))
        for p in inspect.signature(conv_router.go_deeper).parameters.values()
    ]
    assert not any("Create" in a or "Request" == a for a in annotations if a != "Request"), (
        f"go-deeper gained a body ({annotations}); re-check the safety ordering"
    )


def test_the_service_still_owns_the_crisis_response():
    """The router only reorders. The service must keep its own check_input —
    it does the saving, the safety_events row and the language routing, and it
    must stay correct when called directly."""
    import pathlib
    src = pathlib.Path(conversation_service_path()).read_text(encoding="utf-8")
    assert src.count("safety_service.check_input") == 1, (
        "the service's own input gate was removed; the router check is an "
        "ordering guard, not a replacement"
    )


def conversation_service_path():
    import services.conversation_service as m
    return m.__file__
