"""Deterministic scoring for the §8.2 harness. Nothing here calls a model.

FOUR SCORES, and each names the production function that produces it so a reader
can check the harness is measuring the shipped check rather than a copy of it:

    brevity            services.postprocessing_service.check_brevity
    persona lexicon    services.postprocessing_service.check_persona_forbidden
    universal lexicon  services.postprocessing_service.check_universal_forbidden
    anti-flex          evals.anti_flex.check_anti_flex          (new; see that module)

plus the modern-term leak, which is data rather than code: each problem in
ten_modern_problems.json carries its own
`auto_grade_checks.forbidden_modern_terms_in_reply`.

BREVITY IS SCORED TWICE, ON PURPOSE (founder ruling D4, 2026-09-22).

Every sample is a first message, so `check_brevity(..., "first_message")` selects
`first_message_max_words` — 35 to 50 depending on persona. But the model is never
told that number. `first_message_max_words` has exactly two readers in the whole
codebase, `check_brevity` and `_compute_max_tokens`, and reaches no prompt. What
the model is told is the STANDARD band, from a line in its own system_fragment
("Keep responses between 20-55 words"). So Socrates is instructed 20-55 and
checked against 35: a 40-word first reply obeys the prompt and fails the check.

Reporting one number would hide that. `against_first_message` is what production
would score; `against_standard` is what the persona was actually asked for. The
gap between the two columns is the finding, logged as BREV-002.

DEEP SAMPLES. `reflective=True` is passed on both, from the sample's own mode,
because the harness knows the mode — it chose it. first_message keeps priority,
so on these samples `against_first_message` is unchanged by the flag and
`against_standard` rises to `reflective_reply_max_words`. That asymmetry is the
point of step 0 and is visible in the two columns.

NOTHING REGENERATES. `would_production_have_corrected` reproduces the TRIGGER
CONDITION at conversation_service.py:1068 — universal-lexicon or persona-lexicon
hit, brevity deliberately excluded — without performing the correction. It is a
column, not a control flow. Brevity is inert in production and stays inert here.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from personas import PERSONA_REGISTRY
from services.postprocessing_service import (
    CheckAction,
    check_brevity,
    check_persona_forbidden,
    check_universal_forbidden,
)

from .anti_flex import check_anti_flex


# ── Style scorers added for B2 ───────────────────────────────────────────────
#
# STANCE IS MEASURED TWO WAYS, AND THE NARROW ONE IS NOT RETIRED.
#
# The original matcher caught only the "notice"/"strikes me" family. Every stance
# number already reported — baseline 6%, arm B 14% — and the founder's 30-40%
# target were set against THAT matcher. Widening it silently would restate every
# prior figure without saying so, so both are reported:
#
#   stance_observation  the original family. Comparable to every earlier run.
#   stance_any          any of the four forms B2 names. Measured over the 440
#                       completions of baseline + arm B: 45.5% and 53.2%.
#
# The four families, and what the corpus already contained:
#
#   observation       baseline  5.9%   arm B 13.6%
#   distinction       baseline 23.6%   arm B 28.2%
#   direct-claim      baseline 28.2%   arm B 29.5%
#   reading-as-mine   baseline  0.0%   arm B  0.0%   <- never once in 440
#
# "A reading you offer as yours" does not exist in the corpus at all. B2 names it
# explicitly, which makes it the cleanest before/after signal in the arm.
STANCE_FAMILIES = {
    "observation": re.compile(
        r"\b(what i notice|what i'?m noticing|i notice|what strikes me|what stands out"
        r"|what catches me|it seems to me|what'?s worth (?:looking at|noticing))\b", re.I),
    "distinction": re.compile(
        r"\bis\s?n'?t [^.?!]{2,40}?[.,]\s*it'?s\b"
        r"|\bthat'?s not [^.?!]{2,40}?[.,]\s*(?:it|that)'?s\b"
        r"|\bnot [^.?!]{2,40}? but rather\b"
        r"|\bthose are (?:two )?different\b|\bthese are not the same\b", re.I),
    "reading_as_mine": re.compile(
        r"\b(i'?d call (?:this|that|it)|i read (?:this|that|it) as"
        r"|to me (?:this|that|it) (?:is|reads|looks)|it reads to me"
        r"|my reading (?:is|of)|i suspect|i'?d say|what i hear (?:is|in))\b", re.I),
    "direct_claim": re.compile(
        r"\byou'?(?:re| are) (?:not )?(?:doing|describing|asking|telling|treating"
        r"|holding|carrying|waiting|performing|building|measuring)\b"
        r"|\byou have already\b", re.I),
}

# opening_present = a question anywhere, OR one of these. Grounded in the arm B
# corpus rather than invented: measured against the 19 replies that contained no
# question mark at all, these six catch 12. Two of them ("say more",
# "I'd like to hear") catch NOTHING today and are kept deliberately — B2 invites
# that form explicitly, so a zero now is the baseline for whether it appears.
#
# REPORT IT AS A FLOOR, NOT A RATE. Seven of those 19 invite a reply with no
# marker at all ("That's not fraud — it's just a long way from home."), and no
# pattern list will catch them.
INVITING = re.compile(
    r"\bthe (?:harder |real |only )?question (?:is|worth|isn'?t)\b"
    r"|\bi'?m curious\b|\bwhat i'?m curious about\b"
    r"|\bworth sitting with\b|\bsit(?:ting)? with\b"
    r"|\btell me\b"
    r"|\b(?:say more|tell me more|more about (?:that|this|it))\b"
    r"|\bi'?d? (?:would )?(?:like|want) to hear\b", re.I)

_ENDS_Q = re.compile(r"[?][\"'”’)\]]*\s*$")


def stance_hits(reply: str) -> list[str]:
    """Which of the four families fire. Order is stable for reporting."""
    return [k for k, rx in STANCE_FAMILIES.items() if rx.search(reply)]


def ends_with_question(reply: str) -> bool:
    return bool(_ENDS_Q.search(reply.strip()))


def has_opening(reply: str) -> bool:
    return "?" in reply or bool(INVITING.search(reply))


@dataclass
class BrevityView:
    word_count: int
    lower: int
    upper: int
    over: bool


@dataclass
class Scores:
    sample_id: str
    persona_slug: str
    problem_id: str
    mode: str
    plan: str
    model: str
    word_count: int

    # two views of the same reply — see module docstring
    against_first_message: BrevityView
    against_standard: BrevityView

    persona_lexicon_hits: list[str] = field(default_factory=list)
    universal_lexicon_hits: list[str] = field(default_factory=list)
    anti_flex_hits: list[str] = field(default_factory=list)
    anti_flex_coverage: list[str] = field(default_factory=list)
    modern_term_leaks: list[str] = field(default_factory=list)

    would_production_have_corrected: bool = False
    bridge_matched: str | None = None
    error: str | None = None

    # B2 additions
    ends_with_question: bool = False
    opening_present: bool = False
    stance_families: list[str] = field(default_factory=list)


@lru_cache(maxsize=512)
def _term_re(term: str) -> re.Pattern:
    """Word-bounded, case-insensitive. Unlike the anti-flex matcher this is NOT
    case-sensitive: "Ghosted" at the start of a sentence is the same leak as
    "ghosted" mid-sentence, and none of these terms is a proper noun whose
    capital carries meaning."""
    return re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)


def _view(result) -> BrevityView:
    lower, upper = result.target_band if result.target_band else (0, 0)
    return BrevityView(
        word_count=result.word_count or 0,
        lower=lower,
        upper=upper,
        over=(result.word_count or 0) > upper if result.target_band else False,
    )


def score(completion, sample) -> Scores:
    """Score one raw completion. `completion` is evals.harness.Completion."""
    persona = PERSONA_REGISTRY[completion.persona_slug]
    reply = completion.reply
    deep = sample.deep

    fm = check_brevity(reply, persona, "first_message", reflective=deep)
    std = check_brevity(reply, persona, "mid_session", reflective=deep)

    pf = check_persona_forbidden(reply, persona)
    fb = check_universal_forbidden(reply)
    af = check_anti_flex(reply, completion.persona_slug, user_text=sample.user_message)

    leaks = [t for t in sample.forbidden_modern_terms if _term_re(t).search(reply)]

    return Scores(
        sample_id=completion.sample_id,
        persona_slug=completion.persona_slug,
        problem_id=completion.problem_id,
        mode=completion.mode,
        plan=completion.plan,
        model=completion.model,
        word_count=len(reply.split()),
        against_first_message=_view(fm),
        against_standard=_view(std),
        persona_lexicon_hits=[h.matched_text for h in pf.hits],
        universal_lexicon_hits=[h.matched_text for h in fb.hits],
        anti_flex_hits=[f"{h.entry_id}:{h.matched}" for h in af.hits],
        anti_flex_coverage=sorted({h.coverage for h in af.hits}),
        modern_term_leaks=leaks,
        # conversation_service.py:1068 — `[c for c in (_fb, _pf) if REGENERATE]`.
        # Brevity is NOT in that tuple and must not be added here.
        would_production_have_corrected=any(
            c.action == CheckAction.REGENERATE for c in (fb, pf)
        ),
        bridge_matched=completion.bridge_matched,
        error=completion.error,
        ends_with_question=ends_with_question(reply),
        opening_present=has_opening(reply),
        stance_families=stance_hits(reply),
    )


CSV_COLUMNS = [
    "sample_id", "persona_slug", "problem_id", "mode", "plan", "model",
    "word_count",
    "fm_upper", "fm_over",
    "std_lower", "std_upper", "std_over",
    "persona_lexicon_hits", "universal_lexicon_hits",
    "anti_flex_hits", "anti_flex_coverage", "modern_term_leaks",
    "would_production_have_corrected", "bridge_matched", "error",
    "ends_with_question", "opening_present", "stance_families",
]


def to_row(s: Scores) -> dict:
    return {
        "sample_id": s.sample_id,
        "persona_slug": s.persona_slug,
        "problem_id": s.problem_id,
        "mode": s.mode,
        "plan": s.plan,
        "model": s.model,
        "word_count": s.word_count,
        "fm_upper": s.against_first_message.upper,
        "fm_over": int(s.against_first_message.over),
        "std_lower": s.against_standard.lower,
        "std_upper": s.against_standard.upper,
        "std_over": int(s.against_standard.over),
        "persona_lexicon_hits": "|".join(s.persona_lexicon_hits),
        "universal_lexicon_hits": "|".join(s.universal_lexicon_hits),
        "anti_flex_hits": "|".join(s.anti_flex_hits),
        "anti_flex_coverage": "|".join(s.anti_flex_coverage),
        "modern_term_leaks": "|".join(s.modern_term_leaks),
        "would_production_have_corrected": int(s.would_production_have_corrected),
        "bridge_matched": s.bridge_matched or "",
        "error": s.error or "",
        "ends_with_question": int(s.ends_with_question),
        "opening_present": int(s.opening_present),
        "stance_families": "|".join(s.stance_families),
    }


SUMMARY_COLUMNS = [
    "persona_slug", "mode", "plan", "model", "n",
    "mean_words", "p95_words",
    "fm_over_rate", "std_over_rate",
    "persona_lexicon_rate", "universal_lexicon_rate",
    "anti_flex_rate", "modern_leak_rate", "would_correct_rate", "errors",
    "ends_q_rate", "no_opening_rate", "stance_observation_rate", "stance_any_rate",
]


def summarise(scores: list[Scores]) -> list[dict]:
    """One row per (persona, mode, plan). Rates only — run 1 reports no pass/fail
    (founder ruling D4): the spec's thresholds were written in 2026-04 against a
    six-persona config with per-persona bands that match no current persona, and
    they are recorded as unanchored until a baseline exists.
    """
    buckets: dict[tuple, list[Scores]] = {}
    for s in scores:
        buckets.setdefault((s.persona_slug, s.mode, s.plan, s.model), []).append(s)

    rows = []
    for (slug, mode, plan, model), group in sorted(buckets.items()):
        ok = [g for g in group if not g.error]
        n = len(ok)
        words = sorted(g.word_count for g in ok)
        rows.append({
            "persona_slug": slug,
            "mode": mode,
            "plan": plan,
            "model": model,
            "n": n,
            "mean_words": round(sum(words) / n, 1) if n else 0,
            "p95_words": words[max(0, int(round(0.95 * n)) - 1)] if n else 0,
            "fm_over_rate": _rate(ok, lambda g: g.against_first_message.over),
            "std_over_rate": _rate(ok, lambda g: g.against_standard.over),
            "persona_lexicon_rate": _rate(ok, lambda g: bool(g.persona_lexicon_hits)),
            "universal_lexicon_rate": _rate(ok, lambda g: bool(g.universal_lexicon_hits)),
            "anti_flex_rate": _rate(ok, lambda g: bool(g.anti_flex_hits)),
            "modern_leak_rate": _rate(ok, lambda g: bool(g.modern_term_leaks)),
            "would_correct_rate": _rate(ok, lambda g: g.would_production_have_corrected),
            "errors": len(group) - n,
            "ends_q_rate": _rate(ok, lambda g: g.ends_with_question),
            # reported as a FLOOR — see INVITING's comment
            "no_opening_rate": _rate(ok, lambda g: not g.opening_present),
            # narrow: comparable to every run reported before B2
            "stance_observation_rate": _rate(
                ok, lambda g: "observation" in g.stance_families),
            # wide: the four forms B2 names
            "stance_any_rate": _rate(ok, lambda g: bool(g.stance_families)),
        })
    return rows


def _rate(group: list[Scores], pred) -> float:
    if not group:
        return 0.0
    return round(sum(1 for g in group if pred(g)) / len(group), 4)


def scores_as_dicts(scores: list[Scores]) -> list[dict]:
    return [asdict(s) for s in scores]
