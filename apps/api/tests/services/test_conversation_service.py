"""Tests for tier-aware model selection and memory window in conversation_service.

Verifies that stream_response() selects the correct Anthropic model and
history window based on user_plan. All external I/O is mocked.

Run: cd apps/api && pytest tests/services/test_conversation_service.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from services.conversation_service import ConversationService
from services.llm_service import MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO


# ── Shared fixtures ───────────────────────────────────────────────────────────

USER_ID = "user-uuid-1"
CONV_ID = "conv-uuid-1"
PERSONA_ID = "persona-uuid-1"


def _mock_conv():
    c = MagicMock()
    c.id = CONV_ID
    c.persona_id = PERSONA_ID
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
            db=db,
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
            db=db,
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
            db=db,
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
            db=db,
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="premium",
        ))

    assert called_with.get("model") == MODEL_PRO, (
        f"Expected model={MODEL_PRO!r}, got {called_with.get('model')!r}"
    )


# ── Section B: History window ─────────────────────────────────────────────────

def _make_db_capture_limit(captured: dict, *, history=None):
    """DB mock that records the .limit() argument used in the history query.

    The history query is the third execute() call in stream_response.
    We intercept the SQLAlchemy Select object passed to execute() on that
    call and record the limit value.
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
        if n == 2:
            # History query — capture the limit
            compiled = stmt.compile(compile_kwargs={"literal_binds": True})
            captured["limit_clause"] = str(compiled)
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
            db=db,
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
async def test_pro_user_history_window_is_20():
    """Pro user → history query uses LIMIT 20 (MEMORY_WINDOW_PRO)."""
    captured = await _run_stream_capture_limit("pro")
    assert str(MEMORY_WINDOW_PRO) in captured.get("limit_clause", ""), (
        f"Expected LIMIT {MEMORY_WINDOW_PRO} in query, got: {captured.get('limit_clause')}"
    )


@pytest.mark.asyncio
async def test_premium_user_history_window_is_20():
    """Premium user is treated as pro → history query uses LIMIT 20."""
    captured = await _run_stream_capture_limit("premium")
    assert str(MEMORY_WINDOW_PRO) in captured.get("limit_clause", ""), (
        f"Expected LIMIT {MEMORY_WINDOW_PRO} in query, got: {captured.get('limit_clause')}"
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
            db=db,
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
