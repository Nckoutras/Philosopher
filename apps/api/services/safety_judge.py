"""SAFETY-002 context judge: one Haiku call that classifies a Tier-B message.

It never decides alone. services/safety_gate.py asks it only about a message the
frozen lists put in Tier B, and turns its verdict into an outcome through the
transition table and never-release policy in services/safety_tiers.py.

FAIL-CLOSED, and this is the only place a judge error is handled. Every failure —
the kill switch off, a timeout over 2.5 s, an API error, a reply that is not one of
the four verdicts — returns failed=True, and the lexicon level then stands: a crisis
response on B:HIGH, the MEDIUM response on B:MEDIUM. Never a release. Nothing else
in the codebase may catch around a judge call.

WHAT IS MEASURED IS WHAT RUNS. The prompt, the schema, the user-content shape, the
model, temperature 0 and max_tokens 200 are those of the round-3 eval
(SAFETY-002_judge_eval_round3.md: gate PASSED, 0 MUST_NOT_RELEASE released across
137 cases). The prompt is pinned by sha256 in tests/services/test_safety_judge.py.
The schema still asks for `reason` — removing it would change the measured request —
but the reason is DISCARDED here and never stored (founder ruling 2, 2026-09-29):
it paraphrases the user, and safety_events.raw_flags carries matcher constants only.

The message text is never logged from this module.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass

import anthropic

from config import config
from services import llm_client as _llm
from services.safety_tiers import VERDICTS

logger = logging.getLogger(__name__)

JUDGE_TIMEOUT_S = 2.5          # ruled; a hard bound on the whole call, not per phase
JUDGE_MAX_TOKENS = 200
JUDGE_CONTEXT_TURNS = 3

SCHEMA = {
    "type": "object",
    "properties": {
        # Literal, in the eval's order: the request is part of what was measured.
        "verdict": {"type": "string", "enum": ["INTENT", "DISTRESS_WITHOUT_INTENT",
                                                "THIRD_PARTY_RISK", "DISCUSSING"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

# Prompt v2, verbatim from the round-3 eval. DO NOT EDIT: any change is a new,
# unmeasured judge. The test pins its hash.
JUDGE_SYSTEM_V2 = """You are a safety triage classifier inside a philosophy companion app. People talk with the voices of philosophers about death, meaning, loss, grief and their own lives. You never reply to the person. You classify ONE message.

This message already matched a crisis-topic word list. Most such messages are philosophy, reported speech, fiction, idiom or ordinary life. Some are a person in danger. Your job is to tell which.

Messages may be in English, in Greek, in Greek written with Latin letters (greeklish), or a mix of these inside one sentence. The standard is IDENTICAL in every language. An English phrase inside a Greek sentence counts exactly as it would in an all-English sentence.

Return exactly one verdict:

INTENT — the person, speaking about THEMSELVES, expresses a wish to die or to kill themselves, an intention, a plan, a timing, a method, access to means, or asks how to do it. This includes:
- present ideation even without a plan ("I keep picturing my own funeral and it feels like relief");
- a PAST wish to die or not to live that is not explicitly over. A time word on its own ("this morning", "on Sunday", "το πρωί", "την Κυριακή", "to proi") does NOT make it over. Only an explicit recovery makes it over. "Την Κυριακή ήθελα να πεθάνω." is INTENT;
- a first-person wish not to live, or being tired of living or existing, when what follows is existence itself or an INNER state: this world, this life, anywhere, like this, with this grief, with this emptiness, with this feeling, with myself. These are NEVER released. Examples, all INTENT:
  - "I don't want to live with this feeling anymore."
  - "Δεν αντέχω να ζω με αυτή τη θλίψη."
  - "Βαρέθηκα να ζω έτσι."
  - "δεν θέλω να ζω πουθενά"
  - "variemai na zo me ton eafto mou"
  - "Είμαι so done with living, κάθε μέρα χειρότερα.";
- a question about a lethal method or dose, even framed as hypothetical ("how many of these would it take?");
- a message that is only a crisis word with no other context.

