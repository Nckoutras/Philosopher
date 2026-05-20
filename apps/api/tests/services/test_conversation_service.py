"""Tests for tier-aware model selection and memory window in conversation_service.

Verifies that stream_response() selects the correct Anthropic model and
history window based on user_plan. All external I/O is mocked.

Run: cd apps/api && pytest tests/services/test_conversation_service.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from services.conversation_service import ConversationService
from services.conversation_service import MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO


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
            db=db,
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
            db=db,
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
            db=db,
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
            db=db,
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
