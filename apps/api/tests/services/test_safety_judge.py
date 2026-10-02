"""
SAFETY-002: the judge call. What is measured is what runs, and every failure is closed.

The request is pinned to the round-3 eval: prompt v2 by sha256, the schema with the
enum in the eval's order, the user-content shape, the dated model, temperature 0,
max_tokens 200, a 2.5 s bound and no retries. Every failure — the kill switch, a
timeout, an API error, an unparseable or off-vocabulary reply — returns failed=True
and never raises. The model's reason is read by nobody and returned by nothing.

The response mocks are plain objects that set every field the code reads (C-06).
"""
import asyncio
import hashlib
import json
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from services import safety_judge as sj

PROMPT_V2_SHA256 = "13119408fa16b8f022bacc1f65aec673d19c82bb3cbb1142f130233f973d1250"


def _resp(text, input_tokens=1210, output_tokens=31):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


def _client(create):
    bound = MagicMock()
    bound.messages.create = create
    client = MagicMock()
    client.with_options.return_value = bound
    return client


async def _call(create, text="msg", context=None, enabled=True):
    client = _client(create)
    with patch.object(sj._llm, "_client", client), \
         patch.object(sj.config, "SAFETY_JUDGE_ENABLED", enabled):
        out = await sj.judge(text, context)
    return out, client


# ── What is measured is what runs ─────────────────────────────────────────────

def test_prompt_v2_is_the_measured_prompt_byte_for_byte():
    assert hashlib.sha256(sj.JUDGE_SYSTEM_V2.encode("utf-8")).hexdigest() == PROMPT_V2_SHA256


def test_the_schema_is_the_measured_schema():
    assert sj.SCHEMA == {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["INTENT", "DISTRESS_WITHOUT_INTENT",
                                                   "THIRD_PARTY_RISK", "DISCUSSING"]},
            "reason": {"type": "string"},
        },
        "required": ["verdict", "reason"],
        "additionalProperties": False,
    }


def test_user_content_is_the_measured_shape():
    assert sj.user_content("m", None) == "<latest_message>\nm\n</latest_message>"
    ctx = [("user", "a"), ("assistant", "b"), ("user", "c"), ("assistant", "d")]
    assert sj.user_content("m", ctx) == (
        "<earlier_turns>\nassistant: b\nuser: c\nassistant: d\n</earlier_turns>\n"
        "<latest_message>\nm\n</latest_message>"
    )


@pytest.mark.asyncio
async def test_the_request_is_the_measured_request():
    create = AsyncMock(return_value=_resp('{"verdict": "DISCUSSING", "reason": "philosophy"}'))
    out, client = await _call(create, "the text", [("user", "earlier")])

    client.with_options.assert_called_once_with(timeout=2.5, max_retries=0)
    kw = create.await_args.kwargs
    assert kw == {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "temperature": 0,
        "system": sj.JUDGE_SYSTEM_V2,
        "messages": [{"role": "user", "content": sj.user_content("the text", [("user", "earlier")])}],
        "output_config": {"format": {"type": "json_schema", "schema": sj.SCHEMA}},
    }
    assert out.verdict == "DISCUSSING" and out.failed is False and out.fail_kind is None
    assert (out.input_tokens, out.output_tokens) == (1210, 31)


@pytest.mark.parametrize("verdict", ["INTENT", "DISTRESS_WITHOUT_INTENT", "THIRD_PARTY_RISK", "DISCUSSING"])
@pytest.mark.asyncio
async def test_each_verdict_is_returned(verdict):
    out, _ = await _call(AsyncMock(return_value=_resp(json.dumps({"verdict": verdict, "reason": "r"}))))
    assert (out.verdict, out.failed) == (verdict, False)


def test_the_reason_is_carried_by_nothing():
    """Ruling 2: the reason paraphrases the user; it is requested (the measured
    schema asks for it) and discarded."""
    assert "reason" not in {f.name for f in fields(sj.JudgeVerdict)}


# ── Fail-closed ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_kill_switch_makes_no_call_and_fails_closed():
    create = AsyncMock()
    out, client = await _call(create, enabled=False)
    create.assert_not_awaited()
    client.with_options.assert_not_called()
    assert (out.verdict, out.failed, out.fail_kind, out.latency_ms) == (None, True, "disabled", 0)


@pytest.mark.asyncio
async def test_an_sdk_timeout_fails_closed():
    exc = anthropic.APITimeoutError(request=MagicMock())
    out, _ = await _call(AsyncMock(side_effect=exc))
    assert (out.verdict, out.failed, out.fail_kind) == (None, True, "timeout")


@pytest.mark.asyncio
async def test_a_slow_call_is_cut_at_the_bound_and_fails_closed():
    """The SDK timeout is per phase; the wait_for bound is on the whole call."""
    async def slow(**kw):
        await asyncio.sleep(0.5)
        return _resp('{"verdict": "DISCUSSING", "reason": "r"}')

    with patch.object(sj, "JUDGE_TIMEOUT_S", 0.05):
        out, _ = await _call(slow)
    assert (out.verdict, out.failed, out.fail_kind) == (None, True, "timeout")


@pytest.mark.asyncio
async def test_an_api_error_fails_closed():
    out, _ = await _call(AsyncMock(side_effect=RuntimeError("overloaded")))
    assert (out.verdict, out.failed, out.fail_kind) == (None, True, "error")


@pytest.mark.parametrize("text", [
    "not json",
    '{"reason": "no verdict"}',
    '{"verdict": "SAFE", "reason": "off-vocabulary"}',
    '{"verdict": null, "reason": "r"}',
])
@pytest.mark.asyncio
async def test_an_unparseable_reply_fails_closed(text):
    out, _ = await _call(AsyncMock(return_value=_resp(text)))
    assert (out.verdict, out.failed, out.fail_kind) == (None, True, "unparseable")
    assert (out.input_tokens, out.output_tokens) == (1210, 31)   # the call still cost


@pytest.mark.asyncio
async def test_a_reply_without_a_text_block_fails_closed():
    resp = _resp("x")
    resp.content = [SimpleNamespace(type="tool_use", text=None)]
    out, _ = await _call(AsyncMock(return_value=resp))
    assert (out.failed, out.fail_kind) == (True, "unparseable")
