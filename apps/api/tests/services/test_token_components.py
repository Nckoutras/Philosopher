"""Tests that the four usage buckets are stored separately (migration 054).

messages.tokens_used is the SUM of the four Anthropic usage fields. The buckets
are disjoint, so the sum is the true prompt+output volume — but they price
differently (input 1.0x, cache_creation 1.25x, cache_read 0.1x), so equal
tokens_used can mean ~10x different spend. These tests pin the components
reaching the row, and the identity that makes a fourth column unnecessary.

Run: cd apps/api && pytest tests/services/test_token_components.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.conversation_service import ConversationService

USER_ID = "user-uuid-1"
CONV_ID = "conv-uuid-1"
PERSONA_ID = "persona-uuid-1"

# Deliberately distinct values: if the write path ever crosses two components,
# equal numbers would hide it.
INPUT_T, CACHE_WR, CACHE_RD, OUTPUT_T = 11, 300, 5000, 27
TOTAL_T = INPUT_T + CACHE_WR + CACHE_RD + OUTPUT_T  # 5338


def _mock_conv():
    c = MagicMock()
    c.id = CONV_ID
    c.persona_id = PERSONA_ID
    c.active_persona_id = None
    c.deep_mode = False
    return c


def _mock_persona_db():
    p = MagicMock()
    p.id = PERSONA_ID
    p.slug = "marcus_aurelius"
    return p


def _make_db():
    """Shape-dispatched session mock (TD-45 pattern): results are chosen by which
    table the statement hits, never by call index, so an inserted query cannot
    shift anything."""
    db = AsyncMock()

    def _generic():
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        r.scalars.return_value.all.return_value = []
        return r

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()
    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    async def execute(stmt, *args, **kwargs):
        try:
            sql = " ".join(str(stmt.compile(compile_kwargs={"literal_binds": True})).split()).upper()
        except Exception:
            return _generic()
        if sql.startswith("SELECT") and "FROM CONVERSATIONS" in sql:
            return conv_result
        if sql.startswith("SELECT") and "FROM PERSONAS" in sql:
            return persona_result
        return _generic()

    db.execute = AsyncMock(side_effect=execute)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _factory(db):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _fake_stream(components):
    """Stand-in for llm_client.stream that fills the sink the way the real client
    now does. `components` of None simulates a failed usage read: the sink stays
    untouched, exactly as the guarded except path leaves it."""
    async def fake_stream(*args, _token_sink=None, **kwargs):
        yield "Hello"
        if _token_sink is not None and components is not None:
            i, w, r, o = components
            _token_sink["total"] = _token_sink.get("total", 0) + i + w + r + o
            _token_sink["input"] = _token_sink.get("input", 0) + i
            _token_sink["cache_creation"] = _token_sink.get("cache_creation", 0) + w
            _token_sink["cache_read"] = _token_sink.get("cache_read", 0) + r
    return fake_stream


async def _run(components=(INPUT_T, CACHE_WR, CACHE_RD, OUTPUT_T)):
    """Drive stream_response with _save_message REAL, so assertions cover the
    actual Message constructor rather than a mock's call args."""
    service = ConversationService()

    mock_llm = AsyncMock()
    mock_llm.stream = _fake_stream(components)

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
        mock_prompt.build_safety_response.return_value = "safe"
        mock_get_persona.return_value = MagicMock(slug="marcus_aurelius")

        db = _make_db()
        service._log_safety_event = AsyncMock()

        async for _ in service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="pro",
        ):
            pass

    return db


def _assistant(db):
    msgs = [c.args[0] for c in db.add.call_args_list if getattr(c.args[0], "role", None) == "assistant"]
    assert len(msgs) == 1, f"expected one assistant message, got {len(msgs)}"
    return msgs[0]


@pytest.mark.asyncio
async def test_components_are_written_on_a_successful_stream():
    """The load-bearing case: all three components reach the persisted row."""
    msg = _assistant(await _run())

    assert msg.input_tokens == INPUT_T
    assert msg.cache_creation_tokens == CACHE_WR
    assert msg.cache_read_tokens == CACHE_RD
    assert msg.tokens_used == TOTAL_T


