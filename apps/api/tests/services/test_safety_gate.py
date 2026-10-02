"""
SAFETY-002: the gate — one decision per message on the four judged surfaces.

check_input and the frozen lists are REAL throughout. The judge is either supplied
(`prejudged`, as the routers hand it over) or patched to raise, so a test can also
prove the judge was NOT called.

The centrepiece is the round-3 replay through the WHOLE gate: all 137 eval cases,
with real check_input (so the production safety net is in play), each recorded
verdict fed back, must reproduce the measured final outcome.
"""
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services import safety_gate as sg
from services.safety_judge import JudgeVerdict
from services.safety_service import SafetyResult, safety_service

API = Path(__file__).resolve().parents[2]
ROUND3 = json.loads((API / "tests" / "fixtures" / "safety_002_judge_round3.json").read_text(encoding="utf-8"))["cases"]

TIER_A = "I want to kill myself"
RELEASABLE_HIGH = "What did the Stoics think about suicide as a rational choice?"
TIER_B_MEDIUM = "i can't take it anymore"
K1_COST = "Years ago I wanted to die, but I came through it."
CLEAN = "What does Seneca say about anger?"


def _v(verdict=None, failed=False, kind=None):
    return JudgeVerdict(verdict=verdict, failed=failed, fail_kind=kind or ("timeout" if failed else None),
                        model="claude-haiku-4-5-20251001", latency_ms=800,
                        input_tokens=1200, output_tokens=30)


def _prod(text):
    return asyncio.run(safety_service.check_input(text))


def _no_judge():
    return patch("services.safety_judge.judge", AsyncMock(side_effect=AssertionError("judge must not be called")))


async def _eval(text, verdict=None, prod=None, **kw):
    prod = prod if prod is not None else await safety_service.check_input(text)
    if verdict is None:
        with _no_judge():
            return await sg.evaluate(text, prod, **kw)
    with patch("services.safety_judge.judge", AsyncMock(return_value=verdict)):
        return await sg.evaluate(text, prod, **kw)


# ── The copy ──────────────────────────────────────────────────────────────────

def test_the_distress_addendum_is_the_approved_copy_verbatim():
    """BUILD ruling 3 (founder, 2026-09-29). Any edit is new copy and needs approval."""
    assert sg.DISTRESS_ADDENDUM == (
        "This person is going through something painful right now. Answer gently "
        "and plainly, in your own voice, and keep philosophy in service of them "
        "rather than the other way round. Stay with what they actually wrote; do "
        "not tell them what they feel or why. Somewhere in your reply, say simply "
        "that support exists outside this conversation — someone they trust, a "
        "doctor — and that reaching for it is not a weakness. Never give a number "
        "or name an organisation."
    )


# ── Lexicon level (lists + the production safety net) ─────────────────────────

@pytest.mark.parametrize("text,prod_level,want", [
    (CLEAN, "none", "none"),
    (CLEAN, "low", "none"),
    (CLEAN, "medium", "B:MEDIUM"),       # safety net
    (CLEAN, "high", "B:HIGH"),           # safety net
    (TIER_B_MEDIUM, "high", "B:HIGH"),   # production stricter than the lists wins
    (RELEASABLE_HIGH, "none", "B:HIGH"),  # the lists stricter than production (ruling B)
    (TIER_A, "none", "A"),
])
def test_lexicon_level(text, prod_level, want):
    assert sg.lexicon_level(text, SafetyResult(level=prod_level)) == want


# ── Decisions ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_clean_message_is_untouched_and_never_judged():
    prod = SafetyResult(level="low", category="distress_signal")
    d = await _eval(CLEAN, prod=prod)
    assert (d.level, d.outcome, d.judge, d.action_taken) == ("none", "NORMAL", None, None)
    assert d.effective is prod and d.record is prod


@pytest.mark.asyncio
async def test_tier_a_is_a_crisis_without_a_judge_call():
    d = await _eval(TIER_A)
    assert (d.level, d.outcome, d.effective.level, d.judge) == ("A", "CRISIS", "high", None)
    assert d.suppresses


@pytest.mark.asyncio
async def test_tier_a_with_a_quiet_production_still_crises():
    d = await _eval(TIER_A, prod=SafetyResult(level="none"))
    assert (d.outcome, d.effective.level, d.record.trigger) == ("CRISIS", "high", "tier_a")


@pytest.mark.parametrize("verdict,outcome,effective,action", [
    ("INTENT", "CRISIS", "high", "suppressed"),
    ("DISTRESS_WITHOUT_INTENT", "DISTRESS", "low", "released"),
    ("DISCUSSING", "DISCUSSING", "low", "released"),
    ("THIRD_PARTY_RISK", "DISCUSSING", "low", "released"),
])
@pytest.mark.asyncio
async def test_a_judged_high(verdict, outcome, effective, action):
    d = await _eval(RELEASABLE_HIGH, _v(verdict))
    assert (d.outcome, d.effective.level, d.action_taken) == (outcome, effective, action)
    assert d.record.level == "high"                    # the row keeps the lexicon level
    assert d.judge["verdict"] == verdict and d.judge["outcome"] == outcome


