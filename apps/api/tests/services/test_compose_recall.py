"""Hybrid recall's lane composition (Memory-v2 Ruling #5, design §2b/§2c/§5a).

WHY THESE ARE UNIT TESTS. `compose_recall` is a pure function over already-fetched
rows precisely so that the half of Ruling #5 that is ARITHMETIC — caps, per-type
quotas, one-way spillover, ordering, tie-breaks — can be tested without a
database. What genuinely needs live Postgres (that the right rows ARRIVE: pgvector
distance, the window ranking, the floor in SQL) is in tests/db_live.

C-06 THROUGHOUT: rows are a real frozen dataclass, not MagicMock. compose_recall
reads .entry_type, .content, .score, .created_at and .id, and a MagicMock would
auto-create every one of them — a missing `score` would compare as a Mock and
silently reorder the block instead of raising, which is the exact failure mode
C-06 exists to prevent. The dataclass raises on a missing field.

Run: cd apps/api && pytest tests/services/test_compose_recall.py -v
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from services.memory_service import (
    INFERRED_CAP,
    INFERRED_PER_TYPE,
    INFERRED_SCORE_FLOOR,
    RECALL_TOTAL_BUDGET,
    STANDING_CAP,
    STANDING_PER_TYPE,
    STANDING_TYPES,
    compose_recall,
)

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Row:
    """Every field compose_recall reads, set explicitly (C-06)."""
    id: str
    entry_type: str
    content: str
    score: float
    created_at: datetime


def _row(entry_type, score, *, id=None, age_minutes=0, content=None):
    return Row(
        id=id or f"{entry_type}-{score}-{age_minutes}",
        entry_type=entry_type,
        content=content or f"{entry_type}@{score}",
        score=score,
        created_at=T0 - timedelta(minutes=age_minutes),
    )


def _types(rows):
    return [r.entry_type for r in rows]


def _contents(rows):
    return [r.content for r in rows]


# ── The constants the lanes are built from ───────────────────────────────────

def test_the_lane_constants_are_internally_consistent():
    """The spillover arithmetic in compose_recall clamps by the smaller of two
    expressions, which only agree while this holds. If someone tunes one constant
    alone, this fails here rather than silently changing the block size."""
    assert STANDING_CAP + INFERRED_CAP == RECALL_TOTAL_BUDGET
    assert STANDING_TYPES == ("stated", "self_portrait")


# ── Lane A: no floor ─────────────────────────────────────────────────────────

def test_a_standing_row_below_the_floor_is_still_returned():
    """THE POINT OF LANE A. `stated` is the person's own words and `self_portrait`
    is a pill they tapped; neither can be WRONG about them the way an inferred row
    can, so neither has to earn its place by cosine score."""
    rows = [
        _row("stated", 0.10),
        _row("self_portrait", 0.05),
        _row("belief", 0.10),      # inferred at the same score → dropped
    ]

    out = compose_recall(rows)

    assert _types(out) == ["stated", "self_portrait"]


def test_lane_a_is_capped_in_total_and_per_type():
    """Bounded, or a user with a long quiz history floods the block."""
    rows = [_row("self_portrait", 0.9 - i / 100, id=f"sp{i}") for i in range(5)]
    rows += [_row("stated", 0.8 - i / 100, id=f"st{i}") for i in range(5)]

    out = compose_recall(rows)
    standing = [r for r in out if r.entry_type in STANDING_TYPES]

    assert len(standing) == STANDING_CAP
    assert _types(standing).count("self_portrait") <= STANDING_PER_TYPE
    assert _types(standing).count("stated") <= STANDING_PER_TYPE


# ── Lane B: floor and quota ──────────────────────────────────────────────────

def test_the_floor_is_applied_to_inferred_rows_from_both_sides():
    """A hair under is out, a hair over is in — the boundary is where the constant
    says, not near it."""
    rows = [
        _row("belief", INFERRED_SCORE_FLOOR - 0.01, content="under"),
        _row("value", INFERRED_SCORE_FLOOR + 0.01, content="over"),
    ]

    assert _contents(compose_recall(rows)) == ["over"]


def test_the_floor_is_exclusive_at_exactly_the_boundary():
    """`score > floor`, not >=. Pinned because the SQL and this function must agree
    on the comparison, and a mismatch would show up only as one row's worth of
    difference between what the query fetched and what the block rendered."""
    assert compose_recall([_row("belief", INFERRED_SCORE_FLOOR)]) == []


def test_one_prolific_type_cannot_take_every_inferred_slot():
    """THE QUOTA. Without it a user whose extractor keeps producing `pattern` rows
    gets a block of nothing but patterns, and the single `milestone` that actually
    answers the turn never appears."""
    rows = [_row("pattern", 0.99 - i / 100, id=f"p{i}") for i in range(6)]
    rows.append(_row("milestone", 0.80, content="the one that matters"))

    out = compose_recall(rows)

    assert _types(out).count("pattern") == INFERRED_PER_TYPE
    assert "the one that matters" in _contents(out)


# ── Lane membership is a catch-all, never an allow-list ──────────────────────

def test_an_unknown_entry_type_is_treated_as_inferred():
    """`entry_type` is NOT validated on write — extraction stores the LLM's `type`
    verbatim — so an unrecognised value can exist in the table. It must land in
    Lane B (floor-gated, quota'd), never be dropped. An allow-list implementation
    would silently lose it."""
    rows = [_row("some_future_type", 0.95, content="kept"),
            _row("some_future_type", 0.10, content="dropped by the floor")]

    assert _contents(compose_recall(rows)) == ["kept"]


def test_self_portrait_shift_is_inferred_not_standing():
    """Ruled 2026-09-03 (design §2b): Lane A is the closed two-type set Ruling #5
    names, so a shift row is Lane B by construction — it clears the floor or it
    does not appear."""
    rows = [_row("self_portrait_shift", 0.95, content="above"),
            _row("self_portrait_shift", 0.20, content="below")]

    out = compose_recall(rows)

    assert _contents(out) == ["above"]
    assert out[0].entry_type not in STANDING_TYPES


# ── Spillover: one way only ──────────────────────────────────────────────────

def test_unfilled_standing_slots_flow_to_inferred():
    """A user with no quiz answers and no ritual text still gets a full block."""
    rows = [_row("pattern", 0.99, id="a"), _row("belief", 0.98, id="b"),
            _row("value", 0.97, id="c"), _row("struggle", 0.96, id="d"),
            _row("milestone", 0.95, id="e"), _row("counterview_belief", 0.94, id="f"),
            _row("onboarding_profile", 0.93, id="g"), _row("pattern", 0.92, id="h"),
            _row("belief", 0.91, id="i")]

    out = compose_recall(rows)

    assert len(out) == RECALL_TOTAL_BUDGET
    assert all(r.entry_type not in STANDING_TYPES for r in out)


def test_inferred_never_spills_into_standing():
    """The reverse direction is forbidden: Lane A has NO floor, so an unbounded
    Lane A would put arbitrarily many unscored rows in the prompt. Four standing
    rows compete for three slots and the fourth does not get in, however much
    room Lane B has left.

    The inferred rows deliberately span SIX types: with all nine on one type the
    per-type quota would cap Lane B at 2 and this would pass for the wrong
    reason, measuring the quota instead of the spillover direction."""
    rows = [_row("stated", 0.9, id="s1"), _row("stated", 0.89, id="s2"),
            _row("self_portrait", 0.88, id="p1"), _row("self_portrait", 0.87, id="p2")]
    rows += [_row(t, 0.99 - i / 100, id=f"x{i}")
             for i, t in enumerate(("pattern", "belief", "value", "struggle",
                                    "milestone", "counterview_belief"))]

    out = compose_recall(rows)
    standing = [r for r in out if r.entry_type in STANDING_TYPES]

    assert len(standing) == STANDING_CAP          # not 4
    assert len(out) == RECALL_TOTAL_BUDGET        # 3 + 5, Lane B fills its own cap


def test_the_total_budget_is_never_exceeded():
    rows = [_row(t, 0.9, id=f"{t}{i}")
            for t in ("stated", "self_portrait", "belief", "value", "struggle",
                      "pattern", "milestone", "counterview_belief")
            for i in range(3)]

    assert len(compose_recall(rows)) <= RECALL_TOTAL_BUDGET


def test_a_smaller_total_budget_is_honoured():
    """top_k is the total across both lanes; a caller asking for less gets less."""
    rows = [_row("stated", 0.9, id="s"), _row("pattern", 0.99, id="p"),
            _row("belief", 0.98, id="b")]

    assert len(compose_recall(rows, total_budget=2)) == 2


def test_a_small_budget_clamps_lane_a_too():
    """THE BUDGET IS THE TOTAL, LANE A INCLUDED. Clamping only Lane B would let a
    surplus of standing rows overshoot: Lane B's room floors at 0 while Lane A has
    already taken more slots than were asked for, and the caller gets back more
    rows than its top_k.

    Latent rather than live — no caller passes a small top_k since PR-2 — but the
    function's contract says total, so it has to be total.

    Lane A still WINS those slots: standing leads, so a budget of 2 against four
    standing rows and a strong inferred row yields two standing rows and nothing
    else."""
    rows = [_row("stated", 0.90, id="s1"), _row("stated", 0.89, id="s2"),
            _row("self_portrait", 0.88, id="p1"), _row("self_portrait", 0.87, id="p2"),
            _row("pattern", 0.99, id="x")]

    out = compose_recall(rows, total_budget=2)

    assert len(out) == 2
    assert all(r.entry_type in STANDING_TYPES for r in out)


# ── Ordering ─────────────────────────────────────────────────────────────────

def test_standing_leads_then_inferred_by_descending_score():
    """Lane A first — it is the stable frame the persona reads the topical matches
    against — and Lane B by relevance within it. Note the inferred rows here
    outscore the standing ones, and STILL follow them."""
    rows = [_row("pattern", 0.99, content="high"),
            _row("belief", 0.80, content="low"),
            _row("stated", 0.40, content="standing")]

    assert _contents(compose_recall(rows)) == ["standing", "high", "low"]


def test_ties_break_on_recency_then_id_so_the_block_is_reproducible():
    """A prompt that reorders between two identical turns is untestable, and it
    churns text that sits after the cache breakpoint for nothing. Equal scores →
    newer first; equal scores AND equal timestamps → id ascending."""
    rows = [
        _row("belief", 0.90, id="zzz", age_minutes=0, content="new-zzz"),
        _row("value", 0.90, id="aaa", age_minutes=0, content="new-aaa"),
        _row("struggle", 0.90, id="mmm", age_minutes=60, content="old-mmm"),
    ]

    assert _contents(compose_recall(rows)) == ["new-aaa", "new-zzz", "old-mmm"]


def test_the_same_rows_in_any_input_order_compose_identically():
    """Determinism is a property of the ROWS, not of the order the query happened
    to return them in."""
    rows = [_row("stated", 0.5, id="s"), _row("pattern", 0.99, id="p"),
            _row("belief", 0.98, id="b"), _row("self_portrait", 0.4, id="sp")]

    assert _contents(compose_recall(rows)) == _contents(compose_recall(list(reversed(rows))))


# ── Degenerate inputs ────────────────────────────────────────────────────────

def test_no_rows_composes_to_no_rows():
    assert compose_recall([]) == []


def test_everything_below_the_floor_leaves_only_standing():
    rows = [_row("belief", 0.10), _row("pattern", 0.20), _row("stated", 0.01)]

    assert _types(compose_recall(rows)) == ["stated"]
