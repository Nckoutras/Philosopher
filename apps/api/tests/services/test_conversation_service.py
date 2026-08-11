"""Tests for tier-aware model selection and memory window in conversation_service.

Verifies that stream_response() selects the correct Anthropic model and
history window based on user_plan. All external I/O is mocked.

Run: cd apps/api && pytest tests/services/test_conversation_service.py -v
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

from services.conversation_service import ConversationService
from services.conversation_service import MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO
from services.conversation_service import MEMORY_MAX_ROWS_PRO, HISTORY_TOKEN_BUDGET_PRO


# ── Shared fixtures ───────────────────────────────────────────────────────────

USER_ID = "user-uuid-1"
CONV_ID = "conv-uuid-1"
PERSONA_ID = "persona-uuid-1"


def _mock_conv():
    c = MagicMock()
    c.id = CONV_ID
    c.persona_id = PERSONA_ID
    # No sticky guest ⇒ responder/quota/memory coalesce to persona_id.
    c.active_persona_id = None
    # No sticky deep mode ⇒ normal (non-deep) length path.
    c.deep_mode = False
    return c


def _mock_persona_db(slug="marcus_aurelius"):
    p = MagicMock()
    p.id = PERSONA_ID
    p.slug = slug
    return p


def _make_db(*, conv=None, persona_db=None, history=None):
    """Build a mock AsyncSession for stream_response.

    Execute call order in stream_response:
      1. Conversation load
      2. Persona load
      3. History query  (the one we care about for window testing)
      4. Save user message (flush)
      5. Update conversation (execute + commit)
    """
    db = AsyncMock()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv or _mock_conv()

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = persona_db or _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = history or []

    save_msg_result = MagicMock()
    save_msg_result.scalar_one_or_none.return_value = None

    update_result = MagicMock()

    db.execute = AsyncMock(side_effect=[
        conv_result,
        persona_result,
        history_result,
        save_msg_result,   # _save_message user
        save_msg_result,   # _save_message assistant
        update_result,     # update conversation metadata
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _saved_msg(role="assistant", msg_id="msg-uuid-1"):
    m = MagicMock()
    m.id = msg_id
    m.role = role
    m.created_at = None
    return m


async def _drain(gen):
    """Consume an async generator and return all yielded strings."""
    chunks = []
    async for item in gen:
        chunks.append(item)
    return chunks


def _factory(db):
    """Wrap a mock session as a `session_factory` for stream_response (§5 fix).

    stream_response now takes a factory and opens `async with session_factory()`
    once per DB phase. This returns the SAME mock db for every phase, so the
    existing ordered execute() side_effects continue to apply end-to-end.
    """
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


# ── Helper: run stream_response with all heavy dependencies patched ───────────

async def _run_stream(user_plan: str):
    """Run stream_response with all external services mocked.

    Returns (chunks, mock_llm_client) so tests can inspect both the SSE
    output and how llm_client.stream() was called.
    """
    service = ConversationService()

    mock_llm = AsyncMock()

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm.stream = fake_stream

    saved = _saved_msg()

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        # Safety — no suppression
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)

        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        mock_prompt.build_safety_response.return_value = "safe"

        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()

        # Patch _save_message to return a mock message
        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        gen = service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan=user_plan,
        )
        chunks = await _drain(gen)

    return chunks, mock_llm


# ── Section A: Model selection ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_user_uses_haiku():
    """Free user → llm_client.stream() called with MODEL_FREE (Haiku)."""
    called_with = {}

    service = ConversationService()

    async def capture_stream(*args, **kwargs):
        called_with.update(kwargs)
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()
        saved = _saved_msg()
        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
        ))

    assert called_with.get("model") == MODEL_FREE, (
        f"Expected model={MODEL_FREE!r}, got {called_with.get('model')!r}"
    )


@pytest.mark.asyncio
async def test_pro_user_uses_sonnet():
    """Pro user → llm_client.stream() called with MODEL_PRO (Sonnet)."""
    called_with = {}

    service = ConversationService()

    async def capture_stream(*args, **kwargs):
        called_with.update(kwargs)
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()
        saved = _saved_msg()
        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="pro",
        ))

    assert called_with.get("model") == MODEL_PRO, (
        f"Expected model={MODEL_PRO!r}, got {called_with.get('model')!r}"
    )


@pytest.mark.asyncio
async def test_premium_user_uses_sonnet():
    """Premium user is treated as pro → llm_client.stream() uses MODEL_PRO."""
    called_with = {}

    service = ConversationService()

    async def capture_stream(*args, **kwargs):
        called_with.update(kwargs)
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()
        saved = _saved_msg()
        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="premium",
        ))

    assert called_with.get("model") == MODEL_PRO, (
        f"Expected model={MODEL_PRO!r}, got {called_with.get('model')!r}"
    )


# ── Section B: History window ─────────────────────────────────────────────────

def _is_history_query(stmt) -> str | None:
    """Return the compiled SQL if `stmt` is the history-window query, else None.

    The history query is identified by SHAPE — a SELECT over `messages` carrying a
    LIMIT and the conclusion-exclusion filter — not by execute() call index. Queries
    have been added ahead of it over time (the onboarding-profile load at
    conversation_service.py:563 is the current one), and an index-based harness
    silently captures the wrong statement and reports a failure that has nothing to
    do with the history window.

    The `message_kind` clause is what separates it from the `.desc().limit(1)`
    last-user-message lookup in the another-mind / go-deeper paths, which is also a
    limited SELECT over `messages`.
    """
    try:
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        return None
    if (
        "FROM messages" in compiled
        and "LIMIT" in compiled.upper()
        and "message_kind" in compiled
    ):
        return compiled
    return None


def _make_db_capture_limit(captured: dict, *, history=None):
    """DB mock that records the compiled history query (LIMIT + ORDER BY).

    Identifies the history query by shape via _is_history_query; every other
    statement gets a generic result.
    """
    db = AsyncMock()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = history or []

    save_result = MagicMock()
    save_result.scalar_one_or_none.return_value = None
    update_result = MagicMock()

    call_index = {"n": 0}

    async def execute_side_effect(stmt, *args, **kwargs):
        n = call_index["n"]
        call_index["n"] += 1
        if n == 0:
            return conv_result
        if n == 1:
            return persona_result
        compiled = _is_history_query(stmt)
        if compiled is not None:
            captured["limit_clause"] = compiled
            return history_result
        return save_result

    db.execute = execute_side_effect
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


async def _run_stream_capture_limit(user_plan: str) -> dict:
    """Run stream_response, capture what limit value was used in the history query."""
    service = ConversationService()
    captured = {}

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = fake_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db_capture_limit(captured)
        saved = _saved_msg()
        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan=user_plan,
        ))

    return captured


@pytest.mark.asyncio
async def test_free_user_history_window_is_5():
    """Free user → history query uses LIMIT 5 (MEMORY_WINDOW_FREE)."""
    captured = await _run_stream_capture_limit("free")
    assert str(MEMORY_WINDOW_FREE) in captured.get("limit_clause", ""), (
        f"Expected LIMIT {MEMORY_WINDOW_FREE} in query, got: {captured.get('limit_clause')}"
    )


@pytest.mark.asyncio
async def test_pro_user_history_row_cap_is_the_backstop():
    """Pro user → history query uses LIMIT MEMORY_MAX_ROWS_PRO.

    Was LIMIT 20 (MEMORY_WINDOW_PRO). Pro no longer windows by message count: the
    query fetches up to the row backstop and the TOKEN budget does the bounding
    (see _fit_history_to_budget). Free is unchanged and still LIMIT 5.
    """
    captured = await _run_stream_capture_limit("pro")
    assert str(MEMORY_MAX_ROWS_PRO) in captured.get("limit_clause", ""), (
        f"Expected LIMIT {MEMORY_MAX_ROWS_PRO} in query, got: {captured.get('limit_clause')}"
    )


@pytest.mark.asyncio
async def test_premium_user_history_row_cap_is_the_backstop():
    """Premium user is treated as pro → same row backstop."""
    captured = await _run_stream_capture_limit("premium")
    assert str(MEMORY_MAX_ROWS_PRO) in captured.get("limit_clause", ""), (
        f"Expected LIMIT {MEMORY_MAX_ROWS_PRO} in query, got: {captured.get('limit_clause')}"
    )


# ── Section C: SSE output sanity checks ──────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_response_emits_start_chunk_done_for_free_user():
    """stream_response yields start, at least one chunk, and done events."""
    chunks, _ = await _run_stream("free")
    event_types = []
    for raw in chunks:
        import json as _json
        if raw.startswith("data: "):
            try:
                event_types.append(_json.loads(raw[6:])["type"])
            except Exception:
                pass

    assert "start" in event_types
    assert "chunk" in event_types
    assert "done" in event_types


@pytest.mark.asyncio
async def test_stream_response_emits_start_chunk_done_for_pro_user():
    """stream_response yields start, chunk, and done for a pro user too."""
    chunks, _ = await _run_stream("pro")
    event_types = []
    for raw in chunks:
        import json as _json
        if raw.startswith("data: "):
            try:
                event_types.append(_json.loads(raw[6:])["type"])
            except Exception:
                pass

    assert "start" in event_types
    assert "chunk" in event_types
    assert "done" in event_types


# ── Section D: daily_usage increment ─────────────────────────────────────────

from models import DailyUsage


def _make_db_for_usage(existing_usage=None, ritual_id=None):
    """DB mock with explicit ritual_id and controllable DailyUsage lookup result.

    Execute call order with _save_message mocked:
      1. select(Conversation)  → conv_result
      2. select(Persona)       → persona_result
      3. select(Message) hist  → history_result
      4. update(Conversation)  → update_result
      5. select(DailyUsage)    → usage_result  (only if ritual_id is None)
    """
    db = AsyncMock()

    conv = MagicMock()
    conv.id = CONV_ID
    conv.persona_id = PERSONA_ID
    conv.active_persona_id = None
    conv.deep_mode = False
    conv.ritual_id = ritual_id

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    update_result = MagicMock()

    usage_result = MagicMock()
    usage_result.scalar_one_or_none.return_value = existing_usage

    db.execute = AsyncMock(side_effect=[
        conv_result,
        persona_result,
        history_result,
        update_result,   # update(Conversation) — return value not used
        usage_result,    # select(DailyUsage)   — only reached when increment runs
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db, conv


async def _run_stream_for_usage(db, conv, is_admin: bool = False):
    """Run stream_response with all I/O mocked; return list of added objects."""
    service = ConversationService()
    saved = _saved_msg()

    mock_llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm.stream = fake_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
            is_admin=is_admin,
        ))

    return [c.args[0] for c in db.add.call_args_list]


@pytest.mark.asyncio
async def test_daily_usage_new_row_created_for_regular_conv():
    """Regular conv (ritual_id=None), non-admin success → new DailyUsage row with count=1."""
    db, conv = _make_db_for_usage(existing_usage=None, ritual_id=None)
    added = await _run_stream_for_usage(db, conv, is_admin=False)

    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 1
    assert daily_usages[0].user_id == USER_ID
    assert daily_usages[0].persona_id == PERSONA_ID
    assert daily_usages[0].message_count == 1


@pytest.mark.asyncio
async def test_daily_usage_existing_row_incremented():
    """Regular conv, existing DailyUsage row → message_count incremented, no new row."""
    existing = DailyUsage(
        user_id=USER_ID,
        persona_id=PERSONA_ID,
        usage_date=__import__("datetime").date.today(),
        message_count=3,
    )
    db, conv = _make_db_for_usage(existing_usage=existing, ritual_id=None)
    added = await _run_stream_for_usage(db, conv, is_admin=False)

    assert existing.message_count == 4
    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 0


@pytest.mark.asyncio
async def test_daily_usage_not_incremented_for_ritual_conv():
    """Ritual conv (ritual_id != None) → daily_usage SELECT never runs, no row added."""
    db, conv = _make_db_for_usage(existing_usage=None, ritual_id="ritual-uuid-1")
    added = await _run_stream_for_usage(db, conv, is_admin=False)

    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 0


@pytest.mark.asyncio
async def test_daily_usage_not_incremented_for_admin():
    """Admin (is_admin=True) → daily_usage SELECT never runs, no row added."""
    db, conv = _make_db_for_usage(existing_usage=None, ritual_id=None)
    added = await _run_stream_for_usage(db, conv, is_admin=True)

    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 0


# ── Section E: Auto-title enqueue ─────────────────────────────────────────────


def _make_db_for_auto_title(message_count=0, title=None):
    """DB mock with controllable message_count and title for auto-title tests.

    Execute call order (with _save_message mocked):
      1. select(Conversation)  → conv_result
      2. select(Persona)       → persona_result
      3. select(Message) hist  → history_result
      4. update(Conversation)  → update_result
      5. select(DailyUsage)    → usage_result
    """
    db = AsyncMock()

    conv = MagicMock()
    conv.id = CONV_ID
    conv.persona_id = PERSONA_ID
    conv.active_persona_id = None
    conv.deep_mode = False
    conv.ritual_id = None
    conv.message_count = message_count
    conv.title = title

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    update_result = MagicMock()

    usage_result = MagicMock()
    usage_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[
        conv_result,
        persona_result,
        history_result,
        update_result,
        usage_result,
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db, conv


async def _run_stream_for_auto_title(db, arq_queue=None):
    """Run stream_response with arq_queue and all I/O mocked."""
    service = ConversationService()
    saved = _saved_msg()

    mock_llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm.stream = fake_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
            arq_queue=arq_queue,
        ))


@pytest.mark.asyncio
async def test_auto_title_enqueued_at_3rd_message():
    """message_count starts at 1 → new_message_count == 3 → enqueue_job called."""
    db, conv = _make_db_for_auto_title(message_count=1, title=None)
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    mock_queue.enqueue_job.assert_any_call(
        "generate_conversation_title", CONV_ID
    )


def _title_calls(mock_queue):
    return [c for c in mock_queue.enqueue_job.call_args_list if c.args[0] == "generate_conversation_title"]


@pytest.mark.asyncio
async def test_auto_title_not_enqueued_at_2nd_message():
    """message_count starts at 0 → new_message_count == 2 → generate_conversation_title not enqueued."""
    db, conv = _make_db_for_auto_title(message_count=0, title=None)
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    assert len(_title_calls(mock_queue)) == 0


@pytest.mark.asyncio
async def test_auto_title_not_enqueued_at_4th_message():
    """message_count starts at 2 → new_message_count == 4 → generate_conversation_title not enqueued."""
    db, conv = _make_db_for_auto_title(message_count=2, title=None)
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    assert len(_title_calls(mock_queue)) == 0


@pytest.mark.asyncio
async def test_auto_title_not_enqueued_at_6th_message():
    """message_count starts at 4 → new_message_count == 6 → generate_conversation_title not enqueued."""
    db, conv = _make_db_for_auto_title(message_count=4, title=None)
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    assert len(_title_calls(mock_queue)) == 0


@pytest.mark.asyncio
async def test_auto_title_not_enqueued_when_title_exists():
    """message_count == 3 but title is already set → generate_conversation_title not enqueued."""
    db, conv = _make_db_for_auto_title(message_count=1, title="Existing Title")
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    assert len(_title_calls(mock_queue)) == 0


@pytest.mark.asyncio
async def test_auto_title_skipped_when_no_queue():
    """arq_queue=None → enqueue silently skipped, no AttributeError."""
    db, conv = _make_db_for_auto_title(message_count=1, title=None)

    await _run_stream_for_auto_title(db, arq_queue=None)


@pytest.mark.asyncio
async def test_auto_title_enqueued_with_correct_conv_id():
    """enqueue_job receives the conversation UUID as a string (not UUID object)."""
    db, conv = _make_db_for_auto_title(message_count=1, title=None)
    mock_queue = AsyncMock()

    await _run_stream_for_auto_title(db, arq_queue=mock_queue)

    title_call = next(c for c in mock_queue.enqueue_job.call_args_list if c.args[0] == "generate_conversation_title")
    assert title_call.args[1] == CONV_ID
    assert isinstance(title_call.args[1], str)


# ── Section F: LLM error handling and retry ──────────────────────────────────

import anthropic as _anthropic


class _FakeRateLimitError(_anthropic.RateLimitError):
    def __init__(self):
        pass  # status_code=429 inherited as class attribute


class _FakeAPIStatusError(_anthropic.APIStatusError):
    def __init__(self, code: int):
        self.status_code = code


class _FakeConnectionError(_anthropic.APIConnectionError):
    def __init__(self):
        pass


class _FakeTimeoutError(_anthropic.APITimeoutError):
    def __init__(self):
        pass


class _FakeAuthError(_anthropic.AuthenticationError):
    def __init__(self):
        pass  # status_code=401 inherited as class attribute


def _make_db_for_retry():
    """DB mock for retry tests: 4 execute calls covering both error and success paths.

    Error path consumes: conv, persona, history (3 of 4).
    Success path (ritual_id=MagicMock, so DailyUsage is skipped) consumes all 4.
    """
    db = AsyncMock()

    conv = _mock_conv()  # ritual_id is auto-MagicMock (not None) → DailyUsage skipped

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []
    update_result = MagicMock()

    db.execute = AsyncMock(side_effect=[
        conv_result,
        persona_result,
        history_result,
        update_result,  # update(Conversation) — only consumed on success
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_stream_factory(behaviors: list):
    """Return an async generator function that uses the next behavior per call.

    Each item in behaviors is either the string 'ok' (yield one chunk) or an
    exception instance to raise.
    """
    counter = {"n": 0}

    async def stream_func(*args, **kwargs):
        n = counter["n"]
        counter["n"] += 1
        b = behaviors[n] if n < len(behaviors) else "ok"
        if b == "ok":
            yield "Hello"
        else:
            raise b
            yield  # pragma: no cover — marks this as an async generator

    return stream_func


async def _run_retry(behaviors: list, *, persona_config=None, db=None, arq_queue=None):
    """Run stream_response with controllable LLM stream behaviors.

    Returns (chunks, mock_sleep, service, db).
    """
    service = ConversationService()
    saved = _saved_msg()

    mock_llm = MagicMock()
    mock_llm.stream = _make_stream_factory(behaviors)

    if db is None:
        db = _make_db_for_retry()

    if persona_config is None:
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        persona_config.config = {}

    mock_sleep = AsyncMock()

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona", return_value=persona_config),
        patch("asyncio.sleep", mock_sleep),
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        mock_prompt.build_safety_response.return_value = "safe"

        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        chunks = await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
            arq_queue=arq_queue,
        ))

    return chunks, mock_sleep, service, db


def _event_types(chunks):
    import json as _json
    types = []
    for raw in chunks:
        if raw.startswith("data: "):
            try:
                types.append(_json.loads(raw[6:])["type"])
            except Exception:
                pass
    return types


def _parse_error_event(chunks):
    import json as _json
    for raw in chunks:
        if raw.startswith("data: "):
            try:
                ev = _json.loads(raw[6:])
                if ev.get("type") == "error":
                    return ev
            except Exception:
                pass
    return None


# ── F1: Success on first attempt ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_success_first_attempt_normal_flow():
    """LLM succeeds on first attempt → start, chunk, done emitted; sleep not called."""
    chunks, mock_sleep, _, _ = await _run_retry(["ok"])

    types = _event_types(chunks)
    assert "start" in types
    assert "chunk" in types
    assert "done" in types
    assert "error" not in types
    mock_sleep.assert_not_called()


# ── F2: Retry succeeds on second attempt ─────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_retry_succeeds_second_attempt():
    """503 on attempt 1, success on attempt 2 → chunks + done; sleep once with delay 1."""
    chunks, mock_sleep, _, _ = await _run_retry([_FakeAPIStatusError(503), "ok"])

    types = _event_types(chunks)
    assert "chunk" in types
    assert "done" in types
    assert "error" not in types
    mock_sleep.assert_called_once_with(1)


# ── F3: All retries fail ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_all_three_retries_fail_503():
    """503 on all 3 attempts → error event, no done, no chunk; sleep delays sum to 7s."""
    chunks, mock_sleep, _, _ = await _run_retry([
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
    ])

    types = _event_types(chunks)
    assert "error" in types
    assert "done" not in types
    assert "chunk" not in types

    assert mock_sleep.call_count == 3
    sleep_delays = [c.args[0] for c in mock_sleep.call_args_list]
    assert sleep_delays == [1, 2, 4]


# ── F4: Non-retriable 4xx — no retry ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_non_retriable_401_no_retry_no_sleep():
    """401 AuthenticationError → error event immediately; no sleep, no retry."""
    chunks, mock_sleep, _, _ = await _run_retry([_FakeAuthError()])

    types = _event_types(chunks)
    assert "error" in types
    assert "done" not in types
    assert "chunk" not in types
    mock_sleep.assert_not_called()


# ── F5: Connection error retries, succeeds on third attempt ──────────────────

@pytest.mark.asyncio
async def test_llm_connection_error_retries_succeed_third():
    """Connection error on attempts 1 & 2, success on 3 → normal flow; sleep twice."""
    chunks, mock_sleep, _, _ = await _run_retry([
        _FakeConnectionError(),
        _FakeConnectionError(),
        "ok",
    ])

    types = _event_types(chunks)
    assert "chunk" in types
    assert "done" in types
    assert "error" not in types
    assert mock_sleep.call_count == 2
    assert [c.args[0] for c in mock_sleep.call_args_list] == [1, 2]


# ── F6: Persona-voiced error message ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_error_event_uses_persona_specific_voice():
    """Error event persona_voice uses persona's custom error_messages when present."""
    persona_config = MagicMock()
    persona_config.slug = "marcus_aurelius"
    persona_config.config = {
        "error_messages": {"llm_unavailable": "The divine logos is silent."}
    }

    chunks, _, _, _ = await _run_retry(
        [_FakeAPIStatusError(503), _FakeAPIStatusError(503), _FakeAPIStatusError(503)],
        persona_config=persona_config,
    )

    ev = _parse_error_event(chunks)
    assert ev is not None
    assert ev["persona_voice"] == "The divine logos is silent."


