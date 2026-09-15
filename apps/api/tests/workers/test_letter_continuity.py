"""Γ-4a — the correspondence belongs to the reader, not to the voice.

WHAT CHANGED, AND WHAT THESE TESTS ARE FOR. The weekly letter's prior-letters
fetch used to filter on voice_persona_id, so "the last 3 letters" meant "the
last 3 from THIS persona". The weekly voice is re-elected every week from the
trailing conversation, so for a reader who alternates that was a chain with
holes in it, and for a reader who switched for good it was EMPTY — the letter
began again from nothing, weekly, and no code path could notice. The filter is
gone and the cap is 6.

THE HALF THAT IS EASY TO MISS, and half this file is about it. User-scoping the
fetch is not sufficient on its own — it is actively WRONG without attribution.
A write-back carried in <prior_letters> used to render BARE, which was correct
precisely because the fetch guaranteed the words had been written to the persona
now reading them. Once the fetch crosses voices, bare is a lie: the reader's
words to Wilde reach Jung with nothing marking them as another voice's, which is
exactly the confusion _build_wrote_back_block's to= form was built to prevent.
So test_a_cross_voice_write_back_is_attributed and its same-voice twin are the
regression guards for A12, not decoration on a new feature.

SPLIT ACROSS TWO FILES, DELIBERATELY. The RENDERER is pure and is tested here.
The QUERY — no voice filter, cap 6, ordering, the four surviving filters — is
tested in tests/db_live/test_letter_continuity.py against real Postgres, because
a mocked session returns whatever the test author invented and the query result
IS the behaviour. Both execute the same _prior_letters_stmt object; neither
rebuilds it.

REAL OBJECTS, NOT MagicMock (C-06). A MagicMock auto-creates `payload`, and
`payload.get('title')` then returns a Mock that formats into the line as
"<MagicMock id=...>" without raising — so a renderer that read the wrong field
would produce garbage and still pass. FakeLetter sets exactly the four
attributes the renderer reads and nothing else, so a fifth would raise.

Run: cd apps/api && pytest tests/workers/test_letter_continuity.py -v
"""
from datetime import datetime, timezone

import pytest

from workers.arq_worker import (
    PRIOR_LETTERS_MAX_CARRIED,
    _build_prior_letters_block,
)

WILDE = "11111111-1111-1111-1111-111111111111"
JUNG = "22222222-2222-2222-2222-222222222222"


class FakeLetter:
    """Exactly the four fields _build_prior_letters_block reads.

    Not a MagicMock, and not the SQLAlchemy model either: the renderer never
    touches the session, so a plain object states the contract more honestly
    than either — if the renderer starts reading a fifth field, this raises
    AttributeError instead of silently absorbing it.
    """

    def __init__(self, *, month_day, title, pull_quote,
                 write_back_text=None, practical_takeaway=None,
                 voice_persona_id=WILDE):
        self.period_start = datetime(2026, 9, month_day, tzinfo=timezone.utc)
        self.write_back_text = write_back_text
        self.voice_persona_id = voice_persona_id
        self.payload = {"title": title, "pull_quote": pull_quote,
                        "practical_takeaway": practical_takeaway}


def _row(name="Oscar Wilde", **kw):
    """One (WeeklyLetter, persona_name) pair as _prior_letters_stmt returns it."""
    return (FakeLetter(**kw), name)


def _plain(month_day, title, **kw):
    return _row(month_day=month_day, title=title, pull_quote="A line.", **kw)


# ── The header line (founder-approved format, 2026-09-15) ────────────────────

def test_the_header_line_carries_the_voice_that_wrote_it():
    """The approved format, verbatim: '[Sep 06 — Oscar Wilde] {title} — {pull}'.

    Pinned as a whole string rather than by its parts. This line is what the
    letter model is told about who said what, and it was approved as copy — a
    test that checked only "the name appears somewhere" would pass on a line
    that had been silently restructured.
    """
    block = _build_prior_letters_block(
        [_row(month_day=6, title="On the week you held still",
              pull_quote="You keep calling it patience.")],
        current_voice_persona_id=JUNG,
    )

    assert (
        "[Sep 06 — Oscar Wilde] On the week you held still — "
        "You keep calling it patience." in block
    )
    assert block.startswith("<prior_letters>\n")
    assert block.endswith("</prior_letters>\n\n")


def test_the_persona_is_named_even_on_its_own_letters():
    """ALWAYS-ATTRIBUTE (founder Decision 1). The alternative — a name only when
    the voice differs — makes ABSENCE of a name mean "you", which is a second
    rule the model has to infer. One rule, stated once, on every line.
    """
    block = _build_prior_letters_block(
        [_plain(6, "Mine", name="Carl Jung")], current_voice_persona_id=JUNG,
    )
    assert "[Sep 06 — Carl Jung] Mine — A line." in block


# ── Attribution on write-backs: the A12 regression guard ─────────────────────

