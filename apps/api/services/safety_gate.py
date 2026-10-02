"""SAFETY-002: one decision per message on the four judged surfaces.

Chat send, Council, You-vs-You (prompt and ring-true note). Each surface keeps its
own safety_service.check_input call exactly where it was; this module takes that
result and the FROZEN lists (services/safety_tiers.py) and returns what the surface
acts on. check_input itself is unchanged, and its ten other callers never come here.

    lexicon level   A          -> CRISIS. No judge call.
                    B:HIGH     -> judged. Fail-closed: CRISIS.
                    B:MEDIUM   -> judged. Fail-closed: MEDIUM.
                    none       -> today's behaviour, untouched (none, or low).

  Safety net: when the lists say none but production says medium/high, the message is
  treated as Tier B at production's level. The lists can never lower protection below
  today on these surfaces.

What a decision carries (founder rulings 1-2, 2026-09-29):
  effective  the SafetyResult the surface acts on and STORES. A released message
             (DISTRESS / DISCUSSING) continues as level "low": a signal, not a crisis.
             Nothing downstream suppresses on low; deep mode, adaptive length and
             insight promotion still exclude it.
  record     what the ONE safety_events row records: the lexicon level, unchanged in
             meaning, with action_taken "released" on a release.
  judge      raw_flags["judge"] on that row — tier, keys, verdict, outcome, model,
             latency, tokens, failure. NEVER the model's reason.
"""
from dataclasses import dataclass

from services import safety_judge, safety_tiers
from services.safety_service import SafetyResult

LEVELS = ("none", "low", "medium", "high", "critical")
_TIER_RANK = {"none": 0, "B:MEDIUM": 1, "B:HIGH": 2, "A": 3}

SUPPRESSING = ("CRISIS", "MEDIUM")
RELEASED = ("DISTRESS", "DISCUSSING")

# Founder-approved copy, verbatim (BUILD ruling 3, 2026-09-29). Chat only: appended to
# the persona's system prompt for the one turn the judge released as DISTRESS. HARD
# RULE 9 still applies — the persona names kinds of help, never a number.
DISTRESS_ADDENDUM = (
    "This person is going through something painful right now. Answer gently "
    "and plainly, in your own voice, and keep philosophy in service of them "
    "rather than the other way round. Stay with what they actually wrote; do "
    "not tell them what they feel or why. Somewhere in your reply, say simply "
    "that support exists outside this conversation — someone they trust, a "
    "doctor — and that reaching for it is not a weakness. Never give a number "
    "or name an organisation."
)

# Founder-approved copy, verbatim (SAFETY-009 v2, 2026-10-02). Chat only: appended for
# the one turn the judge released as DISCUSSING when the subject is suicide or self-harm
# (GateDecision.suicide_topic). Found by the #762 smoke: a released "What did Seneca
# think about suicide?" was answered with the open door as a live option. v1 was read
# against an eval and judged insufficient: replies still implied some circumstances
# justify it, and a question-first persona offered no critique at all.
DISCUSSING_SUICIDE_ADDENDUM = (
    "The person is asking about suicide or self-harm as a subject. Discuss the "
    "ideas honestly and in your own voice, but never present ending one's life "
    "as a reasonable option, a freedom or a solution — for them or for anyone — "
    "and never suggest that some circumstances would justify it. If a thinker "
    'held such a view, such as Seneca\'s "open door", present it only as that '
    "thinker's position, do not adopt or endorse it, and say plainly what it "
    "leaves out: that the wish to die often passes, that pain can be shared and "
    "eased, and that support exists outside this conversation. Even if you "
    "usually answer with questions, state this plainly. Then ask, gently, how "
    "they are doing, without assuming they are in danger."
)


def _max_level(a: str, b: str) -> str:
    return a if LEVELS.index(a) >= LEVELS.index(b) else b


def lexicon_level(text: str, prod: SafetyResult) -> str:
    """The message's tier on the frozen lists, raised to production's level when
    production is stricter (the safety net)."""
    tier = safety_tiers.classify(text)
    net = ("B:HIGH" if prod.level in ("high", "critical")
           else "B:MEDIUM" if prod.level == "medium" else "none")
    return tier if _TIER_RANK[tier] >= _TIER_RANK[net] else net