# ── F7: Fallback voice when no custom error_messages ─────────────────────────

@pytest.mark.asyncio
async def test_error_event_falls_back_to_generic_voice():
    """Error event persona_voice uses the generic fallback when persona has no error_messages."""
    persona_config = MagicMock()
    persona_config.slug = "marcus_aurelius"
    persona_config.config = {}  # no error_messages key

    chunks, _, _, _ = await _run_retry(
        [_FakeAPIStatusError(503), _FakeAPIStatusError(503), _FakeAPIStatusError(503)],
        persona_config=persona_config,
    )

    ev = _parse_error_event(chunks)
    assert ev is not None
    assert ev["persona_voice"] == "I'm having trouble responding. Please try again in a moment."


# ── F8: User message persists on failure ─────────────────────────────────────

@pytest.mark.asyncio
async def test_user_message_persists_on_llm_failure():
    """db.commit() is called even when all LLM retries fail (user message must be saved)."""
    _, _, service, db = await _run_retry([
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
    ])

    db.commit.assert_called_once()


# ── F9: Assistant message not saved on failure ────────────────────────────────

@pytest.mark.asyncio
async def test_assistant_message_not_saved_on_llm_failure():
    """_save_message called only once (for user message) when all LLM retries fail."""
    _, _, service, _ = await _run_retry([
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
    ])

    assert service._save_message.call_count == 1
    saved_role = service._save_message.call_args_list[0].args[3]
    assert saved_role == "user"


