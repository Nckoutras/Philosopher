"""Tests for the letter generators' pure helpers (A12 write-back block, A17 parse).

Covers _build_wrote_back_block — the pure renderer for write-backs the CURRENT
letter voice did not receive, which must reach whoever writes next, attributed.

NOT covered here, and NOT covered anywhere: the 14-day cutoff and the
already-fetched-ID deduplication both live in the SQL query inside
generate_weekly_letter_task / generate_monthly_letter_task. No letter-generation
test harness exists in this repo (nothing imports arq_worker's tasks or either
prompt), and none was invented for this PR.

Run: cd apps/api && pytest tests/workers/test_letter_write_back.py -v
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from workers.arq_worker import (
    _build_wrote_back_block,
    _parse_letter_payload,
    JSON_RETRY_DIRECTIVE,
    WRITE_BACK_WINDOW_DAYS_WEEKLY,
    WRITE_BACK_WINDOW_DAYS_MONTHLY,
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
    """The windows and the 2-note cap are product decisions, not incidental numbers:
    pin them so a change is deliberate.

    A14 split one shared 14-day window into one per cadence. The single window
    expired before the next season letter existed — the monthly cron fires on the
    last calendar day of the month, so a reader who answered promptly, early in the
    month, was silently dropped. The pin stays so the NEXT change is deliberate too.
    """
    assert WRITE_BACK_WINDOW_DAYS_WEEKLY == 14
    assert WRITE_BACK_WINDOW_DAYS_MONTHLY == 45
    assert WRITE_BACK_MAX_CARRIED == 2


# ── A14: the windows must match their cadences ────────────────────────────────
#
# These assert the cutoff ARITHMETIC over the constants, which is the property the
# fix is about. They do NOT prove each query reads the right constant — that pairing
# lives in the SQL inside generate_weekly_letter_task / generate_monthly_letter_task
# and, with no letter-generation harness in this repo, is reviewable only in the diff.

def _is_live(written_days_ago: int, window_days: int) -> bool:
    """Reproduce the generators' cutoff test: write_back_at >= now - window."""
    now = datetime.now(timezone.utc)
    written_at = now - timedelta(days=written_days_ago)
    cutoff = now - timedelta(days=window_days)
    return written_at >= cutoff


def test_monthly_write_back_written_30_days_ago_is_still_live():
    """The defect in one line: season letters are ~30 days apart, so a write-back
    from a month ago must still reach the next one."""
    assert _is_live(30, WRITE_BACK_WINDOW_DAYS_MONTHLY) is True


def test_weekly_write_back_written_30_days_ago_has_aged_out():
    """The weekly cadence is 7 days; a month-old note is stale there and must not
    be carried. The monthly widening must not leak into the weekly path."""
    assert _is_live(30, WRITE_BACK_WINDOW_DAYS_WEEKLY) is False


def test_monthly_window_covers_a_day_one_write_back_in_the_longest_month():
    """A season letter fires on the last calendar day. Answered on day 1 of a 31-day
    month, the note is 30 days old when the next letter is generated 31 days later —
    61 days is beyond any window, but the note only needs to survive to the NEXT
    letter, 30 days out. 45 gives headroom over the longest month without keeping a
    note alive across two seasons (which would need > 62)."""
    assert WRITE_BACK_WINDOW_DAYS_MONTHLY > 31
    assert WRITE_BACK_WINDOW_DAYS_MONTHLY < 62


# ── A17: the payload parse must fail as a branch, never as an exception ───────
#
# The 2026-08-09 incident: generate_weekly_letter_task ran 14.8s, the LLM produced
# the letter, and json.loads raised on an unescaped quote mid-string. The raise
# unwound past the row-writing code into the outer `except Exception`, which logged
# and swallowed — no row, no retry, arq j_failed=0, letter gone. These pin the
# helper that turns that raise into a None the caller can handle.
#
# NOT covered here: the retry loop and the 'failed' row inside the two generators.
# Reaching them means driving a task that opens a session, runs ~8 queries and calls
# the LLM — i.e. the letter-generation harness this repo deliberately does not have.
# That behaviour is reviewable in the diff only.

def test_valid_json_parses_to_a_dict():
    """The ordinary path — unchanged behaviour, pinned so the refactor is honest."""
    assert _parse_letter_payload('{"status": "generated", "title": "A Quiet Turn"}') == {
        "status": "generated",
        "title": "A Quiet Turn",
    }


def test_valid_json_wrapped_in_code_fences_parses():
    """The model routinely fences its reply. The fence-strip is carried over verbatim
    from the two call sites this helper replaced — losing it would break every letter,
    not just the malformed ones."""
    fenced = '```json\n{"status": "generated", "title": "Fenced"}\n```'
    assert _parse_letter_payload(fenced) == {"status": "generated", "title": "Fenced"}


def test_the_incident_shape_returns_none_instead_of_raising():
    """THE regression guard. An unescaped quote mid-string is exactly what broke
    production: json.loads raises "Expecting ',' delimiter". The helper must return
    None so the caller can retry and, failing that, write the loss down."""
    incident = '{"status": "generated", "title": "She said "no" and meant it"}'

    assert _parse_letter_payload(incident) is None


def test_truncated_json_returns_none_instead_of_raising():
    """The other failure mode, and the one the monthly generator's max_tokens comment
    already anticipated: a reply cut off mid-object."""
    truncated = '{"status": "generated", "title": "A Quiet Turn", "body": "It began'

    assert _parse_letter_payload(truncated) is None


def test_the_retry_directive_names_the_actual_failure():
    """The directive is appended to the user message on the retry only — prompts are
    untouched. Pin its substance: it must name JSON, name quote escaping (the observed
    cause), and forbid the fences and prose that would fail the parse a second time."""
    assert "not valid JSON" in JSON_RETRY_DIRECTIVE
    assert "escaping" in JSON_RETRY_DIRECTIVE
    assert "No prose, no code fences." in JSON_RETRY_DIRECTIVE