def test_a_cross_voice_write_back_is_attributed():
    """THE REASON THIS PR IS NOT JUST A DELETED WHERE-CLAUSE.

    Words the reader wrote to Wilde now arrive in a letter Jung is writing. They
    must carry to="Oscar Wilde", or Jung reads them as a message addressed to
    itself — the exact failure _build_wrote_back_block exists to prevent, which
    user-scoping this fetch would otherwise have reintroduced one level up.
    """
    block = _build_prior_letters_block(
        [_plain(6, "Hers", write_back_text="I have been avoiding it.",
                voice_persona_id=WILDE)],
        current_voice_persona_id=JUNG,
    )

    assert '<reader_wrote_back to="Oscar Wilde">I have been avoiding it.' in block


def test_a_same_voice_write_back_stays_bare():
    """Unchanged, and byte-identical to before this PR.

    When the voice reading the block IS the voice that received the words, they
    were addressed to it, and a to= would be false in the other direction. This
    is also what keeps a single-voice reader's prompt exactly as it was.
    """
    block = _build_prior_letters_block(
        [_plain(6, "Hers", write_back_text="I have been avoiding it.",
                voice_persona_id=JUNG, name="Carl Jung")],
        current_voice_persona_id=JUNG,
    )

    assert "<reader_wrote_back>I have been avoiding it.</reader_wrote_back>" in block
    assert "to=" not in block


def test_the_attribution_is_escaped():
    """A persona name carrying a quote must not break out of the tag. Matches
    _build_wrote_back_block: the ATTRIBUTE is escaped, the body is not."""
    block = _build_prior_letters_block(
        [_plain(6, "Hers", write_back_text="her words",
                name='Ann "Nan" Shepherd')],
        current_voice_persona_id=JUNG,
    )

    assert '<reader_wrote_back to="Ann &quot;Nan&quot; Shepherd">' in block


# ── Decision 2: a missing voice name ─────────────────────────────────────────

def test_a_letter_with_no_voice_name_is_still_carried_but_bare():
    """voice_persona_id is nullable and a persona row can be deleted.

    The letter STAYS — dropping it would silently shorten the correspondence,
    which is the defect this whole change exists to fix — and its header falls
    back to the pre-Γ-4a bare form. Only the attribution that cannot be made
    honestly is withheld.
    """
    block = _build_prior_letters_block(
        [_plain(6, "Orphaned", name=None, voice_persona_id=None)],
        current_voice_persona_id=JUNG,
    )

    assert "[Sep 06] Orphaned — A line." in block
    assert "—" in block  # the title/pull separator survives


def test_a_nameless_letters_write_back_is_dropped_not_emitted_empty():
    """An empty to="" would read as words written to no one.

    _build_wrote_back_block refuses that same case for the same reason; this is
    the one place the two renderers could have diverged, so it is pinned on both
    sides. The letter's title and pull-quote still carry.
    """
    block = _build_prior_letters_block(
        [_plain(6, "Orphaned", name=None, voice_persona_id=None,
                write_back_text="words into the dark")],
        current_voice_persona_id=JUNG,
    )

    assert "Orphaned" in block
    assert "words into the dark" not in block
    assert 'to=""' not in block


# ── Ordering, shape, degenerate input ────────────────────────────────────────

def test_the_block_reads_oldest_first_while_the_query_returns_newest_first():
    """The query orders period_start DESC; the prompt must read forward in time.

    The reversal lived in the inline loop this renderer replaced and is easy to
    lose in an extraction — which would hand the model a correspondence running
    backwards, with no error and no visible symptom.
    """
    block = _build_prior_letters_block(
        [_plain(20, "Third"), _plain(13, "Second"), _plain(6, "First")],
        current_voice_persona_id=JUNG,
    )

    assert block.index("First") < block.index("Second") < block.index("Third")


def test_three_voices_all_render():
    """The ruling's core claim, at the renderer: a reader who rotated across
    three personas gets all three, each named."""
    block = _build_prior_letters_block(
        [_plain(20, "C", name="Epictetus"),
         _plain(13, "B", name="Carl Jung"),
         _plain(6, "A", name="Oscar Wilde")],
        current_voice_persona_id=JUNG,
    )

    for name in ("Oscar Wilde", "Carl Jung", "Epictetus"):
        assert f"— {name}]" in block


def test_the_prior_suggestion_still_carries():
    """Feed-forward (B) is unchanged in FORM by this PR — only its ownership
    moved, and LETTER_PROMPT carries that. The tag must not have drifted."""
    block = _build_prior_letters_block(
        [_plain(6, "Hers", practical_takeaway="Pause before you call it unfair.")],
        current_voice_persona_id=JUNG,
    )

    assert "<prior_suggestion>Pause before you call it unfair.</prior_suggestion>" in block


@pytest.mark.parametrize("value", [None, "", "   "])
def test_blank_write_backs_and_suggestions_emit_nothing(value):
    """Empty tags are noise in a prompt that insists the week stays dominant."""
    block = _build_prior_letters_block(
        [_plain(6, "Hers", write_back_text=value, practical_takeaway=value)],
        current_voice_persona_id=JUNG,
    )

    assert "<reader_wrote_back" not in block
    assert "<prior_suggestion>" not in block