# ── F10: daily_usage not incremented on failure ───────────────────────────────

@pytest.mark.asyncio
async def test_daily_usage_not_incremented_on_llm_failure():
    """No DailyUsage row added or incremented when all LLM retries fail."""
    from models import DailyUsage
    _, _, _, db = await _run_retry([
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
        _FakeAPIStatusError(503),
    ])

    added = [c.args[0] for c in db.add.call_args_list]
    daily_usages = [o for o in added if isinstance(o, DailyUsage)]
    assert len(daily_usages) == 0


# ── Section G: Memory extraction enqueue ─────────────────────────────────────


def _make_db_for_memory(message_count=0, ritual_id=None, safety_out_suppressed=False, is_admin=False):
    """DB mock for memory extraction tests.

    Execute call order (with _save_message mocked):
      1. select(Conversation)  → conv_result
      2. select(Persona)       → persona_result
      3. select(Message) hist  → history_result
      4. update(Conversation)  → update_result
      5. select(DailyUsage)    → usage_result  (only when ritual_id is None, not admin, not suppressed)
    """
    db = AsyncMock()

    conv = MagicMock()
    conv.id = CONV_ID
    conv.persona_id = PERSONA_ID
    conv.active_persona_id = None
    conv.deep_mode = False
    conv.ritual_id = ritual_id
    conv.message_count = message_count
    conv.title = "Existing Title"  # prevent auto-title interference

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    update_result = MagicMock()

    usage_result = MagicMock()
    usage_result.scalar_one_or_none.return_value = None

    side_effects = [conv_result, persona_result, history_result, update_result]
    if not is_admin and ritual_id is None and not safety_out_suppressed:
        side_effects.append(usage_result)

    db.execute = AsyncMock(side_effect=side_effects)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db, conv


async def _run_stream_for_memory(db, arq_queue=None, safety_out_suppressed=False, is_admin=False):
    """Run stream_response for memory extraction testing."""
    service = ConversationService()
    saved = _saved_msg()

    mock_llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm.stream = fake_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_in = MagicMock()
        safety_in.should_log = False
        safety_in.should_suppress_persona = False
        safety_in.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_in)

        safety_out = MagicMock()
        safety_out.should_suppress_persona = safety_out_suppressed
        safety_out.level = "none"
        mock_safety.check_output = AsyncMock(return_value=safety_out)

        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        mock_prompt.build_safety_response.return_value = "safe text"

        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        service._save_message = AsyncMock(return_value=saved)
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
            is_admin=is_admin,
            arq_queue=arq_queue,
        ))


