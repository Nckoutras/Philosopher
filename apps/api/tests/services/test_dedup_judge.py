"""MEM2-B5: the dedup judge call. What is measured is what runs, and every failure is open.

The request is pinned to the Step 1 dry run (2026-10-03): the prompt by sha256, the
schema with the enums in the dry run's order, the user-content shape, the dated
model, temperature 0 and max_tokens 200. Every failure — the kill switch, a timeout,
an API error, an unparseable or off-vocabulary reply — returns failed=True, never
raises, and is logged at ERROR with its traceback. The model's reason is read by
nobody and returned by nothing.

The response mocks are plain objects that set every field the code reads (C-06).
"""
import asyncio
import hashlib
import json
import logging
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import dedup_judge as dj

# The calibrated prompt, with the more_specific field (founder approval 2026-10-03).
# A change here is a new, unmeasured judge: re-run the 30 pairs first.
PROMPT_SHA256 = "06bd47fecab2bdd11490a9c195e20edfbc7783c6fc01d6b9c0f4ef007038ab4c"


def _resp(text):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=700, output_tokens=30,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


def _client(create):
    bound = MagicMock()
    bound.messages.create = create
    client = MagicMock()
    client.with_options.return_value = bound
    return client


async def _call(create, enabled=True):
    client = _client(create)
    with patch.object(dj._llm, "_client", client), \
         patch.object(dj.config, "MEMORY_DEDUP_ENABLED", enabled):
        out = await dj.judge_pair("stored row", "new row")
    return out, client


def _reply(verdict="RESTATEMENT", more_specific="new", reason="same thing"):
    return json.dumps({"verdict": verdict, "more_specific": more_specific, "reason": reason})


# ── What is measured is what runs ─────────────────────────────────────────────

def test_the_prompt_is_the_calibrated_prompt_byte_for_byte():
    assert hashlib.sha256(dj.JUDGE_SYSTEM.encode("utf-8")).hexdigest() == PROMPT_SHA256


def test_the_schema_is_the_measured_schema():
    assert dj.SCHEMA == {
        "type": "object",
        "properties": {
            "verdict": {"type": "string",
                        "enum": ["RESTATEMENT", "DISTINCT", "CONTRADICTION"]},
            "more_specific": {"type": "string", "enum": ["earlier", "new", "same"]},
            "reason": {"type": "string"},
        },
        "required": ["verdict", "more_specific", "reason"],
        "additionalProperties": False,
    }


def test_user_content_is_the_measured_shape_stored_row_first():
    assert dj.user_content("old", "new") == (
        "<earlier_note>\nold\n</earlier_note>\n<new_note>\nnew\n</new_note>"
    )


@pytest.mark.asyncio
async def test_the_request_is_the_measured_request():
    create = AsyncMock(return_value=_resp(_reply()))
    out, client = await _call(create)
    assert out.failed is False
    kw = create.await_args.kwargs
    assert kw["model"] == "claude-haiku-4-5-20251001" == dj.JUDGE_MODEL
    assert kw["temperature"] == 0
    assert kw["max_tokens"] == 200
    assert kw["system"] == dj.JUDGE_SYSTEM
    assert kw["messages"] == [{"role": "user", "content": dj.user_content("stored row", "new row")}]
    assert kw["output_config"] == {"format": {"type": "json_schema", "schema": dj.SCHEMA}}


def test_the_model_does_not_follow_the_extraction_model():
    """Pinned in the module: moving ANTHROPIC_MEMORY_MODEL must not move the judge."""
    import inspect
    assert "ANTHROPIC_MEMORY_MODEL" not in inspect.getsource(dj.judge_pair)


# ── Parsing ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", dj.VERDICTS)
@pytest.mark.parametrize("spec", dj.SPECIFICITY)
async def test_every_verdict_and_specificity_parses(verdict, spec):
    out, _ = await _call(AsyncMock(return_value=_resp(_reply(verdict, spec))))
    assert (out.verdict, out.more_specific, out.failed, out.fail_kind) == (verdict, spec, False, None)


@pytest.mark.parametrize("raw", [
    "not json",
    json.dumps({"verdict": "DUPLICATE", "more_specific": "new", "reason": "x"}),
    json.dumps({"verdict": "RESTATEMENT", "more_specific": "both", "reason": "x"}),
    json.dumps({"verdict": "RESTATEMENT", "reason": "x"}),
    json.dumps({"more_specific": "new", "reason": "x"}),
])
def test_parse_reply_refuses_anything_off_vocabulary(raw):
    with pytest.raises(Exception):
        dj.parse_reply(raw)


def test_the_reason_is_returned_by_nothing():
    assert {f.name for f in fields(dj.DedupVerdict)} == {
        "verdict", "more_specific", "failed", "fail_kind", "latency_ms",
    }


# ── Fail-open ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_kill_switch_makes_no_call():
    create = AsyncMock()
    out, _ = await _call(create, enabled=False)
    assert (out.failed, out.fail_kind, out.verdict) == (True, "disabled", None)
    create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("exc, kind", [
    (RuntimeError("api down"), "error"),
    (asyncio.TimeoutError(), "timeout"),
])
async def test_an_api_failure_fails_open_and_logs_error_with_trace(exc, kind, caplog):
    with caplog.at_level(logging.ERROR, logger="services.dedup_judge"):
        out, _ = await _call(AsyncMock(side_effect=exc))
    assert (out.failed, out.fail_kind, out.verdict, out.more_specific) == (True, kind, None, None)
    (rec,) = [r for r in caplog.records if r.name == "services.dedup_judge"]
    assert rec.levelno == logging.ERROR and rec.exc_info is not None
    assert f"kind={kind}" in rec.getMessage()


@pytest.mark.asyncio
async def test_an_unparseable_reply_fails_open_and_logs_error_with_trace(caplog):
    with caplog.at_level(logging.ERROR, logger="services.dedup_judge"):
        out, _ = await _call(AsyncMock(return_value=_resp("RESTATEMENT")))
    assert (out.failed, out.fail_kind) == (True, "unparseable")
    (rec,) = [r for r in caplog.records if r.name == "services.dedup_judge"]
    assert rec.levelno == logging.ERROR and rec.exc_info is not None


# ── Verdict → which row is retired (ruling 2026-10-03) ────────────────────────

def _v(verdict, spec, failed=False):
    return dj.DedupVerdict(verdict=verdict, more_specific=spec, failed=failed,
                           fail_kind="error" if failed else None, latency_ms=0)


@pytest.mark.parametrize("verdict, spec, loser", [
    ("RESTATEMENT", "earlier", "new"),   # the stored row is more specific: it survives
    ("RESTATEMENT", "new", "old"),       # the new row is more specific: it survives
    ("RESTATEMENT", "same", "old"),      # equal: the newer one survives (original rule)
    ("DISTINCT", "earlier", None),
    ("DISTINCT", "same", None),
    ("CONTRADICTION", "new", None),      # ambivalence is never resolved: both stay
    ("CONTRADICTION", "earlier", None),
])
def test_dedup_outcome(verdict, spec, loser):
    assert dj.dedup_outcome(_v(verdict, spec)) == loser


def test_a_failed_verdict_retires_nothing():
    assert dj.dedup_outcome(_v(None, None, failed=True)) is None