def test_no_rows_returns_empty_string():
    """The caller concatenates unconditionally, so 'nothing to carry' must be ''
    and not a stray empty wrapper."""
    assert _build_prior_letters_block([], current_voice_persona_id=JUNG) == ""


def test_the_cap_is_six():
    """Pinned as a number, not as an inequality.

    6 was chosen against a measurement (see PRIOR_LETTERS_MAX_CARRIED): the
    realistic block is ~452 tokens at 6, and the constraint is the TAIL — six
    write-backs at the 2,000-character cap render ~2,956. A silent bump to 10
    would roughly double that against a prompt whose every paragraph insists the
    week's own messages stay dominant.
    """
    assert PRIOR_LETTERS_MAX_CARRIED == 6


# ── The size budget ──────────────────────────────────────────────────────────

# A representative carried letter: an 8-word title, a one-sentence pull-quote and
# a one-sentence suggestion, all at the length LETTER_PROMPT asks for. Written out
# rather than generated, so the budget below measures prose of the shape this
# block actually carries.
_TITLE = "On the week you held still"
_PULL = ("You keep calling it patience, but patience is a thing you choose, "
         "and this has been happening to you.")
_TAKEAWAY = ("This week, when something stings, pause before you call it "
             "'unfair' — and notice how long the pause has to be.")
_WRITE_BACK = ("I read this on Monday and it landed. The bit about my father "
               "was uncomfortable and right.")

# Characters, NOT tokens, and that is a deliberate choice rather than laziness.
# tiktoken downloads its BPE table on first use, so a token assertion would make
# this test depend on the RUNNER having network — the exact shape of the failure
# #578 had to remove from test_the_theme_eyebrow_is_renderable, where an
# assertion measured the machine instead of the product and was green on the one
# it was written on. Characters are deterministic everywhere.
#
# The conversion, measured out of band on 2026-09-15 with cl100k_base (a proxy
# for Anthropic's tokenizer, close enough for a budget and not for a bill):
#   6 letters, no write-backs   1,849 chars   ~452 tokens
#   6 letters, 2 write-backs    2,139 chars   ~521 tokens
#   6 letters, 6 write-backs    2,728 chars   ~664 tokens
# against a system prompt of 10,483 chars / ~2,321 tokens.
FULL_BLOCK_CHAR_BUDGET = 3_000


def _representative_rows(n, with_write_backs=0):
    return [
        (FakeLetter(month_day=1 + i, title=_TITLE, pull_quote=_PULL,
                    practical_takeaway=_TAKEAWAY,
                    write_back_text=_WRITE_BACK if i < with_write_backs else None,
                    voice_persona_id=f"voice-{i}"),
         f"Persona Number {i}")
        for i in range(n)
    ]


def test_a_full_block_stays_inside_its_budget():
    """SIX LETTERS, EVERY ONE WITH A WRITE-BACK AND A SUGGESTION — the realistic
    worst case — must stay well under the week's own messages.

    This is the guard on the number, not on the prose. The two edits that would
    blow it are raising PRIOR_LETTERS_MAX_CARRIED and adding a fourth carried
    field per letter, and both are exactly the kind of change that looks free in
    a diff. <week> is unbounded and dominates by design; every prompt in this
    file insists it stay dominant, and a continuity block that grew past a
    quarter of the system prompt would start competing with it.
    """
    block = _build_prior_letters_block(
        _representative_rows(PRIOR_LETTERS_MAX_CARRIED, with_write_backs=6),
        current_voice_persona_id="someone-else",
    )

    assert len(block) < FULL_BLOCK_CHAR_BUDGET, (
        f"the carried correspondence is {len(block)} chars, over the "
        f"{FULL_BLOCK_CHAR_BUDGET} budget. If this is intended, move the budget "
        f"and record the new measurement — do not widen it silently."
    )


def test_the_tail_is_known_and_accepted():
    """WRITE-BACKS AT THEIR 2,000-CHARACTER CAP ARE THE REAL TAIL, and it is
    recorded here rather than guarded, because no truncation shipped.

    schemas.WriteBackIn caps a write-back at 2,000 characters, so six carried
    letters can in principle render ~14,000 characters (~2,956 tokens) — larger
    than the system prompt. Founder ruling 2026-09-15: not truncated, because no
    reader has yet written back at all and a truncation length would be invented
    rather than measured. The lever, when it is needed, is truncating in the
    renderer — NOT lowering the cap, which would cost the common case to fix a
    rare one.

    This test exists so that tail is a number someone chose and can find again,
    instead of a surprise in a token bill.
    """
    block = _build_prior_letters_block(
        [(FakeLetter(month_day=1 + i, title=_TITLE, pull_quote=_PULL,
                     write_back_text="word " * 400, voice_persona_id=f"v{i}"),
          f"Persona {i}")
         for i in range(PRIOR_LETTERS_MAX_CARRIED)],
        current_voice_persona_id="someone-else",
    )

    assert 12_000 < len(block) < 16_000