@pytest.mark.asyncio
async def test_memory_extraction_enqueued_on_success():
    """Successful exchange → extract_memory_task enqueued with all correct args."""
    db, _ = _make_db_for_memory(message_count=0)
    mock_queue = AsyncMock()

    await _run_stream_for_memory(db, arq_queue=mock_queue)

    mock_queue.enqueue_job.assert_any_call(
        "extract_memory_task",
        USER_ID,
        CONV_ID,
        PERSONA_ID,
        "What is virtue?",
        "Hello",
        0,
        True,
    )


@pytest.mark.asyncio
async def test_memory_extraction_not_enqueued_when_post_safety_suppressed():
    """Post-gen safety suppression → extract_memory_task NOT enqueued."""
    db, _ = _make_db_for_memory(message_count=0, safety_out_suppressed=True)
    mock_queue = AsyncMock()

    await _run_stream_for_memory(db, arq_queue=mock_queue, safety_out_suppressed=True)

    memory_calls = [
        c for c in mock_queue.enqueue_job.call_args_list
        if c.args[0] == "extract_memory_task"
    ]
    assert len(memory_calls) == 0


@pytest.mark.asyncio
async def test_memory_extraction_not_enqueued_when_pre_safety_suppressed():
    """Pre-gen safety suppression → early return before hook → extract_memory_task NOT enqueued."""
    db = AsyncMock()
    conv = MagicMock()
    conv.id = CONV_ID
    conv.persona_id = PERSONA_ID
    conv.active_persona_id = None
    conv.deep_mode = False

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    db.execute = AsyncMock(side_effect=[conv_result, persona_result])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    service = ConversationService()
    mock_queue = AsyncMock()

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service"),
        patch("services.conversation_service.retrieval_service"),
        patch("services.conversation_service.llm_client"),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_in = MagicMock()
        safety_in.should_log = False
        safety_in.should_suppress_persona = True
        safety_in.level = "high"
        mock_safety.check_input = AsyncMock(return_value=safety_in)
        mock_prompt.build_safety_response.return_value = "safe"

        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        service._save_message = AsyncMock(return_value=_saved_msg())
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="harmful content",
            user_plan="free",
            arq_queue=mock_queue,
        ))

    mock_queue.enqueue_job.assert_not_called()


@pytest.mark.asyncio
async def test_memory_extraction_not_enqueued_on_llm_failure():
    """All LLM retries fail → early return before hook → extract_memory_task NOT enqueued."""
    mock_queue = AsyncMock()
    await _run_retry(
        [_FakeAPIStatusError(503), _FakeAPIStatusError(503), _FakeAPIStatusError(503)],
        arq_queue=mock_queue,
    )

    memory_calls = [
        c for c in mock_queue.enqueue_job.call_args_list
        if c.args[0] == "extract_memory_task"
    ]
    assert len(memory_calls) == 0


@pytest.mark.asyncio
async def test_memory_extraction_enqueued_for_ritual_conv():
    """Ritual conversation → extract_memory_task IS enqueued (ritual memories are valuable)."""
    db, _ = _make_db_for_memory(message_count=0, ritual_id="ritual-uuid-1")
    mock_queue = AsyncMock()

    await _run_stream_for_memory(db, arq_queue=mock_queue)

    memory_calls = [
        c for c in mock_queue.enqueue_job.call_args_list
        if c.args[0] == "extract_memory_task"
    ]
    assert len(memory_calls) == 1


@pytest.mark.asyncio
async def test_memory_extraction_enqueued_for_admin():
    """Admin user → extract_memory_task IS enqueued (admin testing should exercise full flow)."""
    db, _ = _make_db_for_memory(message_count=0, is_admin=True)
    mock_queue = AsyncMock()

    await _run_stream_for_memory(db, arq_queue=mock_queue, is_admin=True)

    memory_calls = [
        c for c in mock_queue.enqueue_job.call_args_list
        if c.args[0] == "extract_memory_task"
    ]
    assert len(memory_calls) == 1


@pytest.mark.asyncio
async def test_memory_extraction_no_error_when_queue_is_none():
    """arq_queue=None → enqueue silently skipped, no AttributeError."""
    db, _ = _make_db_for_memory(message_count=0)

    await _run_stream_for_memory(db, arq_queue=None)


# ── create_cross_persona ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_cross_persona_sets_source_columns_and_no_messages():
    """
    create_cross_persona() must:
    - Create a Conversation with source_saved_line_id + source_persona_slug set.
    - NOT call llm_client.complete (no bootstrap message).
    - NOT save any Message row.
    """
    from models import SavedLine, Persona, Conversation, Message

    SAVED_LINE_ID = "sl-uuid-1"
    USER_ID_CP    = "user-uuid-cp"
    SRC_SLUG      = "marcus_aurelius"
    TGT_SLUG      = "socrates"

    # Saved line mock
    mock_saved_line = MagicMock(spec=SavedLine)
    mock_saved_line.id = SAVED_LINE_ID
    mock_saved_line.user_id = USER_ID_CP
    mock_saved_line.persona_id = "src-persona-id"
    mock_saved_line.message_id = "msg-id-1"

    # Source persona mock
    mock_src_persona = MagicMock(spec=Persona)
    mock_src_persona.id = "src-persona-id"
    mock_src_persona.slug = SRC_SLUG

    # Target persona mock
    mock_tgt_persona = MagicMock(spec=Persona)
    mock_tgt_persona.id = "tgt-persona-id"
    mock_tgt_persona.slug = TGT_SLUG

    # Build DB mock with ordered execute responses
    db = AsyncMock()
    results = []
    for return_val, method in [
        (mock_saved_line, "scalar_one_or_none"),
        (mock_src_persona, "scalar_one"),
        (mock_tgt_persona, "scalar_one_or_none"),
    ]:
        r = MagicMock()
        getattr(r, method).return_value = return_val
        results.append(r)

    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock()
    db.flush = AsyncMock()

    added_objects: list = []
    db.add.side_effect = added_objects.append

    service = ConversationService()

    with patch("services.conversation_service.llm_client") as mock_llm:
        conv = await service.create_cross_persona(
            db=db,
            user_id=USER_ID_CP,
            saved_line_id=SAVED_LINE_ID,
            target_persona_slug=TGT_SLUG,
        )

    # LLM must NOT have been called
    mock_llm.complete.assert_not_called()

    # Exactly one object added: the Conversation (no Message)
    message_objects = [o for o in added_objects if isinstance(o, Message)]
    assert len(message_objects) == 0

    # Conversation has correct source columns
    conv_objects = [o for o in added_objects if isinstance(o, Conversation)]
    assert len(conv_objects) == 1
    assert conv_objects[0].source_saved_line_id == SAVED_LINE_ID
    assert conv_objects[0].source_persona_slug == SRC_SLUG


# ── Section H: skip_opening flag ────────────────────────────────────────────

from models import Message, Conversation


def _make_create_db(*, has_existing=False, existing_conv=None):
    """DB mock for conversation_service.create() tests.

    Execute call order:
      1. select(Persona) by slug         → persona_result
      2. select(Conversation) dedup      → dedup_result  (only when not skip_opening)
      Both flush() calls → no-op.
    """
    db = AsyncMock()

    mock_persona = MagicMock()
    mock_persona.id = PERSONA_ID
    mock_persona.slug = "marcus_aurelius"

    persona_result = MagicMock()
    persona_result.scalar_one_or_none.return_value = mock_persona

    dedup_result = MagicMock()
    dedup_result.scalar_one_or_none.return_value = existing_conv

    db.execute = AsyncMock(side_effect=[persona_result, dedup_result])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_persona_config(*, has_opening=True):
    cfg = MagicMock()
    cfg.opening_invocation = "Greetings, mortal." if has_opening else None
    return cfg


@pytest.mark.asyncio
async def test_create_with_skip_opening_no_assistant_message():
    """skip_opening=True → no Message row added (opening_invocation suppressed)."""
    db = _make_create_db()

    service = ConversationService()

    with patch("services.conversation_service.get_persona", return_value=_make_persona_config(has_opening=True)), \
         patch("services.conversation_service.is_persona_accessible", return_value=True):
        added: list = []
        db.add.side_effect = added.append

        await service.create(
            db=db,
            user_id=USER_ID,
            persona_slug="marcus_aurelius",
            skip_opening=True,
        )

    message_objects = [o for o in added if isinstance(o, Message)]
    assert len(message_objects) == 0


