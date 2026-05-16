"""Tests for POST /api/v1/messages endpoint.

Uses FastAPI TestClient with mocked llm_service and Anthropic SDK.
Run: cd apps/api && pytest tests/routers/test_messages.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from fastapi.testclient import TestClient

from models import Conversation, DailyUsage, Message
from services.llm_service import LLMResponse, MODEL_FREE, MODEL_PRO
from services.exceptions import LLMServiceUnavailable, PersonaAccessDenied

ENDPOINT = "/api/v1/messages"
USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
PERSONA_ID = "bbbbbbbb-0000-0000-0000-000000000001"
CONV_ID = "cccccccc-0000-0000-0000-000000000001"
OTHER_USER_ID = "dddddddd-0000-0000-0000-000000000001"

_MISSING = object()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(user_id=USER_ID):
    u = MagicMock()
    u.id = user_id
    u.is_admin = False
    return u


def _make_persona(tier="free"):
    p = MagicMock()
    p.id = PERSONA_ID
    p.tier = tier
    p.config = {"system_fragment": "You are a philosopher."}
    return p


def _make_conversation(
    message_count=0,
    deleted_at=None,
    title=None,
    user_id=USER_ID,
    persona_id=PERSONA_ID,
):
    c = MagicMock(spec=Conversation)
    c.id = CONV_ID
    c.user_id = user_id
    c.persona_id = persona_id
    c.message_count = message_count
    c.deleted_at = deleted_at
    c.title = title
    c.created_at = datetime.now(timezone.utc)
    c.last_message_at = None
    return c


def _make_subscription(active=True):
    if not active:
        return None
    s = MagicMock()
    s.status = "active"
    s.current_period_end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    return s


def _make_llm_response(model=MODEL_FREE, input_tokens=10, output_tokens=20, latency_ms=100):
    return LLMResponse(
        content="Virtue is its own reward.",
        model_used=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )


def _make_db(
    persona,
    existing_conv=_MISSING,
    subscription=None,
    daily_usage=None,
):
    """Build mock AsyncSession for the endpoint's execute sequence.

    - persona: always included (first execute)
    - existing_conv: if not _MISSING, adds a conversation lookup next
    - subscription: get_user_tier query (always after persona + optional conv)
    - daily_usage: DailyUsage lookup on success path
    """
    db = AsyncMock()
    db.add = MagicMock()       # session.add() is synchronous
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    def _r(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        return r

    side_effects = [_r(persona)]
    if existing_conv is not _MISSING:
        side_effects.append(_r(existing_conv))
    side_effects.append(_r(subscription))
    side_effects.append(_r(daily_usage))

    db.execute = AsyncMock(side_effect=side_effects)

    async def _refresh(obj, *args, **kwargs):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh)
    return db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user():
    return _make_user()


@pytest.fixture
def client(mock_user):
    from main import app
    from auth import get_current_user
    from db.session import get_db

    db_holder = [None]

    async def override_get_db():
        yield db_holder[0]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    test_client = TestClient(app, raise_server_exceptions=True)
    test_client._db = db_holder

    yield test_client

    app.dependency_overrides.clear()


# ── Success path ──────────────────────────────────────────────────────────────

def test_new_conversation_creates_conversation_and_returns_envelope(client):
    """POST without conversation_id: creates conversation, saves both messages, returns envelope."""
    persona = _make_persona("free")
    db = _make_db(persona=persona, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "Virtue is its own reward."
    assert data["message"]["model_used"] == MODEL_FREE
    assert data["message"]["tokens_used"] == 30
    assert data["conversation"]["persona_id"] == PERSONA_ID

    # Conversation object added to DB
    added = [c.args[0] for c in db.add.call_args_list]
    conversations = [o for o in added if isinstance(o, Conversation)]
    assert len(conversations) == 1

    # Both user and assistant messages added
    msgs = [o for o in added if isinstance(o, Message)]
    user_msgs = [m for m in msgs if m.role == "user"]
    asst_msgs = [m for m in msgs if m.role == "assistant"]
    assert len(user_msgs) == 1
    assert len(asst_msgs) == 1
    assert user_msgs[0].content == "Hello"
    assert asst_msgs[0].model_used == MODEL_FREE


def test_existing_conversation_appends_message(client):
    """POST with conversation_id: does not create new conversation, appends message."""
    persona = _make_persona("free")
    conv = _make_conversation(message_count=2)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()
        resp = client.post(
            ENDPOINT,
            json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "What is virtue?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation"]["id"] == CONV_ID

    # No new Conversation row should be added
    added = [c.args[0] for c in db.add.call_args_list]
    assert not any(isinstance(o, Conversation) for o in added)

    msgs = [o for o in added if isinstance(o, Message)]
    assert len(msgs) == 2  # user + assistant


def test_auto_title_enqueued_after_3rd_message(client):
    """When message_count reaches 3 and title is NULL, enqueue title generation."""
    from main import app

    persona = _make_persona("free")
    # Conversation starts at 1 (e.g., opening invocation not counted in message_count)
    # After += 2, message_count == 3
    conv = _make_conversation(message_count=1, title=None)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    mock_queue = AsyncMock()
    app.state.arq_queue = mock_queue

    try:
        with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_llm_response()
            resp = client.post(
                ENDPOINT,
                json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
            )

        assert resp.status_code == 200
        mock_queue.enqueue_job.assert_called_once_with(
            "generate_conversation_title", CONV_ID
        )
    finally:
        if hasattr(app.state, "arq_queue"):
            del app.state.arq_queue


def test_auto_title_not_enqueued_on_1st_message(client):
    """message_count starts at 0 → after update == 2 → no title enqueue."""
    from main import app

    persona = _make_persona("free")
    conv = _make_conversation(message_count=0, title=None)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    mock_queue = AsyncMock()
    app.state.arq_queue = mock_queue

    try:
        with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_llm_response()
            resp = client.post(
                ENDPOINT,
                json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
            )

        assert resp.status_code == 200
        mock_queue.enqueue_job.assert_not_called()
    finally:
        if hasattr(app.state, "arq_queue"):
            del app.state.arq_queue


def test_auto_title_not_enqueued_on_2nd_message(client):
    """message_count starts at 2 → after update == 4 → no title enqueue."""
    from main import app

    persona = _make_persona("free")
    conv = _make_conversation(message_count=2, title=None)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    mock_queue = AsyncMock()
    app.state.arq_queue = mock_queue

    try:
        with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_llm_response()
            resp = client.post(
                ENDPOINT,
                json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
            )

        assert resp.status_code == 200
        mock_queue.enqueue_job.assert_not_called()
    finally:
        if hasattr(app.state, "arq_queue"):
            del app.state.arq_queue


def test_auto_title_not_enqueued_on_4th_message(client):
    """message_count starts at 4 → after update == 6 → no title enqueue."""
    from main import app

    persona = _make_persona("free")
    conv = _make_conversation(message_count=4, title=None)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    mock_queue = AsyncMock()
    app.state.arq_queue = mock_queue

    try:
        with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_llm_response()
            resp = client.post(
                ENDPOINT,
                json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
            )

        assert resp.status_code == 200
        mock_queue.enqueue_job.assert_not_called()
    finally:
        if hasattr(app.state, "arq_queue"):
            del app.state.arq_queue


def test_daily_usage_new_row_created(client):
    """When no DailyUsage row exists, a new row with message_count=1 is added."""
    persona = _make_persona("free")
    db = _make_db(persona=persona, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 200
    added = [c.args[0] for c in db.add.call_args_list]
    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 1
    assert daily_usages[0].user_id == USER_ID
    assert daily_usages[0].persona_id == PERSONA_ID
    assert daily_usages[0].message_count == 1


def test_daily_usage_existing_row_incremented(client):
    """When a DailyUsage row already exists, message_count is incremented."""
    persona = _make_persona("free")
    existing_usage = DailyUsage(
        user_id=USER_ID, persona_id=PERSONA_ID,
        usage_date=__import__("datetime").date.today(), message_count=5,
    )
    db = _make_db(persona=persona, subscription=None, daily_usage=existing_usage)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 200
    assert existing_usage.message_count == 6

    # No new DailyUsage row added (we incremented, not created)
    added = [c.args[0] for c in db.add.call_args_list]
    assert not any(isinstance(o, DailyUsage) for o in added)


def test_conversation_message_count_and_last_message_at_updated(client):
    """After success, message_count += 2 and last_message_at is set."""
    persona = _make_persona("free")
    conv = _make_conversation(message_count=4)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response()
        resp = client.post(
            ENDPOINT,
            json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
        )

    assert resp.status_code == 200
    assert conv.message_count == 6
    assert conv.last_message_at is not None


# ── Access control ────────────────────────────────────────────────────────────

def test_unauthenticated_returns_401():
    """Sending an invalid JWT token returns 401."""
    from main import app
    c = TestClient(app, raise_server_exceptions=True)
    resp = c.post(
        ENDPOINT,
        json={"persona_id": PERSONA_ID, "content": "Hello"},
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert resp.status_code == 401


def test_free_user_free_persona_returns_200_with_haiku(client):
    """Free user + free persona → 200, model uses Haiku."""
    persona = _make_persona("free")
    db = _make_db(persona=persona, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(model=MODEL_FREE)
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 200
    assert resp.json()["message"]["model_used"] == MODEL_FREE


def test_pro_user_pro_persona_returns_200_with_sonnet(client, mock_user):
    """Pro user + pro persona → 200, model uses Sonnet."""
    persona = _make_persona("pro")
    sub = _make_subscription(active=True)
    db = _make_db(persona=persona, subscription=sub, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(model=MODEL_PRO)
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 200
    assert resp.json()["message"]["model_used"] == MODEL_PRO


def test_free_user_pro_persona_returns_403_persona_locked(client):
    """Free user + pro persona → 403 with persona_locked error. LLM is never called."""
    persona = _make_persona("pro")
    # subscription=None means free tier
    db = _make_db(persona=persona, subscription=None)
    # Only 2 execute calls needed: persona + get_user_tier (no daily_usage)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error_code"] == "persona_locked"
    assert "Pro" in detail["persona_voice"]
    mock_llm.assert_not_called()


def test_conversation_other_user_returns_404(client):
    """Conversation owned by a different user returns 404 (no existence hint)."""
    persona = _make_persona("free")
    conv = _make_conversation(user_id=OTHER_USER_ID)
    # Conversation lookup returns None because user_id filter excludes other users' convs
    db = _make_db(persona=persona, existing_conv=None, subscription=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock):
        resp = client.post(
            ENDPOINT,
            json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
        )

    assert resp.status_code == 404


def test_deleted_conversation_returns_404(client):
    """Conversation with deleted_at set returns 404."""
    persona = _make_persona("free")
    # deleted_at filter means the query returns None
    db = _make_db(persona=persona, existing_conv=None, subscription=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock):
        resp = client.post(
            ENDPOINT,
            json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
        )

    assert resp.status_code == 404


def test_persona_id_mismatch_returns_400(client):
    """conversation.persona_id != request.persona_id → 400."""
    DIFFERENT_PERSONA_ID = "eeeeeeee-0000-0000-0000-000000000001"
    persona = _make_persona("free")
    persona.id = PERSONA_ID
    # Conversation belongs to a different persona
    conv = _make_conversation(persona_id=DIFFERENT_PERSONA_ID)
    db = _make_db(persona=persona, existing_conv=conv, subscription=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock):
        resp = client.post(
            ENDPOINT,
            json={"persona_id": PERSONA_ID, "conversation_id": CONV_ID, "content": "Hello"},
        )

    assert resp.status_code == 400


# ── Error path ────────────────────────────────────────────────────────────────

def test_llm_unavailable_returns_503_with_fallback_voice(client):
    """LLMServiceUnavailable → 503 with generic fallback persona voice."""
    persona = _make_persona("free")
    db = _make_db(persona=persona, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMServiceUnavailable(persona_id=PERSONA_ID)
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["error_code"] == "llm_unavailable"
    assert len(detail["persona_voice"]) > 0


def test_user_message_saved_on_llm_failure(client):
    """User message persisted (committed) even when LLM fails; no assistant message."""
    persona = _make_persona("free")
    db = _make_db(persona=persona, subscription=None, daily_usage=None)
    client._db[0] = db

    with patch("routers.messages.llm_service_module.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMServiceUnavailable(persona_id=PERSONA_ID)
        resp = client.post(ENDPOINT, json={"persona_id": PERSONA_ID, "content": "Hello"})

    assert resp.status_code == 503

    # DB commit was called (persists user message)
    db.commit.assert_called()

    # Inspect what was added: 1 user msg, 0 assistant msgs
    added = [c.args[0] for c in db.add.call_args_list]
    msgs = [o for o in added if isinstance(o, Message)]
    user_msgs = [m for m in msgs if m.role == "user"]
    asst_msgs = [m for m in msgs if m.role == "assistant"]
    assert len(user_msgs) == 1
    assert len(asst_msgs) == 0


def test_content_too_long_returns_422(client):
    """content > 4000 chars → 422 validation error before handler runs."""
    persona = _make_persona("free")
    db = _make_db(persona=persona)
    client._db[0] = db

    resp = client.post(
        ENDPOINT,
        json={"persona_id": PERSONA_ID, "content": "x" * 4001},
    )
    assert resp.status_code == 422


def test_empty_content_returns_422(client):
    """Empty content string → 422 validation error."""
    persona = _make_persona("free")
    db = _make_db(persona=persona)
    client._db[0] = db

    resp = client.post(
        ENDPOINT,
        json={"persona_id": PERSONA_ID, "content": ""},
    )
    assert resp.status_code == 422
