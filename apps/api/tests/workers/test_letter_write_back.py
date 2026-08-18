"""Tests for the letter generators' pure helpers (A12 write-back, A17 parse, A18 rituals).

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
    _is_null_reply,
    _build_rituals_block,
    RITUALS_MAX_ENTRIES,
    RITUALS_MAX_ENTRY_CHARS,
    RITUALS_MAX_BLOCK_CHARS,
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


# ── A18: the week is more than chat ───────────────────────────────────────────
#
# The 2026-08-16 dispatch enqueued ZERO letters. The one active user had spent the
# week entirely in rituals and sent no chat messages, so a week of 1 council, 3
# rebuttals, 2 mirror notes and a you-vs-you classified as quiet. These pin the
# renderer for the block that carries that week into the letter.
#
# HER WORDS ONLY is a property of what the CALLER selects (input_text, user_text,
# ring_true_note, prompt — never synthesis, persona_response or verdict), so it lives
# in _fetch_ritual_entries and is reviewable in the diff, not here.
#
# NOT covered here: the four queries, the eligibility merge in cron, the quiet-week
# gate, and the per-entry safety filter. All need a session and a live safety_service
# — the letter-generation harness this repo deliberately does not have.

def _r(kind, day, text):
    """One (kind, occurred_at, text) tuple as _fetch_ritual_entries returns it."""
    return (kind, datetime(2026, 8, day, 12, 0, tzinfo=timezone.utc), text)


def test_the_incident_week_renders_all_four_surfaces():
    """THE regression guard: the exact 2026-08-16 shape — 1 council, 3 counterview
    rebuttals, 2 mirror notes, 1 you-vs-you — the week that produced no letter."""
    block = _build_rituals_block([
        _r("council", 12, "Whether to take the job in Berlin"),
        _r("counterview", 13, "I still think loyalty is worth the cost"),
        _r("counterview", 13, "But that assumes I owe them something"),
        _r("counterview", 13, "Maybe the debt is imagined"),
        _r("mirror", 14, "This landed harder than I expected"),
        _r("mirror", 14, "I keep returning to the same week in March"),
        _r("you_vs_you", 15, "Am I steadier than I was in spring?"),
    ])

    assert block.startswith("<rituals>\n")
    assert block.endswith("</rituals>\n\n")
    assert "brought before the council" in block
    assert "pushed back in counterview" in block
    assert "noted at the mirror" in block
    assert "asked of themselves" in block
    # Every one of the seven acts survives — none is collapsed or deduplicated.
    assert block.count("[") == 7


def test_no_ritual_rows_returns_empty_string():
    """The caller concatenates the block unconditionally, so 'no rituals this week'
    must be '' and never an empty wrapper the voice would try to interpret."""
    assert _build_rituals_block([]) == ""


def test_entries_with_blank_or_missing_text_are_skipped():
    """ring_true_note is nullable and a matter can be whitespace. An empty entry would
    render a label with nothing after it — a day the voice would read as meaningful."""
    assert _build_rituals_block([_r("mirror", 12, None)]) == ""
    assert _build_rituals_block([_r("mirror", 12, "   ")]) == ""


def test_unknown_kind_is_skipped_rather_than_rendered_unlabelled():
    """A future surface added to the fetcher but not to _RITUAL_LABELS must not leak
    in without a label — an unlabelled line tells the voice nothing about what it is."""
    assert _build_rituals_block([_r("seance", 12, "words")]) == ""


def test_caller_ordering_is_preserved_oldest_first():
    """The fetcher selects newest-first then reverses, so the block reads forward
    through the week. A reordering here would scramble the week's shape."""
    block = _build_rituals_block([
        _r("council", 12, "earlier thing"),
        _r("mirror", 15, "later thing"),
    ])

    assert block.index("earlier thing") < block.index("later thing")


def test_a_long_entry_is_truncated_not_dropped():
    """A council matter runs to 600 chars. Truncating keeps the week's shape intact;
    dropping would silently lose the act entirely."""
    long_text = "x" * (RITUALS_MAX_ENTRY_CHARS + 200)
    block = _build_rituals_block([_r("council", 12, long_text)])

    assert "brought before the council" in block
    assert "…" in block
    assert len(block) < RITUALS_MAX_ENTRY_CHARS + 200


def test_entry_count_is_capped():
    """Defensive: the fetcher already cuts to RITUALS_MAX_ENTRIES, but the renderer
    re-applies it so the block cannot grow past what the week's messages compete with."""
    rows = [_r("mirror", 12, "note {}".format(i)) for i in range(RITUALS_MAX_ENTRIES + 8)]
    block = _build_rituals_block(rows)

    assert block.count("[") == RITUALS_MAX_ENTRIES