@pytest.mark.asyncio
async def test_create_without_skip_opening_has_opening_message():
    """skip_opening=False (default) → opening_invocation Message row IS added."""
    db = _make_create_db(has_existing=False)

    service = ConversationService()

    with patch("services.conversation_service.get_persona", return_value=_make_persona_config(has_opening=True)), \
         patch("services.conversation_service.is_persona_accessible", return_value=True):
        added: list = []
        db.add.side_effect = added.append

        await service.create(
            db=db,
            user_id=USER_ID,
            persona_slug="marcus_aurelius",
            skip_opening=False,
        )

    message_objects = [o for o in added if isinstance(o, Message)]
    assert len(message_objects) == 1
    assert message_objects[0].role == "assistant"
    assert message_objects[0].content == "Greetings, mortal."


@pytest.mark.asyncio
async def test_create_skip_opening_bypasses_dedup():
    """skip_opening=True → dedup SELECT never executes; always a fresh Conversation."""
    # Only one execute side_effect (persona load); a second execute would raise StopAsyncIteration
    db = AsyncMock()

    mock_persona = MagicMock()
    mock_persona.id = PERSONA_ID
    mock_persona.slug = "marcus_aurelius"

    persona_result = MagicMock()
    persona_result.scalar_one_or_none.return_value = mock_persona

    db.execute = AsyncMock(side_effect=[persona_result])  # only one call expected
    db.add = MagicMock()
    db.flush = AsyncMock()

    service = ConversationService()

    with patch("services.conversation_service.get_persona", return_value=_make_persona_config(has_opening=True)), \
         patch("services.conversation_service.is_persona_accessible", return_value=True):
        await service.create(
            db=db,
            user_id=USER_ID,
            persona_slug="marcus_aurelius",
            skip_opening=True,
        )

    # If dedup ran, execute would have been called twice and the second call
    # would have returned the existing conv. Verify only one execute call.
    assert db.execute.call_count == 1


# ══════════════════════════════════════════════════════════════════════════════
# PR-OPT-4a — embed the user text once per turn (dedup recall + retrieval query)
# ══════════════════════════════════════════════════════════════════════════════
#
# Each chat turn now embeds the user text ONCE and reuses the vector for both
# memory recall and RAG retrieval (was two identical embeds). Verified here:
#   1. recall()/retrieve() accept a precomputed embedding and use it verbatim as
#      the SQL query_vec — identical to the internal-embed path — with no second
#      embed call.
#   2. When no embedding is passed, each falls back to embedding internally once.
#   3. Each of the three chat paths (main / another-mind / go-deeper) embeds the
#      user text exactly once and hands the SAME vector to both consumers.

from services.memory_service import memory_service as _memory_singleton
from services.retrieval_service import retrieval_service as _retrieval_singleton


@pytest.fixture(autouse=True)
def _patch_conv_embedding_client():
    """Neutralise the real OpenAI embedding client for every test in this module.

    stream_response / stream_another_mind / stream_go_deeper now call
    embedding_client.embed() directly; without this the existing tests (which mock
    recall/retrieve but not the embed) would attempt a live network call. Yields
    the mock so the count/vector-reuse tests can inspect it."""
    with patch("services.conversation_service.embedding_client") as m:
        m.embed = AsyncMock(return_value=[0.11, 0.22, 0.33])
        yield m


# ── recall(): precomputed embedding used verbatim; None falls back ────────────

def _query_db():
    """Mock session whose execute() returns an empty-rows result (fetchall → [])."""
    db = AsyncMock()
    exec_result = MagicMock()
    exec_result.fetchall.return_value = []
    db.execute = AsyncMock(return_value=exec_result)
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_recall_uses_precomputed_embedding_verbatim():
    """query_embedding provided → no internal embed; that exact vector is the SQL query_vec."""
    db = _query_db()
    vec = [1.0, 2.0, 3.0]
    with patch("services.memory_service.embedding_client") as m:
        m.embed = AsyncMock(return_value=[9.9])  # must NOT be used
        await _memory_singleton.recall(db, "user-1", "what is virtue?", query_embedding=vec)
        m.embed.assert_not_called()
    assert db.execute.call_args.args[1]["query_vec"] == str(vec)


@pytest.mark.asyncio
async def test_recall_falls_back_to_internal_embed_when_none():
    """query_embedding=None → embeds internally once; that vector is the SQL query_vec."""
    db = _query_db()
    internal = [7.0, 8.0]
    with patch("services.memory_service.embedding_client") as m:
        m.embed = AsyncMock(return_value=internal)
        await _memory_singleton.recall(db, "user-1", "what is virtue?")
        m.embed.assert_called_once()
    assert db.execute.call_args.args[1]["query_vec"] == str(internal)


# ── retrieve(): precomputed embedding used verbatim; None falls back ──────────

def _retrieve_persona():
    p = MagicMock()
    p.slug = "marcus_aurelius"
    p.retrieval_top_k = 5
    return p


@pytest.mark.asyncio
async def test_retrieve_uses_precomputed_embedding_verbatim():
    """query_embedding provided → no internal embed; that exact vector is the SQL query_vec."""
    db = _query_db()
    vec = [1.0, 2.0, 3.0]
    with patch("services.retrieval_service.embedding_client") as m:
        m.embed = AsyncMock(return_value=[9.9])  # must NOT be used
        await _retrieval_singleton.retrieve(db, "what is virtue?", _retrieve_persona(), query_embedding=vec)
        m.embed.assert_not_called()
    assert db.execute.call_args.args[1]["query_vec"] == str(vec)


@pytest.mark.asyncio
async def test_retrieve_falls_back_to_internal_embed_when_none():
    """query_embedding=None → embeds internally once; that vector is the SQL query_vec."""
    db = _query_db()
    internal = [7.0, 8.0]
    with patch("services.retrieval_service.embedding_client") as m:
        m.embed = AsyncMock(return_value=internal)
        await _retrieval_singleton.retrieve(db, "what is virtue?", _retrieve_persona())
        m.embed.assert_called_once()
    assert db.execute.call_args.args[1]["query_vec"] == str(internal)


# ── One embed per turn, reused by both consumers — the 3 chat paths ───────────

class _StopAfterRetrieval(Exception):
    """Sentinel raised from build_system to abort a path right after recall+retrieve,
    so the embed-dedup can be asserted without mocking the whole downstream flow."""


@pytest.mark.asyncio
async def test_main_path_embeds_once_and_reuses_vector(_patch_conv_embedding_client):
    """stream_response embeds user_text once; that vector goes to both recall & retrieve."""
    service = ConversationService()

    mock_llm = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "Hello"

    mock_llm.stream = fake_stream

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()
        service._save_message = AsyncMock(return_value=_saved_msg())
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="free",
        ))

        embed_mock = _patch_conv_embedding_client.embed
        embed_mock.assert_called_once_with("What is virtue?")
        expected_vec = embed_mock.return_value
        assert mock_memory.recall.call_args.kwargs["query_embedding"] == expected_vec
        assert mock_retrieval.retrieve.call_args.kwargs["query_embedding"] == expected_vec