@pytest.mark.asyncio
async def test_output_tokens_is_derivable_so_no_fourth_column_is_needed():
    """The identity the no-fourth-column decision rests on:

        output = tokens_used - (input + cache_creation + cache_read)
    """
    msg = _assistant(await _run())

    derived = msg.tokens_used - (
        msg.input_tokens + msg.cache_creation_tokens + msg.cache_read_tokens
    )
    assert derived == OUTPUT_T


@pytest.mark.asyncio
async def test_components_are_null_when_the_usage_read_fails():
    """The guarded except path leaves the sink empty. NULL means 'not measured';
    writing 0 would claim the call was free."""
    msg = _assistant(await _run(components=None))

    assert msg.tokens_used is None
    assert msg.input_tokens is None
    assert msg.cache_creation_tokens is None
    assert msg.cache_read_tokens is None


@pytest.mark.asyncio
async def test_zero_cache_read_is_stored_as_zero_not_null():
    """An uncached request genuinely reads 0 cache tokens. That is a measurement,
    not an absence, and `or None` would flatten the two together — which is why
    the components use a plain .get() while tokens_used keeps `or None`."""
    msg = _assistant(await _run(components=(3000, 0, 0, 40)))

    assert msg.cache_read_tokens == 0, "a real zero was flattened to NULL"
    assert msg.cache_creation_tokens == 0
    assert msg.input_tokens == 3000
    assert msg.tokens_used == 3040


@pytest.mark.asyncio
async def test_existing_save_message_callers_are_unaffected():
    """Every pre-054 call site omits the three params and must still write NULL."""
    service = ConversationService()
    msg = await service._save_message(_make_db(), _mock_conv(), USER_ID, "assistant", "hi")

    assert msg.input_tokens is None
    assert msg.cache_creation_tokens is None
    assert msg.cache_read_tokens is None


# ── The real llm_client.stream(), against a mocked Anthropic client ──────────

def _mock_anthropic(input_tokens=INPUT_T, cache_creation=CACHE_WR,
                    cache_read=CACHE_RD, output_tokens=OUTPUT_T):
    """All four usage fields set explicitly: a bare MagicMock would auto-create a
    missing one and make the arithmetic a MagicMock instead of raising, so a
    dropped field would pass silently."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.cache_creation_input_tokens = cache_creation
    usage.cache_read_input_tokens = cache_read
    usage.output_tokens = output_tokens

    final = MagicMock()
    final.usage = usage

    async def _text_stream():
        yield "chunk"

    handle = MagicMock()
    handle.text_stream = _text_stream()
    handle.get_final_message = AsyncMock(return_value=final)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=handle)
    cm.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.messages.stream = MagicMock(return_value=cm)
    return client


@pytest.mark.asyncio
async def test_real_stream_fills_all_four_sink_keys():
    """stream() itself must populate the components, not just the total."""
    from services.llm_client import LLMClient

    sink: dict = {}
    with patch("services.llm_client._client", _mock_anthropic()):
        async for _ in LLMClient().stream(system="s", messages=[], _token_sink=sink):
            pass

    assert sink == {
        "total": TOTAL_T,
        "input": INPUT_T,
        "cache_creation": CACHE_WR,
        "cache_read": CACHE_RD,
    }


@pytest.mark.asyncio
async def test_every_sink_key_accumulates_in_lockstep():
    """Two calls on one sink — the correction-regeneration case. The components
    must accumulate with the total, or the output identity breaks on any message
    that spans more than one call."""
    from services.llm_client import LLMClient

    sink: dict = {}
    client = LLMClient()
    for _ in range(2):
        with patch("services.llm_client._client", _mock_anthropic()):
            async for _ in client.stream(system="s", messages=[], _token_sink=sink):
                pass

    assert sink["total"] == 2 * TOTAL_T
    assert sink["input"] == 2 * INPUT_T
    assert sink["cache_creation"] == 2 * CACHE_WR
    assert sink["cache_read"] == 2 * CACHE_RD
    # The identity survives accumulation — this is what removes the need for a
    # stored output_tokens column.
    derived = sink["total"] - (sink["input"] + sink["cache_creation"] + sink["cache_read"])
    assert derived == 2 * OUTPUT_T
