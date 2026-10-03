"""MEM2-B5 write-time dedup judge: one Haiku call that compares two memory rows.

It never retires anything itself. MemoryService.dedup_new_entries asks it about a
pair that already cleared DUPLICATE_SIM_THRESHOLD, and turns its verdict into a
write through dedup_outcome below.

FAIL-OPEN, the opposite of the safety judge and for the opposite reason. A
failure there could release a person in danger, so it fails closed. A failure
here only means a duplicate is kept, which is the pre-B5 state of every row. So
every failure — the kill switch off, a timeout, an API error, a reply that does
not parse — returns failed=True, and the caller retires nothing.

WHAT IS MEASURED IS WHAT RUNS. The prompt, the schema, the user-content shape,
the model, temperature 0 and max_tokens 200 are those of the Step 1 dry run
(2026-10-03: 30 hand-labelled production pairs, both orders, three runs; 13/13
paraphrases RESTATEMENT in the production band). The prompt is pinned by sha256
in tests/services/test_dedup_judge.py: any wording change is a new, unmeasured
judge and re-runs the 30 pairs first (founder ruling 2026-10-03).

The schema asks for `reason` because the measured request did. It is DISCARDED
here and never logged: it paraphrases the person's memory rows, and the row
content is never logged from this module.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass

from config import config
from services import llm_client as _llm

logger = logging.getLogger(__name__)

# Pinned to the dated id the dry run measured, deliberately NOT read from
# ANTHROPIC_MEMORY_MODEL: moving the extraction model must not silently move
# this judge onto an unmeasured one.
JUDGE_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MAX_TOKENS = 200
# Worker-side, never on a request path, so the bound is about a stuck call
# holding the memory task open, not about anyone waiting.
JUDGE_TIMEOUT_S = 15.0

VERDICTS = ("RESTATEMENT", "DISTINCT", "CONTRADICTION")
SPECIFICITY = ("earlier", "new", "same")

SCHEMA = {
    "type": "object",
    "properties": {
        # Literal, in the dry run's order: the request is part of what was measured.
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "more_specific": {"type": "string", "enum": list(SPECIFICITY)},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "more_specific", "reason"],
    "additionalProperties": False,
}

# Verbatim from the calibrated dry run. DO NOT EDIT: the test pins its hash.
JUDGE_SYSTEM = """You compare two notes that a companion app keeps about the same person, and decide whether the NEW note only says again what the EARLIER note already says. You never reply to the person. You judge ONE pair.

Both notes were written by a model reading the person's conversations. They are not the person's own words, and the app will keep only one of them if they say the same thing.

The notes may be in English, in Greek, or one of each. Judge the meaning, never the language or the wording.

Return exactly one verdict:

RESTATEMENT — both notes are about the same thing in the person's life and say essentially the same thing about it: the same struggle, belief, value or habit, reworded, re-emphasised, or told with a little more or less detail. Keeping both would make the app hold one fact twice. Examples:
- "User feels they have no friends and is experiencing loneliness." / "User feels isolated and lacks meaningful friendships."
- "User avoids conflict at work to keep the peace." / "User tends to stay quiet in workplace disagreements rather than risk friction."

DISTINCT — the notes are related but say different things. This includes: a different person, place or event; a different side of the same theme (a cause and its consequence, a feeling and a habit, a fear and a goal); or one note makes a claim about the person that the other does not. Keeping both loses nothing. Examples:
- "User worries about money if they leave their job." / "User hesitates to act on a wish to change careers."
- "User misses their father, who died last year." / "User is grieving the end of a long friendship."

CONTRADICTION — the notes say opposite things about the same matter, so they cannot both describe the person in the same way. Example:
- "User recharges best alone and values solitude." / "User finds being alone draining and seeks company to feel like themselves."

Rules:
- If you are unsure between RESTATEMENT and DISTINCT, choose DISTINCT. A wrong DISTINCT keeps a duplicate; a wrong RESTATEMENT throws away something true.
- A note that names a different person, place or event from the other is DISTINCT, even when the feeling is the same.
- Do not judge which note is better written or more accurate.

Reply with JSON only: {"verdict": "...", "more_specific": "earlier" | "new" | "same", "reason": "<= 15 words"}. "more_specific" says which note carries more concrete, specific detail about the person's life."""