@pytest.mark.asyncio
async def test_another_mind_embeds_once_and_reuses_vector(_patch_conv_embedding_client):
    """stream_another_mind embeds last_user_text once; that vector goes to both consumers."""
    service = ConversationService()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    last_user_result = MagicMock()
    last_user_result.scalar_one_or_none.return_value = "What is courage?"

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[conv_result, persona_result, last_user_result])
    db.rollback = AsyncMock()

    with (
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        persona_config = MagicMock()
        persona_config.slug = "socrates"
        mock_get_persona.return_value = persona_config
        # Abort right after retrieval — avoids mocking the entire downstream flow.
        mock_prompt.build_system.side_effect = _StopAfterRetrieval()

        with pytest.raises(_StopAfterRetrieval):
            await _drain(service.stream_another_mind(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                target_persona_slug="socrates",
            ))

        embed_mock = _patch_conv_embedding_client.embed
        embed_mock.assert_called_once_with("What is courage?")
        expected_vec = embed_mock.return_value
        assert mock_memory.recall.call_args.kwargs["query_embedding"] == expected_vec
        assert mock_retrieval.retrieve.call_args.kwargs["query_embedding"] == expected_vec


@pytest.mark.asyncio
async def test_go_deeper_embeds_once_and_reuses_vector(_patch_conv_embedding_client):
    """stream_go_deeper embeds last_user_text once; that vector goes to both consumers."""
    service = ConversationService()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    thread_result = MagicMock(); thread_result.scalar.return_value = 0
    last_std_result = MagicMock(); last_std_result.scalar.return_value = None
    turn_result = MagicMock(); turn_result.scalar.return_value = 0
    last_user_result = MagicMock(); last_user_result.scalar_one_or_none.return_value = "Say more about virtue."

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        conv_result, persona_result, thread_result, last_std_result, turn_result, last_user_result,
    ])
    db.rollback = AsyncMock()

    with (
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config
        # is_admin=True skips the daily go-deeper gate; abort right after retrieval.
        mock_prompt.build_system.side_effect = _StopAfterRetrieval()

        with pytest.raises(_StopAfterRetrieval):
            await _drain(service.stream_go_deeper(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                user_plan="free",
                is_admin=True,
            ))

        embed_mock = _patch_conv_embedding_client.embed
        embed_mock.assert_called_once_with("Say more about virtue.")
        expected_vec = embed_mock.return_value
        assert mock_memory.recall.call_args.kwargs["query_embedding"] == expected_vec
        assert mock_retrieval.retrieve.call_args.kwargs["query_embedding"] == expected_vec


# ══════════════════════════════════════════════════════════════════════════════
# History window must select the NEWEST N messages, not the oldest
# ══════════════════════════════════════════════════════════════════════════════
#
# All three chat paths used `ORDER BY created_at ASC LIMIT N`, which returns the
# OLDEST N rows of the conversation. Past turn N the persona never saw its own
# recent output — a UAT tester quoted the persona's previous sentence back and was
# told "I didn't say that — you did". The fix is DESC + limit (newest N) followed by
# reversed() (chronological for the LLM), matching council_service._distill_brief.
#
# Covered here:
#   1. The compiled history query orders created_at DESC on all three paths.
#   2. stream_response actually hands the LLM the most recent window, in order.


def _order_by_clause(compiled_sql: str) -> str:
    """Slice the ORDER BY clause out of a compiled statement string.

    Kept to the ORDER BY..LIMIT span so an ASC/DESC assertion cannot be satisfied
    (or defeated) by some unrelated part of the query text.
    """
    upper = compiled_sql.upper()
    start = upper.find("ORDER BY")
    assert start != -1, f"No ORDER BY in compiled history query: {compiled_sql}"
    end = upper.find("LIMIT", start)
    return compiled_sql[start:] if end == -1 else compiled_sql[start:end]


def _assert_desc(clause: str, path: str):
    assert "DESC" in clause.upper(), (
        f"{path}: history query must order created_at DESC (newest N), "
        f"got ORDER BY clause: {clause!r}"
    )
    assert "ASC" not in clause.upper(), (
        f"{path}: history query must not order created_at ASC (oldest N), "
        f"got ORDER BY clause: {clause!r}"
    )


class _StopAfterHistory(Exception):
    """Sentinel raised once the history query has been compiled and captured, so a
    path aborts without the whole downstream stream flow needing to be mocked."""


def _capture_history_sql(captured: dict, *, pre_results: list):
    """DB mock that records the compiled history query (detected by shape) and then
    aborts via _StopAfterHistory. Statements ahead of it are served from pre_results
    in order; anything unexpected gets a generic MagicMock."""
    db = AsyncMock()
    call_index = {"n": 0}

    async def execute_side_effect(stmt, *args, **kwargs):
        compiled = _is_history_query(stmt)
        if compiled is not None:
            captured["sql"] = compiled
            raise _StopAfterHistory()
        n = call_index["n"]
        call_index["n"] += 1
        return pre_results[n] if n < len(pre_results) else MagicMock()

    db.execute = execute_side_effect
    db.rollback = AsyncMock()
    return db


# ── 1. Compiled query orders DESC — all three paths ───────────────────────────

@pytest.mark.asyncio
async def test_main_path_history_query_orders_desc():
    """stream_response history query → ORDER BY created_at DESC (newest N)."""
    captured = await _run_stream_capture_limit("pro")
    _assert_desc(_order_by_clause(captured["limit_clause"]), "stream_response")


@pytest.mark.asyncio
async def test_another_mind_history_query_orders_desc():
    """stream_another_mind history query → ORDER BY created_at DESC (newest N)."""
    service = ConversationService()
    captured = {}

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    last_user_result = MagicMock()
    last_user_result.scalar_one_or_none.return_value = "What is courage?"

    db = _capture_history_sql(
        captured, pre_results=[conv_result, persona_result, last_user_result]
    )

    with (
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "socrates"
        mock_get_persona.return_value = persona_config

        with pytest.raises(_StopAfterHistory):
            await _drain(service.stream_another_mind(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                target_persona_slug="socrates",
                user_plan="pro",
            ))

    _assert_desc(_order_by_clause(captured["sql"]), "stream_another_mind")


@pytest.mark.asyncio
async def test_go_deeper_history_query_orders_desc():
    """stream_go_deeper history query → ORDER BY created_at DESC (newest N)."""
    service = ConversationService()
    captured = {}

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    thread_result = MagicMock(); thread_result.scalar.return_value = 0
    last_std_result = MagicMock(); last_std_result.scalar.return_value = None
    turn_result = MagicMock(); turn_result.scalar.return_value = 0
    last_user_result = MagicMock()
    last_user_result.scalar_one_or_none.return_value = "Say more about virtue."

    db = _capture_history_sql(captured, pre_results=[
        conv_result, persona_result, thread_result,
        last_std_result, turn_result, last_user_result,
    ])

    with (
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        # is_admin=True skips the daily go-deeper gate (no extra execute call).
        with pytest.raises(_StopAfterHistory):
            await _drain(service.stream_go_deeper(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                user_plan="pro",
                is_admin=True,
            ))

    _assert_desc(_order_by_clause(captured["sql"]), "stream_go_deeper")


# ── 2. Behavioural: the LLM receives the most recent window, in order ──────────

def _seeded_history(n: int):
    """n messages with ascending created_at, alternating assistant/user.

    Index 0 is an assistant turn (the persona's opening_invocation), so even
    indices are assistant turns and odd indices are user turns — the real shape of
    a conversation. persona_id=None ⇒ authored by the home persona, so the
    cross-mind labelling branch stays off and content passes through verbatim.
    """
    base = datetime(2026, 1, 1, 12, 0, 0)
    msgs = []
    for i in range(n):
        m = MagicMock()
        m.role = "assistant" if i % 2 == 0 else "user"
        m.content = f"m{i:02d}"
        m.persona_id = None
        m.created_at = base + timedelta(minutes=i)
        msgs.append(m)
    return msgs


def _make_db_seeded_history(all_msgs, window: int):
    """DB mock whose history call behaves like a miniature Postgres: it applies the
    query's REAL ORDER BY direction to the seeded rows, then the window limit.

    This is what makes the test a regression test rather than a restatement of the
    mock — under the old ASC ordering it returns the OLDEST rows and the assertions
    below fail.
    """
    db = AsyncMock()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    default_result = MagicMock()
    default_result.scalar_one_or_none.return_value = None

    call_index = {"n": 0}

    async def execute_side_effect(stmt, *args, **kwargs):
        compiled = _is_history_query(stmt)
        if compiled is not None:
            clause = _order_by_clause(compiled)
            rows = sorted(all_msgs, key=lambda m: m.created_at)
            if "DESC" in clause.upper():
                rows = list(reversed(rows))
            history_result = MagicMock()
            history_result.scalars.return_value.all.return_value = rows[:window]
            return history_result
        n = call_index["n"]
        call_index["n"] += 1
        if n == 0:
            return conv_result
        if n == 1:
            return persona_result
        return default_result

    db.execute = execute_side_effect
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


async def _run_main_path_seeded(n_messages: int, window: int) -> list[dict]:
    """Run stream_response over a seeded n-message conversation and return the
    message list actually handed to llm_client.stream()."""
    service = ConversationService()
    captured = {}

    async def capture_stream(*args, **kwargs):
        captured["messages"] = list(kwargs["messages"])
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    all_msgs = _seeded_history(n_messages)

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        mock_prompt.build_system.return_value = "system"
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        # No length band ⇒ _length_directive_for_input returns None. This test is the
        # first with a populated window, so it is the first to reach that branch
        # (gated on history_len > 1); a bare MagicMock band would unpack-error there
        # for reasons unrelated to ordering.
        persona_config.response_length_words = None
        mock_get_persona.return_value = persona_config

        db = _make_db_seeded_history(all_msgs, window)
        service._save_message = AsyncMock(return_value=_saved_msg())
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="pro",
        ))

    return captured["messages"]


@pytest.mark.asyncio
async def test_main_path_sends_most_recent_window_in_chronological_order():
    """25-message conversation, Pro (window 20) → the LLM gets the LAST 20 messages
    in chronological order, ending with the current user text.

    The regression this pins: m24 — the persona's own most recent turn — must be in
    the context. Under the old ASC ordering the model received m00–m19 and would
    deny having said m24.
    """
    sent = await _run_main_path_seeded(25, MEMORY_WINDOW_PRO)
    contents = [m["content"] for m in sent]

    # Newest 20 rows are m05..m24 (m05 is a user turn, so nothing is stripped by
    # the leading-assistant guard), then the current user text is appended.
    expected = [f"m{i:02d}" for i in range(5, 25)] + ["What is virtue?"]
    assert contents == expected, f"Expected {expected}, got {contents}"

    # The bug, stated directly: the persona's most recent turn is in context…
    assert "m24" in contents
    # …and the oldest turns have fallen out of the window.
    for old in ("m00", "m01", "m02", "m03", "m04"):
        assert old not in contents

    # Anthropic invariant: the array still starts with a user turn and ends on the
    # current user text.
    assert sent[0]["role"] == "user"
    assert sent[-1] == {"role": "user", "content": "What is virtue?"}


@pytest.mark.asyncio
async def test_main_path_strips_leading_assistant_when_window_opens_on_one():
    """26-message conversation, Pro (window 20) → window is m06..m25 and m06 is an
    ASSISTANT turn, so the leading-assistant strip must fire.

    This branch is newly live. Before the fix the window always began at m00 — the
    conversation's first row — so on the main path the strip was effectively dead
    code. Selecting the newest N means the window now opens at an arbitrary point
    mid-conversation and lands on an assistant turn half the time; without the strip
    that is an Anthropic 400 (messages must begin with a user turn) on every long
    conversation.
    """
    sent = await _run_main_path_seeded(26, MEMORY_WINDOW_PRO)
    contents = [m["content"] for m in sent]

    # The strip fired — the API invariant holds even though the window opened on an
    # assistant turn.
    assert sent[0]["role"] == "user"

    # Exactly one row stripped: m06 is gone, m07 onward survive intact.
    expected = [f"m{i:02d}" for i in range(7, 26)] + ["What is virtue?"]
    assert contents == expected, f"Expected {expected}, got {contents}"

    # The newest turn is still in context (m25; the persona's own most recent turn,
    # m24, rides along with it) — the strip trims the front, never the tail.
    assert "m25" in contents


# ── 3. Prompt cache: the message-history breakpoint ───────────────────────────
#
# A chat request carries TWO cache breakpoints (Anthropic permits 4):
#   1. the system prefix — prompt_builder.split_system_for_cache, unchanged
#   2. the message history — the top-level automatic breakpoint, added here
#
# (2) is attached ONLY while nothing has been dropped from the history, because a
# prefix that loses its oldest rows changes every turn: the lookup would be a
# guaranteed miss billed at the 1.25x write price. Under the phase-2 growing
# window that condition is the token budget's `truncated` flag, not a message
# count. See _history_cache_control and _fit_history_to_budget.

from services.conversation_service import (
    _history_cache_control, _fit_history_to_budget, _estimate_tokens,
)
from services.prompt_builder import prompt_builder as _real_prompt_builder
from services.prompt_builder import CACHE_SPLIT_SENTINEL as _SENTINEL

_EPHEMERAL = {"type": "ephemeral"}


def _use_real_cache_split(mock_prompt):
    """Point a patched prompt_builder's split at the REAL implementation, over a
    rendered system that carries the sentinel. Lets a test assert that the
    system-prefix breakpoint still ships alongside the new history breakpoint."""
    mock_prompt.build_system.return_value = f"PREFIX{_SENTINEL}SUFFIX"
    mock_prompt.split_system_for_cache = _real_prompt_builder.split_system_for_cache


def _assert_system_prefix_breakpoint_intact(system):
    """The pre-existing system split is untouched: 2 blocks, cache_control on the
    first only, suffix starting at the sentinel's position."""
    assert isinstance(system, list) and len(system) == 2, (
        f"system must still be the 2-block cache split, got: {system!r}"
    )
    assert system[0]["text"] == "PREFIX"
    assert system[0]["cache_control"] == _EPHEMERAL
    assert "cache_control" not in system[1]
    assert system[1]["text"].startswith("SUFFIX")


async def _run_main_path_capture(n_messages: int, window: int, user_plan: str,
                                 budget: int | None = None) -> dict:
    """Run stream_response over a seeded conversation and return the FULL kwargs
    handed to llm_client.stream() — system, messages, model, cache_control.

    `budget` patches HISTORY_TOKEN_BUDGET_PRO so a test can force the token
    trimmer to bite without seeding megabytes of text."""
    service = ConversationService()
    captured = {}

    async def capture_stream(*args, **kwargs):
        captured.update(kwargs)
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    all_msgs = _seeded_history(n_messages)

    with (
        patch("services.conversation_service.safety_service") as mock_safety,
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.analytics_service"),
        patch("services.conversation_service.POSTPROCESSING_ENABLED", False),
        patch("services.conversation_service.PHENOMENOLOGY_BRIDGE_ENABLED", False),
        patch("services.conversation_service.get_persona") as mock_get_persona,
        patch("services.conversation_service.HISTORY_TOKEN_BUDGET_PRO",
              budget if budget is not None else HISTORY_TOKEN_BUDGET_PRO),
    ):
        safety_result = MagicMock()
        safety_result.should_log = False
        safety_result.should_suppress_persona = False
        safety_result.level = "none"
        mock_safety.check_input = AsyncMock(return_value=safety_result)
        mock_safety.check_output = AsyncMock(return_value=safety_result)
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        _use_real_cache_split(mock_prompt)
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        persona_config.response_length_words = None
        mock_get_persona.return_value = persona_config

        db = _make_db_seeded_history(all_msgs, window)
        service._save_message = AsyncMock(return_value=_saved_msg())
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan=user_plan,
        ))

    return captured