def test_character_budget_drops_the_oldest_not_the_newest():
    """When the budget runs out the WEEK'S END must survive: what she did on Saturday
    is more use to a letter written on Sunday than what she did on Monday."""
    big = "y" * RITUALS_MAX_ENTRY_CHARS
    rows = [_r("council", 10 + i, "{} {}".format(i, big)) for i in range(RITUALS_MAX_ENTRIES)]
    block = _build_rituals_block(rows)

    assert len(block) <= RITUALS_MAX_BLOCK_CHARS + len("<rituals>\n</rituals>\n\n") + RITUALS_MAX_ENTRY_CHARS
    # The newest entry is kept; the oldest is the one sacrificed.
    assert block.count("[") < RITUALS_MAX_ENTRIES
    assert "{} ".format(RITUALS_MAX_ENTRIES - 1) in block
    assert not block.startswith("<rituals>\n[Mon Aug 10")


def test_label_text_is_exactly_the_approved_wording():
    """The four labels are approved input format, not incidental strings — the voice is
    told what she was doing so it can interpret a council matter differently from a
    mirror note. Pin them so a reword is deliberate."""
    block = _build_rituals_block([
        _r("council", 12, "a"), _r("counterview", 12, "b"),
        _r("mirror", 12, "c"), _r("you_vs_you", 12, "d"),
    ])

    assert "· brought before the council]" in block
    assert "· pushed back in counterview]" in block
    assert "· noted at the mirror]" in block
    assert "· asked of themselves]" in block


# ── A17b: the same net over mirror and insight ────────────────────────────────
#
# A17's enumeration found the identical silent-loss shape at two more sites. The
# mirror one matters twice over since A18: a lost mirror costs the mirror AND one of
# the four ritual sources feeding the weekly letter, on the same weekly cron.
#
# The one behaviour A17b could plausibly BREAK is the insight null sentinel.
# INSIGHT_PROMPT asks for bare `null` when nothing is worth surfacing — a valid,
# probably common outcome. json.loads("null") returns None, the same value
# _parse_letter_payload returns on a parse FAILURE, so the two are indistinguishable
# downstream and must be told apart from the raw reply before any retry decision.
#
# NOT covered here: the retry loops and the no-row failure paths inside the three
# tasks. Same limit as A17 — they need a session and a live LLM.

def test_null_reply_is_recognised_in_its_bare_form():
    """The form INSIGHT_PROMPT actually asks for. If this ever returns False, every
    quiet day becomes a wasted retry and a spurious FAILED log."""
    assert _is_null_reply("null") is True
    assert _is_null_reply("  null  ") is True
    assert _is_null_reply("NULL") is True


def test_null_reply_is_recognised_when_fenced():
    """The strict `== "null"` sentinel at the call site misses a fenced null; this is
    why the check is fence-tolerant. A fenced null is still the model declining, not a
    malformed payload."""
    assert _is_null_reply("```json\nnull\n```") is True
    assert _is_null_reply("```\nnull\n```") is True


def test_real_payloads_are_not_mistaken_for_null():
    """The other direction, and the more dangerous one: treating a real insight as
    'nothing here' would silently discard it."""
    assert _is_null_reply('{"content": "You circle the same question."}') is False
    assert _is_null_reply("```json\n{\"content\": \"x\"}\n```") is False
    assert _is_null_reply("") is False
    assert _is_null_reply("nullify the assumption") is False


def test_a_null_payload_parses_to_none_which_is_why_the_guard_exists():
    """Pins the collision itself. json.loads("null") SUCCEEDS and yields None — the
    exact value the helper returns on failure. This test is the reason _is_null_reply
    exists at all; if json ever stopped doing this the guard could be simplified."""
    assert _parse_letter_payload("null") is None
    assert _parse_letter_payload("{ broken") is None
    # Indistinguishable by return value alone — only the raw reply separates them.
    assert _is_null_reply("null") is True
    assert _is_null_reply("{ broken") is False


def test_label_threads_into_the_warning_line(caplog):
    """The label is the only reason the helper gained an argument: three tasks now
    share it, and a parse warning that does not say which one is nearly useless."""
    with caplog.at_level("WARNING", logger="workers.arq_worker"):
        assert _parse_letter_payload("{ broken", label="Mirror") is None
    assert any("Mirror payload parse failed" in r.message for r in caplog.records)


def test_label_defaults_to_letter_so_a17_behaviour_is_unchanged(caplog):
    """The default keeps the four letter call sites byte-identical — they pass no
    label and must still log exactly what they logged before A17b."""
    with caplog.at_level("WARNING", logger="workers.arq_worker"):
        assert _parse_letter_payload("{ broken") is None
    assert any("Letter payload parse failed" in r.message for r in caplog.records)
