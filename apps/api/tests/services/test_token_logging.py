"""Tests that Anthropic token usage reaches messages.tokens_used.

The column has existed since migration 001 and was NULL on every row: the LLM
client read usage off the final stream message, logged it, and dropped it.
These tests pin the whole path — stream() sink -> _save_message -> Message.

Run: cd apps/api && pytest tests/services/test_token_logging.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.conversation_service import ConversationService

USER_ID = "user-uuid-1"
CONV_ID = "conv-uuid-1"
PERSONA_ID = "persona-uuid-1"


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
    """Mock AsyncSession. First three execute() calls are conversation, persona
    and history; everything after that is a throwaway result, so this does not
    have to track the exact number of metadata updates."""
    db = AsyncMock()

    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = _mock_conv()

    persona_result = MagicMock()
    persona_result.scalar_one.return_value = _mock_persona_db()

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = []

    ordered = [conv_result, persona_result, history_result]

    async def _execute(*args, **kwargs):
        return ordered.pop(0) if ordered else MagicMock()

    db.execute = AsyncMock(side_effect=_execute)
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


async def _drain(gen):
    return [item async for item in gen]


def _fake_stream_reporting(total):
    """Stand-in for llm_client.stream that yields one chunk and reports `total`
    tokens through the sink, the way the real client now does."""
    async def fake_stream(*args, _token_sink=None, **kwargs):
        yield "Hello"
        if _token_sink is not None:
            _token_sink["total"] = _token_sink.get("total", 0) + total
    return fake_stream


async def _run(total=42):
    """Drive stream_response with a stream that reports `total` tokens.

    Returns the mock db so callers can inspect the Message objects handed to
    db.add(). _save_message is left REAL so the assertion covers the actual
    Message constructor, not a mock's call args.
    """
    service = ConversationService()

    mock_llm = AsyncMock()
    mock_llm.stream = _fake_stream_reporting(total)

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

        persona_config = MagicMock()
        persona_config.slug = "marcus_aurelius"
        mock_get_persona.return_value = persona_config

        db = _make_db()
        service._log_safety_event = AsyncMock()

        await _drain(service.stream_response(
            session_factory=_factory(db),
            conversation_id=CONV_ID,
            user_id=USER_ID,
            user_text="What is virtue?",
            user_plan="pro",
        ))

    return db


def _added_messages(db):
    return [c.args[0] for c in db.add.call_args_list]


@pytest.mark.asyncio
async def test_assistant_message_records_token_count():
    """The count reported by stream() lands on the persisted assistant row."""
    db = await _run(total=42)

    assistant = [m for m in _added_messages(db) if m.role == "assistant"]
    assert len(assistant) == 1, "expected exactly one assistant message"
    assert assistant[0].tokens_used == 42


@pytest.mark.asyncio
async def test_user_message_records_no_token_count():
    """User messages cost nothing to generate and must stay NULL."""
    db = await _run(total=42)

    user_msgs = [m for m in _added_messages(db) if m.role == "user"]
    assert len(user_msgs) == 1, "expected exactly one user message"
    assert user_msgs[0].tokens_used is None


@pytest.mark.asyncio
async def test_missing_usage_leaves_column_null_not_zero():
    """If the usage read fails the sink stays empty. NULL means 'unknown';
    0 would be a false claim that the call was free."""
    db = await _run(total=0)

    assistant = [m for m in _added_messages(db) if m.role == "assistant"]
    assert assistant[0].tokens_used is None


@pytest.mark.asyncio
async def test_save_message_defaults_to_null():
    """Every pre-existing call site omits tokens_used and must be unaffected."""
    service = ConversationService()
    db = _make_db()

    msg = await service._save_message(db, _mock_conv(), USER_ID, "assistant", "hi")

    assert msg.tokens_used is None


# ── The real llm_client.stream(), against a mocked Anthropic client ──────────

def _mock_anthropic(input_tokens=10, cache_creation=3, cache_read=5, output_tokens=20):
    """Minimal stand-in for anthropic.AsyncAnthropic supporting the async
    context-manager + text_stream + get_final_message shape stream() uses.

    All four usage fields are set explicitly. A MagicMock would happily
    auto-create a missing one and return a MagicMock from the getattr, which
    turns the sum into a MagicMock instead of raising — so a dropped field
    would pass silently rather than fail. Setting them makes the arithmetic
    real."""
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
async def test_real_stream_counts_every_billed_component():
    """input + cache_creation + cache_read + output all reach the sink."""
    from services.llm_client import LLMClient

    sink: dict = {}
    with patch("services.llm_client._client", _mock_anthropic(10, 3, 5, 20)):
        async for _ in LLMClient().stream(
            system="s", messages=[], _token_sink=sink
        ):
            pass

    assert sink["total"] == 38


@pytest.mark.asyncio
async def test_real_stream_does_not_drop_cache_tokens():
    """Regression guard for the amendment. History caching makes cache_read the
    dominant input component on deep conversations, so counting only
    input+output would make the most expensive conversations record the
    smallest numbers — the exact failure this column exists to avoid."""
    from services.llm_client import LLMClient

    sink: dict = {}
    with patch("services.llm_client._client", _mock_anthropic(10, 300, 5000, 20)):
        async for _ in LLMClient().stream(
            system="s", messages=[], _token_sink=sink
        ):
            pass

    assert sink["total"] == 5330, "cache_read/cache_creation must be counted"
    assert sink["total"] != 30, "input+output only — cache tokens were dropped"


@pytest.mark.asyncio
async def test_real_stream_accumulates_into_one_sink():
    """One sink shared by the main stream and the correction regeneration must
    total both, not keep only the last. This is what makes a corrected reply
    record the tokens it actually cost."""
    from services.llm_client import LLMClient

    sink: dict = {}
    client = LLMClient()
    for _ in range(2):
        with patch("services.llm_client._client", _mock_anthropic(10, 3, 5, 20)):
            async for _ in client.stream(system="s", messages=[], _token_sink=sink):
                pass

    assert sink["total"] == 76


@pytest.mark.asyncio
async def test_real_stream_without_sink_still_streams():
    """Every existing caller omits _token_sink and must be unaffected."""
    from services.llm_client import LLMClient

    with patch("services.llm_client._client", _mock_anthropic()):
        chunks = [c async for c in LLMClient().stream(system="s", messages=[])]

    assert chunks == ["chunk"]
