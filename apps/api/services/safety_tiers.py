"""SAFETY-002 Tier A / Tier B classification over the FROZEN lists (v0.6.1).

NOTHING CALLS THIS YET (PR-1). The judge PR wires it onto the four judged
surfaces; safety_service.check_input is not changed by either PR and keeps its
15 callers byte-identical.

The lists live in data/safety_002_tiers_v0.6.1.json, frozen by the founder on
2026-09-29 and pinned by sha256 in test_safety_tiers.py. A newly found gap goes
into the SAFETY-005 semantic-recall test set, never into that file.

This is a port of the evaluator the lists and the judge were measured with
(round 3, 2026-09-29): every rule below reproduces that run's lexicon tier,
policy keys and final outcome on all 137 eval cases, and a test replays them.

    classify(text)            -> "A" | "B:HIGH" | "B:MEDIUM" | "none"
    never_release_keys(text)  -> the K1-K4 keys a Tier-B message carries
    final_outcome(...)        -> CRISIS | MEDIUM | DISTRESS | DISCUSSING | NORMAL

The rules, as the lists' _meta states them:
  R1/R7  a Tier-A core followed by a locative ("in", "with", "σε", "me", ...)
         is DEMOTED to Tier B HIGH: "I don't want to live in this city".
  R2/B2  a "[subject] " term binds only when a first-person subject precedes
         it with nothing but allow-listed tokens between ("I really ...").
  R3     every governed core has a Tier-B HIGH backstop, so a demotion or a
         failed bind can only ever lower a message to B:HIGH, never to none.
  R6     continuation tokens ("anymore", "πια", "allo") are skipped before
         the locative is looked for.
"""
import json
import re
from pathlib import Path
from typing import NamedTuple

from text_utils import phrase_pattern
from services.safety_service import _prepare

_LISTS_PATH = Path(__file__).resolve().parent.parent / "data" / "safety_002_tiers_v0.6.1.json"
_LISTS = json.loads(_LISTS_PATH.read_text(encoding="utf-8"))

_T = _LISTS["_meta"]["tokens"]
_SUBJECTS = [s.split() for s in _T["subject"]]
_ALLOW = sorted((a.split() for a in _T["subject_allow_B2"]), key=len, reverse=True)
_CONTS = [c.split() for band in _T["continuation_R6"].values() for c in band]
_LOCATIVES = {x for band in _T["locative_R1_R7"].values() for x in band}

_WORD = re.compile(r"\w(?:[\w']*\w)?")    # quote marks around a word are not part of it
_PUNCT = ".,;:!?\""
_SUBJECT_PREFIX = "[subject] "

TIER_A = [e for band in _LISTS["tier_a"].values() for e in band]
TIER_B = [e for band in _LISTS["tier_b"].values() for e in band]

_PATTERNS: dict[str, re.Pattern] = {}


def _pattern(core: str) -> re.Pattern:
    p = _PATTERNS.get(core)
    if p is None:
        p = _PATTERNS[core] = phrase_pattern(core)
    return p


def core_of(term: str) -> str:
    return term[len(_SUBJECT_PREFIX):] if term.startswith(_SUBJECT_PREFIX) else term


def b_level(entry: dict) -> str:
    """'HIGH' or 'MEDIUM' — current_level may carry a trailing note."""
    return entry["current_level"].split()[0]


# ── R2 / B2: the first-person subject rule ───────────────────────────────────

def _allowed_run(tokens: list[str]) -> bool:
    """True when every token is on the B2 allow-list (multi-word entries match as a sequence)."""
    j = 0
    while j < len(tokens):
        for a in _ALLOW:
            if tokens[j:j + len(a)] == a:
                j += len(a)
                break
        else:
            return False
    return True


def bound(text: str, core_start: int) -> bool:
    """A subject occurs before the core with only allow-listed tokens between. No window (B2)."""
    words = _WORD.findall(text[:core_start])
    for i in range(len(words)):
        for s in _SUBJECTS:
            if words[i:i + len(s)] == s and _allowed_run(words[i + len(s):]):
                return True
    return False


