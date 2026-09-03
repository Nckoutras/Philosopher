"""Self-Portrait question-bank loader + statement helpers.

The "Self-Portrait" is a perpetual self-knowledge quiz. A canonical question bank
(apps/api/data/question_bank.json) is the SOURCE OF TRUTH; this module is content-
AGNOSTIC — it is built against the bank SCHEMA, never against specific questions:

    { "questions": [ { "id", "category", "question", "pills": [...],
                       "theme_tags": [...], "feeds": [...] }, ... ] }

(A bare top-level list of question objects is also accepted, so the real bank file
can drop in with or without the wrapper.)

Responsibilities:
  - Load + validate the bank at import (FAIL FAST on a bad theme_tag).
  - Resolve a (question_id, pill_index) answer into a short memory statement.
  - Provide the per-question dedup key used to seed/refresh a self_portrait
    memory_entry incrementally (see `question_key`).

This module does NOT touch the onboarding pills path (profile_text.py /
profile_to_statements / <what_we_know>). Quiz answers flow into the persona ONLY via
memory recall and the Sunday/season letters — never into the turn-1 prompt.
"""
from __future__ import annotations

import json
import zlib
from pathlib import Path

# Fixed theme vocabulary. Every theme_tag on every question MUST be in this set;
# the loader fails fast at import otherwise, so a typo never reaches production.
THEME_VOCABULARY: frozenset[str] = frozenset({
    "grief", "fear", "envy", "meaning", "duty", "desire", "guilt", "parents",
    "power", "loneliness", "death", "aging", "friendship", "resentment",
    "identity", "discipline", "freedom", "doubt", "control", "dilemma",
})

_BANK_PATH = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"

# Cap on self_portrait statements injected into a single letter's material, so the
# week's/month's own messages stay dominant. Deterministic selection (sorted by
# question_id) keeps the chosen subset stable across runs for the same answer set.
MAX_LETTER_STATEMENTS = 12