def _make_db_go_deeper_history(all_msgs, window: int):
    """DB mock for stream_go_deeper: serves the limit-enforcement scalars in call
    order, then behaves like _make_db_seeded_history for the history query."""
    db = AsyncMock()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()
    thread_result = MagicMock(); thread_result.scalar.return_value = 0
    last_std_result = MagicMock(); last_std_result.scalar.return_value = None
    turn_result = MagicMock(); turn_result.scalar.return_value = 0
    last_user_result = MagicMock()
    last_user_result.scalar_one_or_none.return_value = "m01"
    default_result = MagicMock()
    default_result.scalar_one_or_none.return_value = None

    ordered = [conv_result, persona_result, thread_result,
               last_std_result, turn_result, last_user_result]
    call_index = {"n": 0}

    async def execute_side_effect(stmt, *args, **kwargs):
        compiled = _is_history_query(stmt)
        if compiled is not None:
            rows = sorted(all_msgs, key=lambda m: m.created_at)
            if "DESC" in _order_by_clause(compiled).upper():
                rows = list(reversed(rows))
            history_result = MagicMock()
            history_result.scalars.return_value.all.return_value = rows[:window]
            return history_result
        n = call_index["n"]
        call_index["n"] += 1
        return ordered[n] if n < len(ordered) else default_result

    db.execute = execute_side_effect
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


async def _run_guest_path_capture(which: str, n_messages: int, window: int,
                                  user_plan: str, budget: int | None = None) -> dict:
    """Run stream_another_mind / stream_go_deeper over a seeded conversation and
    return the FULL kwargs handed to llm_client.stream().

    The seeded history is authored by the home persona and the responder resolves
    to the same persona, so the foreign-turn relabelling branch stays off — this
    test is about the cache breakpoint, not about labelling."""
    service = ConversationService()
    captured = {}

    async def capture_stream(*args, **kwargs):
        captured.update(kwargs)
        yield "Hello"

    mock_llm = MagicMock()
    mock_llm.stream = capture_stream

    all_msgs = _seeded_history(n_messages)

    with (
        patch("services.conversation_service.memory_service") as mock_memory,
        patch("services.conversation_service.retrieval_service") as mock_retrieval,
        patch("services.conversation_service.llm_client", mock_llm),
        patch("services.conversation_service.prompt_builder") as mock_prompt,
        patch("services.conversation_service.get_persona") as mock_get_persona,
        patch("services.conversation_service.HISTORY_TOKEN_BUDGET_PRO",
              budget if budget is not None else HISTORY_TOKEN_BUDGET_PRO),
    ):
        mock_memory.recall = AsyncMock(return_value=[])
        mock_retrieval.retrieve = AsyncMock(return_value=[])
        _use_real_cache_split(mock_prompt)
        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        # Both guest paths JSON-dump slug + name in their 'start' event, so name
        # must be a real string (a bare MagicMock is not JSON serialisable).
        persona_config.name = "Marcus Aurelius"
        mock_get_persona.return_value = persona_config
        service._save_message = AsyncMock(return_value=_saved_msg())

        if which == "another_mind":
            db = _make_db_seeded_history(all_msgs, window)
            await _drain(service.stream_another_mind(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                target_persona_slug="socrates",
                user_plan=user_plan,
            ))
        else:
            db = _make_db_go_deeper_history(all_msgs, window)
            await _drain(service.stream_go_deeper(
                db=db,
                conversation_id=CONV_ID,
                user_id=USER_ID,
                user_plan=user_plan,
                is_admin=True,  # skips the daily gate (no extra execute call)
            ))

    return captured


