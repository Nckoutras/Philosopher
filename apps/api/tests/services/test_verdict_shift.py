"""MEM2-B2 — the pure half of verdict reversal: the template, the 72h guard, and
which 'no' anchors it.

The live half (the handler's transaction, reactivation, the task's row) is in
tests/db_live/test_verdict_shift_live.py. These are pure functions, so their
boundaries are pinned here exactly, without a clock.
"""
from datetime import datetime, timedelta, timezone

from services.memory_service import (
    STANDING_TYPES,
    VERDICT_SHIFT_GUARD,
    VERDICT_SHIFT_TYPE,
    shift_anchor,
    verdict_entry,
    verdict_shift_days,
    verdict_shift_statement,
)

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _h(verdict, at):
    return verdict_entry(verdict, at)


# ── The template (founder-approved text, 2026-10-03) ─────────────────────────

def test_the_template_is_the_approved_text_exactly():
    # Written out, not derived: an expectation computed from the function under
    # test could not fail.
    assert verdict_shift_statement("You keep returning to the same decision.", 12) == (
        "They came to accept, after 12 days, an observation they had first "
        "rejected: “You keep returning to the same decision.”"
    )


def test_the_insight_is_quoted_verbatim_apart_from_outer_whitespace():
    out = verdict_shift_statement("  Η ίδια απόφαση επιστρέφει.\n", 3)
    assert out.endswith("“Η ίδια απόφαση επιστρέφει.”")


def test_empty_content_writes_nothing():
    assert verdict_shift_statement("", 5) is None
    assert verdict_shift_statement("   ", 5) is None
    assert verdict_shift_statement(None, 5) is None


def test_the_shift_type_is_lane_b_by_the_catch_all():
    assert VERDICT_SHIFT_TYPE == "insight_verdict_shift"
    assert VERDICT_SHIFT_TYPE not in STANDING_TYPES


# ── The 72h guard ────────────────────────────────────────────────────────────

def test_the_guard_is_72_hours():
    assert VERDICT_SHIFT_GUARD == timedelta(hours=72)


def test_exactly_72h_writes_and_reads_as_3_days():
    assert verdict_shift_days(T0, T0 + timedelta(hours=72)) == 3


def test_one_microsecond_under_72h_does_not():
    assert verdict_shift_days(T0, T0 + timedelta(hours=72) - timedelta(microseconds=1)) is None


def test_days_are_whole_days_rounded_down():
    assert verdict_shift_days(T0, T0 + timedelta(hours=95, minutes=59)) == 3
    assert verdict_shift_days(T0, T0 + timedelta(hours=96)) == 4


def test_no_anchor_means_no_shift():
    assert verdict_shift_days(None, T0) is None


# ── Which 'no' anchors the guard ─────────────────────────────────────────────

def test_the_latest_no_in_history_anchors():
    history = [_h("no", T0 - timedelta(days=9)), _h("no", T0)]
    assert shift_anchor(history, "no", T0) == T0


def test_partly_is_passed_over_so_the_no_before_it_anchors():
    """no → partly → yes: the 'no' anchors (ruling 4, 2026-10-03)."""
    history = [_h("no", T0), _h("partly", T0 + timedelta(days=1))]
    assert shift_anchor(history, "partly", T0 + timedelta(days=1)) == T0


def test_a_yes_after_the_no_ends_the_search():
    """yes → yes is not a change of mind, even with an old 'no' further back."""
    history = [_h("no", T0), _h("yes", T0 + timedelta(days=4))]
    assert shift_anchor(history, "yes", T0 + timedelta(days=4)) is None


def test_legacy_insight_falls_back_to_ring_true_at_when_the_loaded_verdict_is_no():
    assert shift_anchor(None, "no", T0) == T0
    assert shift_anchor([], "no", T0) == T0


def test_the_fallback_needs_the_loaded_verdict_to_be_no():
    assert shift_anchor([], "partly", T0) is None
    assert shift_anchor([], "yes", T0) is None
    assert shift_anchor([], None, None) is None


def test_a_naive_fallback_timestamp_is_read_as_utc():
    naive = datetime(2026, 10, 1, 12, 0)
    assert shift_anchor([], "no", naive) == T0


def test_an_unreadable_no_produces_no_shift():
    """A history 'no' whose time cannot be read must not fall through to an older
    'no' or to the fallback: that would anchor on the wrong verdict."""
    history = [_h("no", T0 - timedelta(days=30)), {"verdict": "no", "at": "not-a-time"}]
    assert shift_anchor(history, "no", T0) is None


def test_history_entries_are_utc_iso_with_a_z():
    assert verdict_entry("no", T0) == {"verdict": "no", "at": "2026-10-01T12:00:00Z"}