# ── R1 / R6 / R7: demotion by a following locative ───────────────────────────

def _tokens_after(text: str, end: int) -> tuple[list[str], list[bool]]:
    toks, stops = [], []
    for r in text[end:].split():
        s = r.rstrip(_PUNCT)
        toks.append(s)
        stops.append(s != r)
    return toks, stops


def _skip_continuations(toks: list[str], stops: list[bool]) -> int | None:
    """Index of the first token after any continuations, or None when a
    continuation carries punctuation (which ends the scan)."""
    i = 0
    while True:
        for c in _CONTS:
            if toks[i:i + len(c)] == c and not any(stops[i:i + len(c) - 1]):
                if stops[i + len(c) - 1]:
                    return None
                i += len(c)
                break
        else:
            return i


def demoting_token(text: str, end: int, locatives: set[str] | None = None) -> str | None:
    """The locative that demotes the core ending at `end`, or None.

    Punctuation (or end of text) straight after the core never demotes, and a
    token carrying trailing punctuation ends the scan. Apostrophes are never
    stripped (R10), so "σ'" stays a locative.
    """
    if not text[end:end + 1].isspace():
        return None
    toks, stops = _tokens_after(text, end)
    i = _skip_continuations(toks, stops)
    if i is None or i >= len(toks):
        return None
    tok = toks[i]
    return tok if tok in (_LOCATIVES if locatives is None else locatives) else None


# ── Matching ─────────────────────────────────────────────────────────────────

class Demotion(NamedTuple):
    entry_id: str
    term: str
    token: str


def _a_matches(entry: dict, text: str):
    """Yield (term, demoting token or None) for every bound match of the entry."""
    demotable = set(entry.get("demotable_terms", []))
    demote_on = entry.get("demote_on", {})         # B3: per-term demotion tokens
    for term in entry["terms"]:
        subj = term.startswith(_SUBJECT_PREFIX)
        for mt in _pattern(core_of(term)).finditer(text):
            if subj and not bound(text, mt.start()):
                continue
            tok = None
            if term in demotable:
                tok = demoting_token(text, mt.end())
            if tok is None and term in demote_on:
                tok = demoting_token(text, mt.end(), set(demote_on[term]))
            yield term, tok


def a_match(entry: dict, text: str) -> str | None:
    """'A' if the entry binds undemoted, 'demoted' if it matches only demoted, else None."""
    out = None
    for _term, tok in _a_matches(entry, text):
        if tok is None:
            return "A"
        out = "demoted"
    return out


def b_match(entry: dict, text: str) -> bool:
    return any(_pattern(t).search(text) for t in entry["terms"])


def classify(raw: str) -> str:
    """The message's tier: 'A', 'B:HIGH', 'B:MEDIUM' or 'none'.

    A demoted Tier-A match is B:HIGH whether or not a Tier-B term also matched.
    R3 guarantees one does (test_safety_tiers enforces it over the frozen file);
    the evaluator asserted it here, and a request path must not raise, so this
    returns the conservative answer instead.
    """
    text = _prepare(raw)
    demoted = False
    for e in TIER_A:
        r = a_match(e, text)
        if r == "A":
            return "A"
        demoted |= r == "demoted"
    if demoted:
        return "B:HIGH"
    levels = {b_level(e) for e in TIER_B if b_match(e, text)}
    if "HIGH" in levels:
        return "B:HIGH"
    if "MEDIUM" in levels:
        return "B:MEDIUM"
    return "none"


class Provenance(NamedTuple):
    level: str
    tier_b_ids: frozenset[str]
    demotions: tuple[Demotion, ...]