def _load_bank(path: Path) -> dict[str, dict]:
    """Load + validate the question bank into an {id: question} map. Raises at import
    on a malformed bank or an out-of-vocabulary theme_tag (fail fast)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions = raw["questions"] if isinstance(raw, dict) else raw
    if not isinstance(questions, list):
        raise ValueError("question_bank: expected a list of questions (or {'questions': [...]})")

    bank: dict[str, dict] = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            raise ValueError(f"question_bank: a question is missing 'id': {q!r}")
        if qid in bank:
            raise ValueError(f"question_bank: duplicate question id {qid!r}")
        if not isinstance(q.get("pills"), list) or not q["pills"]:
            raise ValueError(f"question_bank: question {qid!r} has no pills")
        for tag in (q.get("theme_tags") or []):
            if tag not in THEME_VOCABULARY:
                raise ValueError(
                    f"question_bank: question {qid!r} has out-of-vocabulary theme_tag {tag!r}. "
                    f"Allowed: {sorted(THEME_VOCABULARY)}"
                )
        bank[qid] = q
    return bank


# Loaded once at import — bad bank ⇒ the app/worker fails to boot (intended).
_BANK: dict[str, dict] = _load_bank(_BANK_PATH)


def get_question(question_id: str) -> dict | None:
    """Return the question dict for an id, or None if it is not in the bank."""
    return _BANK.get(question_id)


def total_question_count() -> int:
    """Total number of questions in the bank (used to compute the Pro-locked count
    for the free tier without reaching into the private _BANK from outside)."""
    return len(_BANK)


def total_category_count() -> int:
    """Number of DISTINCT categories in the bank — the denominator for coverage.

    DERIVED, never hardcoded: the bank is the only authority on how many categories
    exist, so adding or removing one moves this number with no code change. Counts
    exactly what answered_category_count counts, so the pair can never disagree
    about what a "category" is."""
    return len({q.get("category", "") for q in _BANK.values()})


# ── Self-Portrait payoff gate ───────────────────────────────────────────────
# The portrait becomes "ready" once a user's answers span breadth across life
# areas — NOT once they reach a raw count. Breadth is what makes a present-tense
# portrait honest. The threshold is tunable; the COUNT is internal only and is
# NEVER exposed to the client (the endpoint surfaces just "forming" | "ready").
READY_CATEGORY_THRESHOLD = 10  # of the 12 categories


def answered_category_count(answers: dict) -> int:
    """Number of DISTINCT bank categories the user has answered at least one
    question in. Unknown ids are skipped (the bank may change under stored
    answers), so this never counts a category that no longer exists."""
    cats: set[str] = set()
    for qid in answers or {}:
        q = _BANK.get(qid)
        if q is not None:
            cats.add(q.get("category", ""))
    return len(cats)


def portrait_state(answers: dict) -> str:
    """Breadth-aware gate: 'ready' once answers span >= READY_CATEGORY_THRESHOLD
    of the 12 categories, else 'forming'. Returns only the state string — the
    underlying count is never surfaced."""
    return "ready" if answered_category_count(answers) >= READY_CATEGORY_THRESHOLD else "forming"


# ── Self-Portrait radar axes (Phase B) ─────────────────────────────────────────
#
# A FIXED, curated 8-axis octagon — IDENTICAL for every user, so portraits stay
# comparable (the per-user signal is the polygon SHAPE, not the axes). Each axis is
# fed by one or more raw theme_tags (the 20-word vocab from THEME_VOCABULARY —
# deliberately NOT the matching bridge in self_portrait_summary, which targets a
# different 12-word vocabulary for persona selection). FROZEN ORDER: the radar draws
# axis i at i*45°, so this sequence is the contract — do not reorder.
#
# Tuple shape: (key, label, tags). The clusters partition the 20-tag vocab (each tag
# on exactly one axis) so every answered question contributes to some axis.
PORTRAIT_AXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("identity",   "Identity",   ("identity",)),
    ("fear",       "Fear",       ("fear", "control")),
    ("freedom",    "Freedom",    ("freedom", "envy")),
    ("desire",     "Desire",     ("desire",)),
    ("doubt",      "Doubt",      ("doubt",)),
    ("duty",       "Duty",       ("duty", "discipline", "guilt")),
    ("connection", "Connection", ("loneliness", "friendship", "parents", "resentment")),
    ("meaning",    "Meaning",    ("meaning", "power", "dilemma", "death", "grief", "aging")),
)

# Flat tag -> axis-key lookup, built once from PORTRAIT_AXES (single source of truth).
_TAG_TO_AXIS: dict[str, str] = {
    tag: key for key, _label, tags in PORTRAIT_AXES for tag in tags
}


def _axis_prevalence() -> dict[str, int]:
    """Per-axis prevalence denominator P_A: how many theme_tag instances across the
    WHOLE bank land on each axis. Derived AT IMPORT from the live bank, so if the bank
    ever changes the denominators self-correct — no hardcoded magic numbers. Bigger
    clusters have a larger P_A, which is exactly what divides out the cluster-size bias
    in portrait_theme_scores (so a wide axis isn't inherently 'higher' for everyone)."""
    counts: dict[str, int] = {key: 0 for key, _l, _t in PORTRAIT_AXES}
    for q in _BANK.values():
        for tag in (q.get("theme_tags") or []):
            axis = _TAG_TO_AXIS.get(tag)
            if axis is not None:
                counts[axis] += 1
    return counts


_AXIS_PREVALENCE: dict[str, int] = _axis_prevalence()


def portrait_theme_scores(answers: dict) -> list[dict]:
    """Per-axis normalized radar scores for the curated octagon, computed ON READ from
    profile.answers. The raw-tag sibling of self_portrait_summary.themes_from_answers,
    WITHOUT the matching bridge — it counts the raw 20-tag vocab straight onto the axes.

    For each axis A:
      raw_A   = # of the user's answered-question theme_tags that fall on A
      rate_A  = raw_A / P_A                 (P_A from the bank → de-biases cluster size)
      score_A = rate_A / max_B(rate_B)      (per-user max-normalize: strongest axis = 1.0
                                             so the polygon fills the frame)
    All-zero answers (no curated hits, e.g. a brand-new user) → every score 0.0; the
    frontend then renders bare spokes + a 'keep answering' line, never a count.

    Returns the axes in FROZEN PORTRAIT_AXES order: [{key, label, score}], score ∈ [0,1].
    NEVER emits raw counts — only the normalized shape crosses the wire (no-count rule).
    Unknown question ids are skipped (the bank may change under stored answers)."""
    raw: dict[str, int] = {key: 0 for key, _l, _t in PORTRAIT_AXES}
    for qid in answers or {}:
        q = _BANK.get(qid)
        if q is None:
            continue
        for tag in (q.get("theme_tags") or []):
            axis = _TAG_TO_AXIS.get(tag)
            if axis is not None:
                raw[axis] += 1

    rates: dict[str, float] = {}
    for key, _label, _tags in PORTRAIT_AXES:
        p = _AXIS_PREVALENCE.get(key, 0)
        rates[key] = (raw[key] / p) if p > 0 else 0.0

    max_rate = max(rates.values()) if rates else 0.0
    return [
        {
            "key": key,
            "label": label,
            "score": round(rates[key] / max_rate, 4) if max_rate > 0 else 0.0,
        }
        for key, label, _tags in PORTRAIT_AXES
    ]


# ── Free-tier gating ──────────────────────────────────────────────────────────
#
# The free tier sees a fixed, DETERMINISTIC slice of the bank; Pro sees everything.
# The slice is computed once at import (the bank is immutable at runtime) so every
# request and worker agrees on exactly which ids are free — the PATCH gate and the
# GET visibility filter must never disagree.

FREE_QUESTION_LIMIT = 15


def _ids_by_category(qids: list[str]) -> dict[str, list[str]]:
    """Group question ids by their bank category, ids sorted within each category."""
    by_category: dict[str, list[str]] = {}
    for qid in qids:
        by_category.setdefault(_BANK[qid].get("category", ""), []).append(qid)
    for ids in by_category.values():
        ids.sort()
    return by_category


def _round_robin_ids(ids_by_category: dict[str, list[str]], limit: int | None) -> list[str]:
    """Round-robin across categories (categories sorted; ids already sorted within each),
    taking one id per category per pass until `limit` ids are collected — or, when
    `limit is None`, until every category is exhausted (the full ordered list). Round-
    robin (rather than first-N-by-id) keeps the result spread across life areas instead
    of front-loading whichever category sorts first. Pure + deterministic for a given
    input, so callers can freeze the result once."""
    ordered_categories = sorted(ids_by_category)
    chosen: list[str] = []
    round_idx = 0
    # Stop once we've collected the limit OR no category has anything left to give.
    while limit is None or len(chosen) < limit:
        progressed = False
        for cat in ordered_categories:
            ids = ids_by_category[cat]
            if round_idx < len(ids):
                chosen.append(ids[round_idx])
                progressed = True
                if limit is not None and len(chosen) >= limit:
                    break
        if not progressed:
            break
        round_idx += 1
    return chosen


def _compute_free_question_ids() -> frozenset[str]:
    """Deterministic interleave: group the bank by category (categories sorted;
    questions sorted by id within each), then round-robin across categories taking
    one each until FREE_QUESTION_LIMIT ids are collected. Round-robin (rather than
    first-N-by-id) keeps the free slice spread across life areas instead of front-
    loading whichever category sorts first. Stable for a given bank → frozen once."""
    by_category = _ids_by_category(list(_BANK.keys()))
    return frozenset(_round_robin_ids(by_category, FREE_QUESTION_LIMIT))


_FREE_QUESTION_IDS: frozenset[str] = _compute_free_question_ids()


def free_question_ids() -> frozenset[str]:
    """The fixed set of question ids visible to the free tier (cached at import)."""
    return _FREE_QUESTION_IDS


def is_free_question(question_id: str) -> bool:
    """True iff this question is part of the free tier's visible slice."""
    return question_id in _FREE_QUESTION_IDS


def _public_question(q: dict) -> dict:
    """Project a bank question to its PUBLIC shape — {id, category, question, pills}.
    Strips the internal `theme_tags` and `feeds` (matching/seeding routing detail
    that must never leave the API)."""
    return {
        "id": q["id"],
        "category": q["category"],
        "question": q["question"],
        "pills": list(q.get("pills") or []),
    }


def visible_questions(is_pro: bool) -> list[dict]:
    """Questions the given tier may see, round-robin across categories (categories
    sorted; ids sorted within each) so consecutive questions move between life areas
    instead of running through one category at a time. Pro → all questions; free →
    only the free slice. Returns the PUBLIC shape only.

    Reorder-safe for stored answers: answers are keyed by question id, not position,
    so changing the served order never duplicates, drops, or mismatches an existing
    answer — only the order of the remaining (and answered) questions changes."""
    visible_ids = [
        qid for qid in _BANK
        if is_pro or is_free_question(qid)
    ]
    ordered_ids = _round_robin_ids(_ids_by_category(visible_ids), None)
    return [_public_question(_BANK[qid]) for qid in ordered_ids]


def question_key(question_id: str) -> int:
    """Deterministic per-question key for self_portrait memory dedup.

    SEMANTIC OVERLOAD WARNING: this value is stored in MemoryEntry.source_turn,
    which everywhere else means "the chat message-turn index a memory was
    extracted from". For entry_type='self_portrait' rows ONLY, source_turn instead
    holds this stable hash of the question_id, so that re-answering question X can
    deactivate exactly that question's prior row and insert one fresh embedded row
    (incremental — one embed per tap, not a full re-seed). No read path interprets
    source_turn for self_portrait rows (self_model excludes them; recall/insight
    read only content), so the overload is safe. crc32 is masked to 31 bits to fit
    Postgres int4; collisions across a user's few-dozen answers are negligible.
    """
    return zlib.crc32(question_id.encode("utf-8")) & 0x7FFFFFFF


def answer_statement(question_id: str, pill_index: int) -> str | None:
    """Resolve one answer into a short, content-agnostic self-statement (third
    person, matching the onboarding-statement voice). Returns None if the question
    is unknown or the pill_index is out of range — so callers seed nothing rather
    than a malformed row. Templated from the question + chosen pill label only; NO
    per-pill authored fragments (keeps the module bank-agnostic)."""
    q = get_question(question_id)
    if q is None:
        return None
    pills = q.get("pills") or []
    if not (0 <= pill_index < len(pills)):
        return None
    return f"Asked “{q['question']}”, they answered: {pills[pill_index]}."


def shift_statement(question_id: str, old_index: int, new_index: int) -> str | None:
    """Resolve a re-answer into a short, content-agnostic movement statement (third
    person, matching answer_statement's voice). Returns None if the question is unknown
    or either index is out of the pills range — so callers seed nothing rather than a
    malformed row. Templated from the question + the two chosen pill labels only."""
    q = get_question(question_id)
    if q is None:
        return None
    pills = q.get("pills") or []
    if not (0 <= old_index < len(pills)) or not (0 <= new_index < len(pills)):
        return None
    return (
        f"On the question “{q['question']}”, they used to answer "
        f"“{pills[old_index]}” and now answer “{pills[new_index]}”."
    )


def answers_to_statements(answers: dict, *, limit: int = MAX_LETTER_STATEMENTS) -> list[str]:
    """Map a profile.answers dict ({question_id: pill_index}) to self-statements.

    Deterministic: questions are taken in sorted question_id order and capped to
    `limit` (default MAX_LETTER_STATEMENTS) so a growing bank can never let quiz
    answers crowd out a letter's actual week/month material. Unknown ids or
    out-of-range pills are silently skipped (the bank may change under stored
    answers). Used by the Sunday/season letter injection."""
    out: list[str] = []
    for qid in sorted(answers):
        if len(out) >= limit:
            break
        stmt = answer_statement(qid, answers[qid])
        if stmt:
            out.append(stmt)
    return out