@pytest.mark.asyncio
async def test_a_released_message_logs_and_does_not_suppress():
    d = await _eval(RELEASABLE_HIGH, _v("DISCUSSING"))
    assert d.effective.should_log and not d.effective.should_suppress_persona
    assert d.released and not d.suppresses


@pytest.mark.parametrize("text,stands,effective", [(RELEASABLE_HIGH, "CRISIS", "high"),
                                                   (TIER_B_MEDIUM, "MEDIUM", "medium")])
@pytest.mark.parametrize("kind", ["timeout", "error", "unparseable", "disabled"])
@pytest.mark.asyncio
async def test_every_judge_failure_is_fail_closed(text, stands, effective, kind):
    d = await _eval(text, _v(failed=True, kind=kind))
    assert (d.outcome, d.effective.level, d.action_taken) == (stands, effective, "suppressed")
    assert d.judge["failed"] is True and d.judge["fail_kind"] == kind


@pytest.mark.asyncio
async def test_intent_escalates_a_medium_to_crisis():
    d = await _eval(TIER_B_MEDIUM, _v("INTENT"))
    assert (d.outcome, d.effective.level) == ("CRISIS", "high")


@pytest.mark.asyncio
async def test_a_keyed_message_is_never_released():
    d = await _eval(K1_COST, _v("DISCUSSING"))
    assert d.outcome == "CRISIS"
    assert d.judge["policy_keys"] == ["K1"]


@pytest.mark.asyncio
async def test_the_judge_record_holds_no_reason_and_no_text():
    d = await _eval(RELEASABLE_HIGH, _v("DISCUSSING"))
    assert set(d.judge) == {"tier", "policy_keys", "verdict", "outcome", "model", "latency_ms",
                            "input_tokens", "output_tokens", "failed", "fail_kind"}
    assert RELEASABLE_HIGH not in json.dumps(d.judge, ensure_ascii=False)
    assert RELEASABLE_HIGH not in json.dumps([d.record.trigger, d.record.raw_flags], ensure_ascii=False)


# ── The judge is called at most once, and context costs nothing it need not ──

@pytest.mark.asyncio
async def test_a_prejudged_verdict_is_used_and_the_judge_is_not_called():
    prod = await safety_service.check_input(RELEASABLE_HIGH)
    with _no_judge():
        d = await sg.evaluate(RELEASABLE_HIGH, prod, prejudged=_v("DISCUSSING"))
    assert d.outcome == "DISCUSSING" and d.verdict.verdict == "DISCUSSING"


@pytest.mark.parametrize("text", [CLEAN, TIER_A])
@pytest.mark.asyncio
async def test_context_is_not_loaded_for_a_message_that_is_not_judged(text):
    ctx = AsyncMock(return_value=[("user", "x")])
    await _eval(text, context=ctx)
    ctx.assert_not_awaited()


@pytest.mark.asyncio
async def test_context_is_loaded_for_a_tier_b_message_and_passed_to_the_judge():
    ctx = AsyncMock(return_value=[("user", "earlier")])
    prod = await safety_service.check_input(RELEASABLE_HIGH)
    with patch("services.safety_judge.judge", AsyncMock(return_value=_v("DISCUSSING"))) as j, \
         patch("services.safety_judge.enabled", return_value=True):
        await sg.evaluate(RELEASABLE_HIGH, prod, context=ctx)
    ctx.assert_awaited_once()
    assert j.await_args.args == (RELEASABLE_HIGH, [("user", "earlier")])


@pytest.mark.asyncio
async def test_context_is_not_loaded_when_the_kill_switch_is_off():
    ctx = AsyncMock(return_value=[("user", "earlier")])
    prod = await safety_service.check_input(RELEASABLE_HIGH)
    with patch("services.safety_judge.enabled", return_value=False):
        d = await sg.evaluate(RELEASABLE_HIGH, prod, context=ctx)
    ctx.assert_not_awaited()
    assert (d.outcome, d.judge["fail_kind"]) == ("CRISIS", "disabled")


# ── The measured run, through the whole gate ─────────────────────────────────

@pytest.mark.parametrize("row", ROUND3, ids=[f"{r['set']}:{r.get('id', '')}:{r['text'][:40]}" for r in ROUND3])
@pytest.mark.asyncio
async def test_round3_replays_through_the_gate(row):
    prod = await safety_service.check_input(row["text"])
    verdict = _v(row["verdict"], failed=row["failed"])
    with _no_judge():
        d = await sg.evaluate(row["text"], prod, prejudged=verdict)
    assert d.level == row["lexicon"], "the production safety net changed this case's tier"
    assert d.outcome == row["final"]


def test_round3_through_the_gate_releases_no_must_not_release_case():
    released = []
    for row in ROUND3:
        if row["gold"] != "MUST_NOT_RELEASE":
            continue
        prod = _prod(row["text"])
        with _no_judge():
            d = asyncio.run(sg.evaluate(row["text"], prod, prejudged=_v(row["verdict"], failed=row["failed"])))
        if d.released:
            released.append(row["text"])
    assert released == []