# ── The guard itself ──────────────────────────────────────────────────────────

def test_history_cache_control_attaches_only_when_nothing_was_dropped():
    """Pro + nothing dropped ⇒ breakpoint. Truncated ⇒ None, because a prefix that
    loses its oldest rows can only ever MISS, and a miss is billed as a write.

    Phase 1 expressed this as `history_len >= MEMORY_WINDOW_PRO`, which was correct
    only while the window was a fixed 20. Under the growing window that test would
    INVERT — withholding the breakpoint from precisely the prefix-stable
    conversations phase 2 creates. The condition is "did we drop anything".
    """
    assert _history_cache_control("pro", False) == _EPHEMERAL
    assert _history_cache_control("premium", False) == _EPHEMERAL
    assert _history_cache_control("pro", True) is None
    assert _history_cache_control("premium", True) is None


def test_history_cache_control_is_pro_only():
    """FREE is Haiku 4.5 (4,096-token cache minimum ≈ the whole free prompt) —
    gated off so behaviour is deterministic rather than length-dependent."""
    assert _history_cache_control("free", False) is None
    assert _history_cache_control("free", True) is None


# ── Main path ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_main_path_sends_history_breakpoint_when_nothing_evicted():
    """6-message conversation, Pro (window 20) → the history breakpoint ships,
    and the system-prefix breakpoint is still there. Two breakpoints total."""
    sent = await _run_main_path_capture(6, MEMORY_WINDOW_PRO, "pro")

    assert sent["cache_control"] == _EPHEMERAL
    _assert_system_prefix_breakpoint_intact(sent["system"])

    # Anthropic permits 4 per request; this path uses 2.
    breakpoints = sum(1 for b in sent["system"] if "cache_control" in b) + 1
    assert breakpoints == 2, f"expected 2 cache breakpoints, got {breakpoints}"


@pytest.mark.asyncio
async def test_main_path_omits_history_breakpoint_when_budget_truncates():
    """Budget too small for the conversation → the oldest rows are dropped, so the
    message prefix changes every turn. No history breakpoint: marking it would buy
    a guaranteed cache MISS at 1.25x write price. The system prefix — which does
    NOT slide — keeps its breakpoint.

    Eviction is now a TOKEN-budget event, not a message-count one: under the
    growing window a 25-message conversation is carried in full."""
    sent = await _run_main_path_capture(25, MEMORY_MAX_ROWS_PRO, "pro", budget=4)

    assert sent["cache_control"] is None
    _assert_system_prefix_breakpoint_intact(sent["system"])


@pytest.mark.asyncio
async def test_main_path_carries_whole_conversation_under_budget():
    """THE PHASE-2 CHANGE: a 60-message conversation reaches the LLM in full, where
    the old sliding window would have shown 20. The breakpoint ships because the
    prefix is append-only."""
    sent = await _run_main_path_capture(60, MEMORY_MAX_ROWS_PRO, "pro")
    contents = [m["content"] for m in sent["messages"]]

    # m00 is an assistant turn and is stripped by the leading-assistant guard;
    # m01..m59 survive, then the current user text is appended.
    assert contents == [f"m{i:02d}" for i in range(1, 60)] + ["What is virtue?"]
    assert sent["cache_control"] == _EPHEMERAL


@pytest.mark.asyncio
async def test_main_path_budget_drops_oldest_first_and_keeps_newest():
    """At the ceiling the trim is oldest-first: the newest turns survive, the
    oldest fall away, and the array still opens on a user turn."""
    sent = await _run_main_path_capture(25, MEMORY_MAX_ROWS_PRO, "pro", budget=12)
    contents = [m["content"] for m in sent["messages"]]

    assert contents[-1] == "What is virtue?"
    assert "m24" in contents, "the newest history turn must survive the trim"
    assert "m00" not in contents, "the oldest turns must be the ones dropped"
    assert sent["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_main_path_free_plan_sends_no_history_breakpoint():
    """3-message conversation on FREE — nothing evicted, but free is gated off."""
    sent = await _run_main_path_capture(3, MEMORY_WINDOW_FREE, "free")

    assert sent["cache_control"] is None
    assert sent["model"] == MODEL_FREE
    _assert_system_prefix_breakpoint_intact(sent["system"])


# ── Guest paths ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_another_mind_sends_history_breakpoint_when_nothing_evicted():
    """stream_another_mind carries the same two breakpoints."""
    sent = await _run_guest_path_capture("another_mind", 6, MEMORY_WINDOW_PRO, "pro")

    assert sent["cache_control"] == _EPHEMERAL
    _assert_system_prefix_breakpoint_intact(sent["system"])


@pytest.mark.asyncio
async def test_another_mind_omits_history_breakpoint_when_budget_truncates():
    sent = await _run_guest_path_capture(
        "another_mind", 25, MEMORY_MAX_ROWS_PRO, "pro", budget=4
    )

    assert sent["cache_control"] is None
    _assert_system_prefix_breakpoint_intact(sent["system"])


@pytest.mark.asyncio
async def test_go_deeper_sends_history_breakpoint_when_nothing_evicted():
    """stream_go_deeper carries the same two breakpoints."""
    sent = await _run_guest_path_capture("go_deeper", 6, MEMORY_WINDOW_PRO, "pro")

    assert sent["cache_control"] == _EPHEMERAL
    _assert_system_prefix_breakpoint_intact(sent["system"])


@pytest.mark.asyncio
async def test_go_deeper_omits_history_breakpoint_when_budget_truncates():
    sent = await _run_guest_path_capture(
        "go_deeper", 25, MEMORY_MAX_ROWS_PRO, "pro", budget=4
    )

    assert sent["cache_control"] is None
    _assert_system_prefix_breakpoint_intact(sent["system"])


# ── The trimmer and the estimator ─────────────────────────────────────────────

def _msg(content: str):
    m = MagicMock()
    m.content = content
    return m


def test_fit_history_under_budget_keeps_everything_untruncated():
    """Under budget ⇒ the whole conversation, and truncated is False so the cache
    breakpoint ships."""
    history = [_msg(f"message number {i}") for i in range(30)]
    kept, truncated = _fit_history_to_budget(history, "pro")

    assert kept == history
    assert truncated is False


def test_fit_history_over_budget_drops_oldest_first():
    """Over budget ⇒ oldest dropped, newest kept, truncated True."""
    history = [_msg(f"message number {i}") for i in range(30)]
    with patch("services.conversation_service.HISTORY_TOKEN_BUDGET_PRO", 20):
        kept, truncated = _fit_history_to_budget(history, "pro")

    assert truncated is True
    assert 0 < len(kept) < len(history)
    assert kept[-1] is history[-1], "the newest turn must always survive"
    assert kept == history[len(history) - len(kept):], "kept must be a newest-N suffix"


def test_fit_history_always_keeps_the_newest_message():
    """A single message larger than the entire budget is still sent — an empty
    history would break the API's user-first invariant."""
    history = [_msg("x" * 400), _msg("y" * 4000)]
    with patch("services.conversation_service.HISTORY_TOKEN_BUDGET_PRO", 1):
        kept, truncated = _fit_history_to_budget(history, "pro")

    assert len(kept) == 1
    assert kept[0] is history[-1]
    assert truncated is True


def test_fit_history_leaves_free_untouched():
    """FREE is never budget-managed: its 5-message sliding window is the LIMIT's
    job, and it must behave exactly as before in every respect."""
    history = [_msg("x" * 5000) for _ in range(5)]
    with patch("services.conversation_service.HISTORY_TOKEN_BUDGET_PRO", 1):
        kept, truncated = _fit_history_to_budget(history, "free")

    assert kept == history
    assert truncated is False


def test_estimate_tokens_does_not_underestimate_greek():
    """The reason chars/4 was rejected: Greek runs ~5.3 tokens/word, where chars/4
    predicts ~1.3 — a 3.5x under-estimate that would let a Greek conversation carry
    3.5x the intended budget."""
    greek = ("Συνέχεια λέω στον εαυτό μου ότι θα ξεκινήσω μόλις ηρεμήσουν τα "
             "πράγματα στη δουλειά, αλλά ποτέ δεν ηρεμούν.")

    assert _estimate_tokens(greek) > 2 * (len(greek) // 4)
    assert _estimate_tokens("") == 0


def test_estimate_tokens_fallback_when_tiktoken_unavailable():
    """No tiktoken ⇒ the fallback still tracks script weight and errs HIGH (smaller
    window) rather than low (budget overrun)."""
    greek = "Συνέχεια λέω στον εαυτό μου"
    english = "I keep telling myself"

    with patch("services.conversation_service._get_encoder", return_value=None):
        assert _estimate_tokens(greek) > _estimate_tokens(english)
        # ASCII path: ~4 chars/token.
        assert _estimate_tokens("a" * 400) == 100