def provenance(raw: str) -> Provenance:
    """How the message reached its tier: the Tier-B entries it matched and every
    Tier-A match a locative demoted. The never-release keys are read from this."""
    text = _prepare(raw)
    dem = tuple(
        Demotion(e["id"], term, tok)
        for e in TIER_A
        for term, tok in _a_matches(e, text)
        if tok is not None
    )
    b_ids = frozenset(e["id"] for e in TIER_B if b_match(e, text))
    return Provenance(classify(raw), b_ids, dem)


# ── Policy (founder rulings 2026-09-29) ──────────────────────────────────────
# DATA, not branches: the judge PR and the tests read these. For a Tier-B
# message carrying any key, the judge may escalate to INTENT but may NEVER
# release; any other verdict leaves the lexicon level standing.
#
#   K1 past tense   a Tier-B match on a past-tense entry.
#   K2 EN live-with a Tier-A living core demoted by the locative "with".
#   K3 bare tired   the tired-of-living backstop matched, and the Tier-A entry
#                   produced NO demotion (the bind failed, or the phrase stood
#                   bare — including the English phrase inside Greek text).
#   K4 EL/GL tired  a Greek or greeklish "tired of living" core demoted by με/me.
#                   The Greek "don't want to live with…" cores are NOT keyed
#                   (round-2 ruling (ii)). The phrases are not quoted here:
#                   test_safety_greek scans this folder for them.
POLICY = {
    "K1_past_tense_b": frozenset({"B_EN_11_past_tense", "B_GR_08_past_tense", "B_GL_04_past_tense"}),
    "K2_live_with_a": frozenset({"A_EN_05_not_want_to_live", "A_EN_13_tired_of_living"}),
    "K2_token": "with",
    "K3_tired_b": "B_EN_10_tired_of_living_backstop",
    "K3_tired_a": "A_EN_13_tired_of_living",
    "K4_tired_a": frozenset({"A_GR_09_tired_of_living", "A_GL_02"}),
    "K4_tokens": frozenset({"με", "me"}),
    # R5/R8: what a judge verdict becomes when the message may be released.
    "release_outcome": {
        "DISTRESS_WITHOUT_INTENT": "DISTRESS",
        "DISCUSSING": "DISCUSSING",
        "THIRD_PARTY_RISK": "DISCUSSING",   # recorded, rendered as DISCUSSING (ruled)
    },
}

VERDICTS = ("INTENT", *POLICY["release_outcome"])


def never_release_keys(raw: str) -> list[str]:
    """The K1-K4 keys on a Tier-B message; [] for Tier A and none."""
    level, b_ids, dem = provenance(raw)
    if not level.startswith("B"):
        return []
    keys = [f"K1 past tense ({b})" for b in sorted(b_ids & POLICY["K1_past_tense_b"])]
    keys += [f"K2 EN live-with ({d.entry_id}: '{d.term}' + with)" for d in dem
             if d.entry_id in POLICY["K2_live_with_a"] and d.token == POLICY["K2_token"]]
    if POLICY["K3_tired_b"] in b_ids and not any(d.entry_id == POLICY["K3_tired_a"] for d in dem):
        keys.append(f"K3 bare tired ({POLICY['K3_tired_b']}, no {POLICY['K3_tired_a']} demotion)")
    keys += [f"K4 EL/GL tired ({d.entry_id}: '{d.term}' + {d.token})" for d in dem
             if d.entry_id in POLICY["K4_tired_a"] and d.token in POLICY["K4_tokens"]]
    return keys


def final_outcome(level: str, verdict: str | None, failed: bool, keys: list[str]) -> str:
    """The R5/R8 transition table with the never-release policy on top.

    A judge failure (timeout, error, unparseable) is fail-closed: the lexicon
    level stands — CRISIS on B:HIGH, MEDIUM on B:MEDIUM. Never a release.
    """
    if level == "A":
        return "CRISIS"
    if level == "none":
        return "NORMAL"
    stands = "CRISIS" if level == "B:HIGH" else "MEDIUM"
    if failed:
        return stands
    if verdict == "INTENT":
        return "CRISIS"
    if keys:
        return stands
    return POLICY["release_outcome"][verdict]