@dataclass(frozen=True)
class DedupVerdict:
    verdict: str | None          # one of VERDICTS, or None when failed
    more_specific: str | None    # one of SPECIFICITY, or None when failed
    failed: bool
    fail_kind: str | None        # disabled | timeout | error | unparseable
    latency_ms: int


def user_content(earlier: str, new: str) -> str:
    """The dry run's request body. EARLIER is the row already stored, NEW the row
    this extraction call just wrote — always in that order (see more_specific)."""
    return f"<earlier_note>\n{earlier}\n</earlier_note>\n<new_note>\n{new}\n</new_note>"


def enabled() -> bool:
    """The kill switch, read at call time so a test or an incident flip is honoured."""
    return bool(config.MEMORY_DEDUP_ENABLED)


def _failed(kind: str, t0: float | None = None) -> DedupVerdict:
    return DedupVerdict(
        verdict=None, more_specific=None, failed=True, fail_kind=kind,
        latency_ms=0 if t0 is None else int((time.perf_counter() - t0) * 1000),
    )


def parse_reply(raw: str) -> tuple[str, str]:
    """(verdict, more_specific) from the model's JSON. Raises on anything else.

    `more_specific` IS WEAKER THAN `verdict`, and that is measured, not assumed.
    Over the 13 paraphrase pairs it swapped correctly with the order of the two
    notes on 10. On two (#4, #15) it answered "earlier" in BOTH orders — it
    favours whichever note it is shown first — and on one (#14) it answered
    "same" one way and "new" the other. Production always shows the stored row as
    "earlier", so on pairs like #4 and #15 the OLD row survives whatever the
    actual specificity. Both rows are restatements, so the cost is choosing the
    slightly less detailed of two equivalent rows, never losing a distinct fact.
    Accepted as calibrated (founder ruling 2026-10-03); not corrected here,
    because a correction would be a second, unmeasured judge.
    """
    data = json.loads(raw)
    verdict = data["verdict"]
    more_specific = data["more_specific"]
    if verdict not in VERDICTS:
        raise ValueError(f"verdict {verdict!r}")
    if more_specific not in SPECIFICITY:
        raise ValueError(f"more_specific {more_specific!r}")
    return verdict, more_specific


async def judge_pair(earlier: str, new: str) -> DedupVerdict:
    """Compare one stored row with one new row. Never raises.

    Every failure is logged at ERROR with its traceback here, where the exception
    is, and the caller logs the decision line (verdict=error) on its template.
    """
    if not enabled():
        return _failed("disabled")

    client = _llm._client.with_options(timeout=JUDGE_TIMEOUT_S, max_retries=1)
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=JUDGE_MAX_TOKENS,
                temperature=0,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": user_content(earlier, new)}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            ),
            timeout=JUDGE_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        logger.error("dedup_judge_failed kind=timeout", exc_info=True)
        return _failed("timeout", t0)
    except Exception:                       # fail-open: nothing is retired
        logger.error("dedup_judge_failed kind=error", exc_info=True)
        return _failed("error", t0)

    _llm._log_usage(resp.usage, JUDGE_MODEL)
    try:
        verdict, more_specific = parse_reply(
            next(b.text for b in resp.content if b.type == "text")
        )
    except Exception:
        logger.error("dedup_judge_failed kind=unparseable", exc_info=True)
        return _failed("unparseable", t0)

    return DedupVerdict(
        verdict=verdict, more_specific=more_specific, failed=False, fail_kind=None,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )


def dedup_outcome(verdict: DedupVerdict) -> str | None:
    """Which row a verdict retires: "old", "new", or None (both stay). PURE.

    Founder rulings 2026-10-03 (the second superseding "new always supersedes old"):
      RESTATEMENT    the SURVIVOR is the more specific note; on "same", the newer
                     one. So "earlier" retires the new row, "new"/"same" the old.
      DISTINCT       both stay.
      CONTRADICTION  both stay, and the caller flags it. Ambivalence is never
                     resolved by this system.
      failed         both stay (fail-open).
    """
    if verdict.failed or verdict.verdict != "RESTATEMENT":
        return None
    return "new" if verdict.more_specific == "earlier" else "old"