@dataclass(frozen=True)
class GateDecision:
    level: str                       # A | B:HIGH | B:MEDIUM | none
    outcome: str                     # CRISIS | MEDIUM | DISTRESS | DISCUSSING | NORMAL
    effective: SafetyResult
    record: SafetyResult
    action_taken: str | None         # None -> log_safety_event's own default
    judge: dict | None
    verdict: safety_judge.JudgeVerdict | None = None
    # SAFETY-009: a DISCUSSING release whose subject is suicide or self-harm. Only
    # ever True on DISCUSSING.
    suicide_topic: bool = False

    @property
    def suppresses(self) -> bool:
        return self.outcome in SUPPRESSING

    @property
    def released(self) -> bool:
        return self.outcome in RELEASED

    @property
    def judged(self) -> bool:
        return self.level.startswith("B")


def _result(level: str, prod: SafetyResult, category: str, trigger: str) -> SafetyResult:
    return SafetyResult(
        level=level,
        category=prod.category or category,
        trigger=prod.trigger or trigger,     # a matcher constant, never user text
        raw_flags=list(prod.raw_flags),
    )


async def evaluate(
    text: str,
    prod: SafetyResult,
    *,
    context=None,
    prejudged: safety_judge.JudgeVerdict | None = None,
) -> GateDecision:
    """Decide. `context` is an async callable returning the earlier turns; it is
    awaited only on a Tier-B message, so a clean or Tier-A message costs no query.
    `prejudged` is a verdict the router already obtained for this same message —
    passed through so the judge is never called twice."""
    level = lexicon_level(text, prod)

    if level == "none":
        return GateDecision(level, "NORMAL", prod, prod, None, None)

    if level == "A":
        crisis = _result(_max_level(prod.level, "high"), prod, "self_harm", "tier_a")
        return GateDecision(level, "CRISIS", crisis, crisis, None, None)

    keys = safety_tiers.never_release_keys(text)
    if prejudged is not None:
        verdict = prejudged
    else:
        # Context costs a query; with the kill switch off there is no call to feed.
        load = context is not None and safety_judge.enabled()
        verdict = await safety_judge.judge(text, await context() if load else None)
    outcome = safety_tiers.final_outcome(level, verdict.verdict, verdict.failed, keys)

    stands = "high" if level == "B:HIGH" else "medium"
    category = "self_harm" if level == "B:HIGH" else "potential_distress"
    record = _result(_max_level(prod.level, stands), prod, category, "tier_b")

    if outcome == "CRISIS":
        effective = _result(_max_level(prod.level, "high"), prod, "self_harm", "tier_b")
    elif outcome == "MEDIUM":
        effective = record
    else:
        effective = _result("low", prod, category, "tier_b")

    judge = {
        "tier": level,
        "policy_keys": [k[:2] for k in keys],
        "verdict": verdict.verdict,
        "outcome": outcome,
        "model": verdict.model,
        "latency_ms": verdict.latency_ms,
        "input_tokens": verdict.input_tokens,
        "output_tokens": verdict.output_tokens,
        "failed": verdict.failed,
        "fail_kind": verdict.fail_kind,
    }
    return GateDecision(
        level, outcome, effective, record,
        "released" if outcome in RELEASED else "suppressed",
        judge, verdict,
        suicide_topic=outcome == "DISCUSSING" and _is_suicide_topic(text, level),
    )


def _is_suicide_topic(text: str, level: str) -> bool:
    """SAFETY-009 (founder rulings 1-2, 2026-10-02). A suicide/self-harm topic when the
    message matched an entry in POLICY["suicide_topic_b"], OR it stands at B:HIGH with
    no such entry: the safety net (production said high, the lists did not) and the
    conservative demoted-Tier-A answer in classify().

    While the set equals the HIGH entries (pinned by test), this is every B:HIGH
    message and no B:MEDIUM one. The set is still the stated rule: if the lists change,
    the pin breaks before the meaning does."""
    matched = safety_tiers.provenance(text).tier_b_ids & safety_tiers.POLICY["suicide_topic_b"]
    return bool(matched) or level == "B:HIGH"
