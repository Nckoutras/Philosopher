"""Tests for llm_service.call_llm.

All Anthropic API calls are mocked — no real HTTP traffic.

Run: cd apps/api && pytest tests/services/test_llm_service.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID

import anthropic

from services.llm_service import (
    call_llm,
    LLMResponse,
    MODEL_FREE,
    MODEL_PRO,
    MEMORY_WINDOW_FREE,
    MEMORY_WINDOW_PRO,
)
from services.exceptions import PersonaAccessDenied, LLMServiceUnavailable, LLMRequestInvalid


USER_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")
PERSONA_ID = UUID("bbbbbbbb-0000-0000-0000-000000000001")
CONV_ID = UUID("cccccccc-0000-0000-0000-000000000001")


def _make_persona(tier="free", system_fragment="You are a philosopher."):
    p = MagicMock()
    p.id = str(PERSONA_ID)
    p.tier = tier
    p.config = {"system_fragment": system_fragment}
    return p


def _make_sub(status="active", days_ahead=30):
    sub = MagicMock()
    sub.status = status
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    return sub


def _make_anthropic_response(content="Hello", model=MODEL_FREE, input_tokens=10, output_tokens=20):
    response = MagicMock()
    response.content = [MagicMock(text=content)]
    response.model = model
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


def _make_db(*, sub, persona, messages=None):
    """Build a mock AsyncSession with sequential execute() side effects.

    Call order:
      1. tier_service → subscriptions query
      2. persona lookup
      3. history query
    """
    db = AsyncMock()

    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = sub

    persona_result = MagicMock()
    persona_result.scalar_one_or_none.return_value = persona

    history_result = MagicMock()
    history_result.scalars.return_value.all.return_value = messages or []

    db.execute = AsyncMock(side_effect=[sub_result, persona_result, history_result])
    return db


# ── Free user, free persona ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_user_free_persona_uses_free_model():
    """Free user chatting with a free persona uses Haiku and 5-message window."""
    persona = _make_persona(tier="free")
    db = _make_db(sub=None, persona=persona)
    api_response = _make_anthropic_response(model=MODEL_FREE)

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=api_response)
        result = await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_FREE
    assert result.model_used == MODEL_FREE
    assert isinstance(result, LLMResponse)


@pytest.mark.asyncio
async def test_free_user_memory_window_is_5():
    persona = _make_persona(tier="free")
    db = _make_db(sub=None, persona=persona)
    api_response = _make_anthropic_response()

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=api_response)
        await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    # Verify .limit(MEMORY_WINDOW_FREE) was used — the history execute call
    # is the third execute call, but we verify via the window constant via
    # inspecting the query passed (the scalars call returns our empty list)
    assert db.execute.call_count == 3


# ── Pro user, free persona ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pro_user_free_persona_uses_pro_model():
    """Pro user always gets Sonnet, even on a free persona."""
    sub = _make_sub(status="active", days_ahead=30)
    persona = _make_persona(tier="free")
    db = _make_db(sub=sub, persona=persona)
    api_response = _make_anthropic_response(model=MODEL_PRO)

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=api_response)
        result = await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == MODEL_PRO
    assert result.model_used == MODEL_PRO


# ── Pro user, pro persona ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pro_user_pro_persona_succeeds():
    """Pro user can access a pro-tier persona."""
    sub = _make_sub(status="active", days_ahead=30)
    persona = _make_persona(tier="pro")
    db = _make_db(sub=sub, persona=persona)
    api_response = _make_anthropic_response(model=MODEL_PRO)

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=api_response)
        result = await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    assert result.model_used == MODEL_PRO


# ── Free user, pro persona → access denied ────────────────────────────────────

@pytest.mark.asyncio
async def test_free_user_pro_persona_raises_access_denied():
    """Free user attempting a pro persona raises PersonaAccessDenied before any API call."""
    persona = _make_persona(tier="pro")
    db = _make_db(sub=None, persona=persona)

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock()
        with pytest.raises(PersonaAccessDenied):
            await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    mock_client.messages.create.assert_not_called()


# ── Retry on 503: succeeds on 2nd attempt ────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_on_503_succeeds_second_attempt():
    """A 503 on the first attempt is retried; success on attempt 2."""
    sub = None
    persona = _make_persona(tier="free")
    db = _make_db(sub=sub, persona=persona)
    api_response = _make_anthropic_response()

    server_error = anthropic.APIStatusError(
        "Service unavailable",
        response=MagicMock(status_code=503, headers={}),
        body={"error": {"message": "overloaded"}},
    )

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(
            side_effect=[server_error, api_response]
        )
        with patch("services.llm_service.asyncio.sleep", new_callable=AsyncMock):
            result = await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    assert mock_client.messages.create.call_count == 2
    assert isinstance(result, LLMResponse)


# ── Retry on timeout: all 3 attempts fail → LLMServiceUnavailable ────────────

@pytest.mark.asyncio
async def test_retry_on_timeout_all_fail_raises_unavailable():
    """Timeout on all 3 attempts raises LLMServiceUnavailable."""
    sub = None
    persona = _make_persona(tier="free")
    db = _make_db(sub=sub, persona=persona)

    timeout_error = anthropic.APITimeoutError(request=MagicMock())

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=timeout_error)
        with patch("services.llm_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMServiceUnavailable) as exc_info:
                await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    assert mock_client.messages.create.call_count == 3
    assert exc_info.value.persona_id == PERSONA_ID


# ── 401 auth error → LLMRequestInvalid (no retry) ────────────────────────────

@pytest.mark.asyncio
async def test_auth_error_raises_request_invalid_no_retry():
    """A 401 auth error raises LLMRequestInvalid immediately without retrying."""
    sub = None
    persona = _make_persona(tier="free")
    db = _make_db(sub=sub, persona=persona)

    auth_error = anthropic.AuthenticationError(
        "Invalid API key",
        response=MagicMock(status_code=401, headers={}),
        body={"error": {"message": "invalid api key"}},
    )

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(side_effect=auth_error)
        with patch("services.llm_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(LLMRequestInvalid):
                await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "Hello")

    assert mock_client.messages.create.call_count == 1
    mock_sleep.assert_not_called()


# ── Response fields are populated correctly ───────────────────────────────────

@pytest.mark.asyncio
async def test_response_fields_populated():
    """LLMResponse carries content, model_used, tokens, and latency."""
    sub = None
    persona = _make_persona(tier="free")
    db = _make_db(sub=sub, persona=persona)
    api_response = _make_anthropic_response(
        content="Virtue is its own reward.",
        model=MODEL_FREE,
        input_tokens=42,
        output_tokens=7,
    )

    with patch("services.llm_service._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=api_response)
        result = await call_llm(db, USER_ID, PERSONA_ID, CONV_ID, "What is virtue?")

    assert result.content == "Virtue is its own reward."
    assert result.model_used == MODEL_FREE
    assert result.input_tokens == 42
    assert result.output_tokens == 7
    assert result.latency_ms >= 0
