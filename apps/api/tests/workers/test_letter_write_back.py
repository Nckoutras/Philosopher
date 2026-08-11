"""Tests for the reader write-back carry-forward block (A12).

Covers _build_wrote_back_block — the pure renderer for write-backs the CURRENT
letter voice did not receive, which must reach whoever writes next, attributed.

NOT covered here, and NOT covered anywhere: the 14-day cutoff and the
already-fetched-ID deduplication both live in the SQL query inside
generate_weekly_letter_task / generate_monthly_letter_task. No letter-generation
test harness exists in this repo (nothing imports arq_worker's tasks or either
prompt), and none was invented for this PR.

Run: cd apps/api && pytest tests/workers/test_letter_write_back.py -v
"""
from unittest.mock import MagicMock

from workers.arq_worker import (
    _build_wrote_back_block,
    WRITE_BACK_WINDOW_DAYS,
    WRITE_BACK_MAX_CARRIED,
)


def _row(text, persona_name):
    """One (WeeklyLetter, persona_name) pair as the query returns it."""
    letter = MagicMock()
    letter.write_back_text = text
    return (letter, persona_name)


def test_attribution_is_present_when_the_voice_is_known():
    """The whole point of the block: the new voice is told WHO the words were
    written to, so it cannot read them as a message addressed to itself."""
    block = _build_wrote_back_block([_row("I have been avoiding it.", "Oscar Wilde")])

    assert '<reader_wrote_back to="Oscar Wilde">' in block
    assert "I have been avoiding it." in block
    assert block.startswith("<reader_wrote_back_recently>\n")
    assert block.endswith("</reader_wrote_back_recently>\n\n")


def test_no_rows_returns_empty_string():
    """The caller concatenates unconditionally, so 'nothing to carry' must be ''
    and not a stray empty wrapper."""
    assert _build_wrote_back_block([]) == ""


def test_row_with_no_persona_name_is_skipped():
    """voice_persona_id is nullable and personas can be deleted. A nameless row
    would render to="" — words written to no one — so it is dropped instead."""
    assert _build_wrote_back_block([_row("something", None)]) == ""
    assert _build_wrote_back_block([_row("something", "   ")]) == ""


def test_row_with_blank_text_is_skipped():
    """Mirrors the existing bare-form guard: a whitespace-only write-back is not
    material and must not produce an empty tag."""
    assert _build_wrote_back_block([_row("   ", "Socrates")]) == ""
    assert _build_wrote_back_block([_row(None, "Socrates")]) == ""


def test_persona_name_is_escaped_in_the_attribute():
    """A name carrying a quote must not be able to break out of the tag."""
    block = _build_wrote_back_block([_row("her words", 'Ann "Nan" Shepherd')])

    assert 'to="Ann &quot;Nan&quot; Shepherd"' in block
    # The tag is still well formed: exactly one opening and one closing tag.
    assert block.count("<reader_wrote_back ") == 1
    assert block.count("</reader_wrote_back>") == 1


def test_caller_ordering_is_preserved():
    """The query orders newest-first; the renderer must not reorder, so the most
    recent words read first."""
    block = _build_wrote_back_block([
        _row("newer", "Oscar Wilde"),
        _row("older", "Socrates"),
    ])

    assert block.index("newer") < block.index("older")
    assert block.index('to="Oscar Wilde"') < block.index('to="Socrates"')


def test_skipped_rows_do_not_break_the_survivors():
    """A nameless row in the middle is dropped without disturbing the rest."""
    block = _build_wrote_back_block([
        _row("kept one", "Oscar Wilde"),
        _row("dropped", None),
        _row("kept two", "Socrates"),
    ])

    assert "kept one" in block and "kept two" in block
    assert "dropped" not in block
    assert block.count("</reader_wrote_back>") == 2


def test_the_bare_unattributed_form_is_never_produced_here():
    """The same-voice case stays in <prior_letters> in its existing bare form.
    This renderer only ever emits the attributed variant."""
    block = _build_wrote_back_block([_row("her words", "Oscar Wilde")])

    assert "<reader_wrote_back>" not in block


def test_window_and_cap_constants_are_the_agreed_values():
    """The 14-day window and the 2-note cap are product decisions, not incidental
    numbers: pin them so a change is deliberate."""
    assert WRITE_BACK_WINDOW_DAYS == 14
    assert WRITE_BACK_MAX_CARRIED == 2