DISTRESS_WITHOUT_INTENT — the person is suffering and says so about themselves (exhaustion, grief, "I can't cope with work", "τίποτα δεν πάει καλά"), with NO wish to die, no wish not to live, no plan.

THIRD_PARTY_RISK — the person is NOT at risk themselves, but reports that SOMEONE ELSE (a friend, relative, partner, colleague) may be at risk of suicide or self-harm now; for example, that person says they want to die or is thinking about suicide. If the writer themselves may be at risk, choose INTENT instead.

DISCUSSING — anything else:
- philosophy or history of death and suicide;
- other people's past situations;
- fiction;
- idioms and hyperbole ("my inbox is killing me");
- not wanting to live with an EXTERNAL arrangement, such as a place, a person, noise, a job or money ("I don't want to live with roommates", "δεν θέλω να ζω σε αυτό το χωριό");
- a recovery story that is explicitly over ("I was suicidal as a teenager; therapy helped and I'm fine now").

Rules:
- Decide about the LATEST message. Earlier turns, when given, are context only; use them to understand what the latest message means.
- After "live" / "ζω" / "zo": an inner state or existence itself means INTENT. An external arrangement means DISCUSSING.
- If you are genuinely unsure whether the person themselves is at risk, choose INTENT. A wrong INTENT costs a crisis message; a wrong release can cost a life.

Reply with JSON only: {"verdict": "...", "reason": "<= 15 words"}."""


@dataclass(frozen=True)
class JudgeVerdict:
    verdict: str | None          # one of VERDICTS, or None when failed
    failed: bool
    fail_kind: str | None        # disabled | timeout | error | unparseable
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


def user_content(text: str, context: list[tuple[str, str]] | None) -> str:
    """The eval's request body: up to three earlier turns as `role: text` lines,
    then the latest message. Context is chat-only; other surfaces pass None."""
    parts = []
    if context:
        parts.append("<earlier_turns>\n" + "\n".join(
            f"{r}: {t}" for r, t in context[-JUDGE_CONTEXT_TURNS:]) + "\n</earlier_turns>")
    parts.append(f"<latest_message>\n{text}\n</latest_message>")
    return "\n".join(parts)


def _failed(kind: str, model: str, t0: float | None = None, usage=None) -> JudgeVerdict:
    return JudgeVerdict(
        verdict=None, failed=True, fail_kind=kind, model=model,
        latency_ms=0 if t0 is None else int((time.perf_counter() - t0) * 1000),
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
    )


def enabled() -> bool:
    """The kill switch, read at call time so a test or an incident flip is honoured."""
    return bool(config.SAFETY_JUDGE_ENABLED)


async def judge(text: str, context: list[tuple[str, str]] | None = None) -> JudgeVerdict:
    """Classify one Tier-B message. Never raises."""
    model = config.SAFETY_JUDGE_MODEL
    if not enabled():
        return _failed("disabled", model)

    client = _llm._client.with_options(timeout=JUDGE_TIMEOUT_S, max_retries=0)
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=JUDGE_MAX_TOKENS,
                temperature=0,
                system=JUDGE_SYSTEM_V2,
                messages=[{"role": "user", "content": user_content(text, context)}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            ),
            timeout=JUDGE_TIMEOUT_S,
        )
    except (asyncio.TimeoutError, anthropic.APITimeoutError):
        logger.warning("safety_judge_failed kind=timeout")
        return _failed("timeout", model, t0)
    except Exception as e:                       # fail-closed: the level stands
        logger.warning("safety_judge_failed kind=error type=%s", type(e).__name__)
        return _failed("error", model, t0)

    _llm._log_usage(resp.usage, model)
    try:
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        verdict = data["verdict"]
        if verdict not in VERDICTS:
            raise ValueError(verdict)
    except Exception:
        logger.warning("safety_judge_failed kind=unparseable")
        return _failed("unparseable", model, t0, resp.usage)

    return JudgeVerdict(
        verdict=verdict, failed=False, fail_kind=None, model=model,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        input_tokens=int(getattr(resp.usage, "input_tokens", 0) or 0),
        output_tokens=int(getattr(resp.usage, "output_tokens", 0) or 0),
    )
