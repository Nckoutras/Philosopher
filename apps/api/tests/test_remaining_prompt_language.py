# -*- coding: utf-8 -*-
"""The language the last seven generators write in, and what happens when they miss.

#626 fixed the council display brief and named the rest of the class. #627/#628
took the memory writers and the self-portrait summary. THIS IS THE REST OF THE
LIST it named, minus one entry that turned out not to exist:

  counterview (x3)   COUNTERVIEW_PROMPT told the model to use the "same language
                     as the person's position" for the title — inference, the
                     exact construct #626 removed from the council prompt. That
                     line is deleted here. DEEPER_PROMPT and RESPOND_PROMPT said
                     nothing at all.
  insight mirror     said nothing.
  you-vs-you (x3)    SELF_SYSTEM_PROMPT, CLOSING_PROMPT and
                     FORMING_REFLECTION_PROMPT said nothing.
  quote suggest      #626 listed it. IT HAS NO PROMPT: services/quote_suggest.py
                     is 67 lines of theme ranking with no LLM call and no I/O at
                     all. Nothing to fix, and recorded here so the enumeration is
                     not carried forward a fourth time (CLAUDE.md, 2026-08-18).

WHERE THE LANGUAGE COMES FROM, and why it is not always the obvious field.
insight.content is NOT a source. #628 enforces language on dilemma-typed insights
ONLY (VERBATIM_INPUT_SIGNAL_TYPES); belief- and aspiration-typed ones are
log-only and may already be wrong. Both insight-seeded generators here read the
source conversation's user messages instead — rows the safety gate has already
loaded, so no new query — and a test below proves a Greek conversation beats an
English thread rather than the other way round.

THE OUT LAYER, per prompt, matching what the caller can actually do about it:

  counterview / deeper / rebuttal / mirror / closing / forming   BLOCK. Every one
      has a first-class empty path the frontend already draws. Two of them are
      PERMANENT (the insight-seeded pair dedup on insight_id and never
      regenerate) and that is the accepted trade: 'generated' persists too, so a
      wrong-language card is stored once and re-served by that same dedup
      forever.
  the two selves   LOG. Not a ruling that could have gone either way: the answer
      is streamed chunk-by-chunk to the client, so there is no moment at which a
      guard could intervene. The directive is the whole protection there.

Run: cd apps/api && pytest tests/test_remaining_prompt_language.py -v
"""
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.counterview_service as cs
import services.insight_mirror_service as ims
import services.self_comparison_service as scs
from services.counterview_service import (
    COUNTERVIEW_PROMPT,
    DEEPER_PROMPT,
    RESPOND_PROMPT,
    generate_counterview,
    generate_deeper,
    respond_to_rebuttal,
)
from services.insight_mirror_service import INSIGHT_MIRROR_PROMPT, generate_insight_mirror
from services.self_comparison_prompts import (
    CLOSING_PROMPT,
    FORMING_REFLECTION_PROMPT,
    SELF_SYSTEM_PROMPT,
)
from text_utils import (
    EN_MIN_TOKENS,
    english_function_word_ratio,
    language_matches,
)

USER_ID = "11111111-1111-1111-1111-111111111111"
INSIGHT_ID = "22222222-2222-2222-2222-222222222222"
CONV_ID = "33333333-3333-3333-3333-333333333333"
CV_ID = "44444444-4444-4444-4444-444444444444"
PERSONA = "miyamoto_musashi"

GREEK_BELIEF = (
    "Πιστεύω ότι πρέπει να περιμένω λίγο ακόμα πριν αφήσω τη δουλειά μου, "
    "γιατί δεν είναι η σωστή στιγμή."
)
ENGLISH_BELIEF = (
    "I believe I should wait a while longer before leaving my job, because this "
    "is not the right moment."
)
GREEK_VERDICT_1 = "Η αναμονή ντυμένη υπομονή κοστίζει περισσότερο απ ό,τι νομίζεις."
GREEK_VERDICT_2 = "Η βολική ιστορία προστατεύει εσένα, όχι εκείνους που αγαπάς."
EN_VERDICT_1 = "Drift dressed as patience costs more than a wrong choice."
EN_VERDICT_2 = "You call it loyalty; it keeps you from deciding."
ID_VERDICT_1 = "Menunggu bukan kesabaran ketika biayanya terus bertambah setiap bulan."
ID_VERDICT_2 = "Kamu menyebutnya kesetiaan, padahal itu menahanmu dari memutuskan sekarang."


def _cv_payload(v1, v2, still=None, title=None):
    return json.dumps({
        "status": "generated",
        "verdicts": [
            {"persona": "miyamoto_musashi", "verdict": v1},
            {"persona": "niccolo_machiavelli", "verdict": v2},
        ],
        "still_stands": still,
        "title": title,
    })


_SENTINEL = object()


def _result(*, scalar=_SENTINEL, scalar_one=_SENTINEL, all_=_SENTINEL):
    """A canned execute() result configured only for the accessor a step uses."""
    r = MagicMock()
    if scalar is not _SENTINEL:
        r.scalar_one_or_none.return_value = scalar
    if scalar_one is not _SENTINEL:
        r.scalar_one.return_value = scalar_one
    if all_ is not _SENTINEL:
        r.scalars.return_value.all.return_value = all_
    return r


def _db(results):
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=list(results))
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _safety(suppress=False):
    """BOTH fields, explicitly (C-06): an unset should_log is a truthy Mock and
    would fire log_safety_event, adding DB calls these sequenced mocks do not
    expect."""
    return MagicMock(should_suppress_persona=suppress, should_log=False)


def _message(content, safety_level="none", created_at=None):
    """role / safety_level / content / created_at — every field either generator
    reads, set explicitly (C-06). The mirror renders `created_at` into its
    conversation block; the counterview never touches it."""
    return SimpleNamespace(
        role="user", safety_level=safety_level, content=content,
        created_at=created_at or datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
    )


def _insight(content, conversation_id=CONV_ID):
    return SimpleNamespace(
        id=INSIGHT_ID, user_id=USER_ID, content=content,
        conversation_id=conversation_id,
    )


@pytest.fixture
def safe(monkeypatch):
    monkeypatch.setattr(cs.safety_service, "check_input", AsyncMock(return_value=_safety()))
    monkeypatch.setattr(cs.safety_service, "check_output", AsyncMock(return_value=_safety()))
    return monkeypatch


def _added(db, cls_name):
    """Every object handed to db.add whose class has this name."""
    return [c.args[0] for c in db.add.call_args_list
            if type(c.args[0]).__name__ == cls_name]


# ═══════════════════════════════════════════════════════════════════════════
# (0) The mechanism: one detector, and the length it needs
# ═══════════════════════════════════════════════════════════════════════════
#
# EN_MIN_TOKENS is new here. The ratio test #626 calibrated was measured on
# multi-sentence briefs (0.536-0.733); five of the seven prompts in this PR emit
# text that is deliberately terse, and a function-word ratio over four words
# carries no signal at all. The samples below ARE the measurement, kept so that a
# stopword edit or a floor change has to face them.

EN_SHORT_NO_FUNCTION_WORDS = [
    "Quiet ambition",                             # 0.000 — a legitimate title
    "Choosing badly",                             # 0.000
    "Comfort dressed as caution",                 # 0.250
    "A pull toward solitude",                     # 0.250 — a legitimate bullet
    "Weighing freedom against loyalty",           # 0.250
    "Movement teaches what deliberation cannot.",  # 0.200
]
EN_LONG_ENOUGH = [
    EN_VERDICT_1, EN_VERDICT_2,
    "Fear wearing the clothes of care.",
    "Returning often to the same decision",
    "You are right that leaving badly would cost more than staying.",
    "The care you take with other people is real and worth keeping.",
    "You keep asking permission from people who are not in the room.",
    "Drawn to questions of duty and what you owe others",
]
WRONG_LANGUAGE_LONG_ENOUGH = [
    ID_VERDICT_1, ID_VERDICT_2,
    "Esperar no es paciencia cuando el coste sigue creciendo.",
    "Du nennst es Loyalitaet, aber es haelt dich vom Entscheiden ab.",
]


def test_every_short_english_sample_would_be_rejected_without_the_threshold():
    """THE DEFECT THE THRESHOLD EXISTS FOR. Each of these is correct English that
    a prompt in this PR can legitimately produce, and each scores below the floor
    purely because terse English contains no function words."""
    for s in EN_SHORT_NO_FUNCTION_WORDS:
        assert english_function_word_ratio(s) < 0.30, s
        assert len(s.split()) < EN_MIN_TOKENS, s


def test_and_the_threshold_accepts_them():
    for s in EN_SHORT_NO_FUNCTION_WORDS:
        assert language_matches(s, "English"), s


def test_above_the_threshold_english_passes_with_room_to_spare():
    for s in EN_LONG_ENOUGH:
        assert english_function_word_ratio(s) >= 0.30, (s, english_function_word_ratio(s))
        assert language_matches(s, "English"), s


def test_above_the_threshold_wrong_language_is_still_caught():
    """The separation that makes the threshold affordable: the strings the guard
    exists to stop are long enough to be measured, and measure near zero."""
    for s in WRONG_LANGUAGE_LONG_ENOUGH:
        assert english_function_word_ratio(s) <= 0.125, (s, english_function_word_ratio(s))
        assert not language_matches(s, "English"), s


def test_the_separation_margin_is_not_narrowed_by_a_stopword_edit():
    """#626 measured >= 0.20 between English and not-English on briefs. Above
    EN_MIN_TOKENS the same margin holds for these much shorter strings. This
    fails if an edit to EN_FUNCTION_WORDS erodes it."""
    worst_en = min(english_function_word_ratio(s) for s in EN_LONG_ENOUGH)
    best_wrong = max(english_function_word_ratio(s) for s in WRONG_LANGUAGE_LONG_ENOUGH)
    assert worst_en - best_wrong >= 0.20, (worst_en, best_wrong)


def test_a_short_latin_script_wrong_language_string_passes_and_that_is_the_named_trade():
    """Stated here rather than discovered later. Under the threshold only the
    script test runs, so a short non-English Latin-script string is accepted. The
    alternative is nulling a quarter of correct English titles."""
    assert language_matches("Bentuk ambisi", "English")


def test_greek_is_caught_at_any_length_because_the_script_test_needs_no_tokens():
    """The threshold relaxes the ENGLISH half only. Greek-vs-English — the cross
    this product actually serves — is unaffected at every length."""
    assert not language_matches("Ήσυχη φιλοδοξία", "English")
    assert not language_matches("Quiet ambition", "Greek")
    assert language_matches("Ήσυχη φιλοδοξία", "Greek")


# ═══════════════════════════════════════════════════════════════════════════
# (1) Every prompt states its language, and none of them infers one
# ═══════════════════════════════════════════════════════════════════════════

ALL_SEVEN = [
    (COUNTERVIEW_PROMPT, "COUNTERVIEW_PROMPT"),
    (DEEPER_PROMPT, "DEEPER_PROMPT"),
    (RESPOND_PROMPT, "RESPOND_PROMPT"),
    (INSIGHT_MIRROR_PROMPT, "INSIGHT_MIRROR_PROMPT"),
    (SELF_SYSTEM_PROMPT, "SELF_SYSTEM_PROMPT"),
    (FORMING_REFLECTION_PROMPT, "FORMING_REFLECTION_PROMPT"),
    (CLOSING_PROMPT, "CLOSING_PROMPT"),
]


@pytest.mark.parametrize("prompt,name", ALL_SEVEN)
def test_no_prompt_body_states_or_infers_a_language_of_its_own(prompt, name):
    """Same rule as #627's: the computed directive must be the ONLY thing in the
    prompt that decides a language. A body sentence saying something different is
    not redundancy, it is two instructions that can disagree.

    COUNTERVIEW_PROMPT is the one that failed this when it was written: its title
    rule said "Same language as the person's position — if they wrote in Greek,
    the title is in Greek". Deleted."""
    body = prompt.lower()
    assert "same language" not in body, f"{name} still infers its own language"
    assert "write in greek" not in body, f"{name} hardcodes a language"
    assert "write in english" not in body, f"{name} hardcodes a language"
    assert "if they wrote in greek" not in body, f"{name} still infers its own language"


@pytest.mark.parametrize("prompt,name", ALL_SEVEN)
def test_the_directive_is_appended_and_never_formatted_in(prompt, name):
    """Four of the seven carry literal JSON braces, so .format() raises KeyError
    on the JSON rather than filling anything, and two more consume their braces
    for real fields. One injection style for all seven: append.

    This pins the reason. If someone later switches a call site to
    .format(language=...), this test still passes — but the call-site tests below
    assert the directive's exact text in the system prompt, and a KeyError there
    is loud."""
    import string
    fields = [f for _, f, _, _ in string.Formatter().parse(prompt) if f is not None]
    if name == "FORMING_REFLECTION_PROMPT":
        assert fields == [], "the one brace-free prompt; append anyway, for one style"
        return
    assert fields, f"{name} was expected to carry braces"
    with pytest.raises((KeyError, IndexError)):
        prompt.format()


# ═══════════════════════════════════════════════════════════════════════════
# (2) Counterview, round 0
# ═══════════════════════════════════════════════════════════════════════════


async def _direct(monkeypatch, belief, payload):
    """The belief path: no insight lookup, no dedup, no message query — zero
    execute() calls before the write."""
    complete = AsyncMock(return_value=payload)
    monkeypatch.setattr(cs.llm_client, "complete", complete)
    db = _db([])
    cv = await generate_counterview(
        db, USER_ID, belief=belief, source="direct",
    )
    return cv, db, complete


@pytest.mark.asyncio
async def test_an_english_belief_tells_the_model_to_write_english(safe):
    _, _, complete = await _direct(safe, ENGLISH_BELIEF,
                                   _cv_payload(EN_VERDICT_1, EN_VERDICT_2))
    assert "LANGUAGE: Write in English." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_a_greek_belief_tells_the_model_to_write_greek(safe):
    _, _, complete = await _direct(safe, GREEK_BELIEF,
                                   _cv_payload(GREEK_VERDICT_1, GREEK_VERDICT_2))
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_the_directive_sits_after_the_prompt_body_not_inside_it(safe):
    _, _, complete = await _direct(safe, ENGLISH_BELIEF,
                                   _cv_payload(EN_VERDICT_1, EN_VERDICT_2))
    system = complete.call_args.kwargs["system"]
    assert system.startswith(COUNTERVIEW_PROMPT)
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_a_greek_answer_to_an_english_belief_blocks_to_empty(safe):
    """THE RULING. status='empty' is what the frontend already draws for a failed
    generation ("There wasn't a clear case to make against this just yet")."""
    cv, db, _ = await _direct(safe, ENGLISH_BELIEF,
                              _cv_payload(GREEK_VERDICT_1, GREEK_VERDICT_2))
    assert cv.status == "empty"
    assert _added(db, "CounterviewResponse") == [], "no verdict may be persisted"


@pytest.mark.asyncio
async def test_an_indonesian_answer_to_an_english_belief_blocks_too(safe):
    """The Latin-script case — the one #626 was actually built for, where the
    script test alone would pass the string straight through."""
    cv, _, _ = await _direct(safe, ENGLISH_BELIEF,
                             _cv_payload(ID_VERDICT_1, ID_VERDICT_2))
    assert cv.status == "empty"


@pytest.mark.asyncio
async def test_one_bad_verdict_condemns_the_set(safe):
    """Matching the safety loop directly above it: any bad line blocks the pair,
    because the two are displayed together as one artifact."""
    cv, _, _ = await _direct(safe, ENGLISH_BELIEF,
                             _cv_payload(EN_VERDICT_1, GREEK_VERDICT_2))
    assert cv.status == "empty"


@pytest.mark.asyncio
async def test_terse_english_verdicts_are_never_blocked(safe):
    """The false-reject direction, at the call site. Both of these score below the
    function-word floor; neither is wrong."""
    cv, db, _ = await _direct(
        safe, ENGLISH_BELIEF,
        _cv_payload("Movement teaches what deliberation cannot.", "Comfort chose this, not principle."),
    )
    assert cv.status == "generated"
    assert len(_added(db, "CounterviewResponse")) == 2


@pytest.mark.asyncio
async def test_an_empty_belief_resolves_to_english_and_is_not_blocked(safe):
    """Undetermined language → today's behaviour. dominant_language has no
    "unknown": an empty anchor ties at zero and its tie rule gives English, so an
    English answer ships exactly as it does now."""
    cv, _, complete = await _direct(safe, "   ", _cv_payload(EN_VERDICT_1, EN_VERDICT_2))
    assert "LANGUAGE: Write in English." in complete.call_args.kwargs["system"]
    assert cv.status == "generated"


@pytest.mark.asyncio
async def test_the_tighten_retry_cannot_bury_the_directive(safe):
    """The retry appends its own instruction. The language directive is appended
    LAST so it stays the final word in both calls."""
    long_verdict = "one two three four five six seven eight nine ten eleven twelve"
    complete = AsyncMock(side_effect=[
        _cv_payload(long_verdict, long_verdict),
        _cv_payload(EN_VERDICT_1, EN_VERDICT_2),
    ])
    safe.setattr(cs.llm_client, "complete", complete)
    await generate_counterview(_db([]), USER_ID, belief=ENGLISH_BELIEF, source="direct")
    assert complete.call_count == 2
    for call in complete.call_args_list:
        system = call.kwargs["system"]
        assert system.endswith("governs the whole output even if the input mixes languages.")
    assert "exceeded 10 words" in complete.call_args_list[1].kwargs["system"]


# ── the field-level pair: nulled, never blocking ─────────────────────────────

@pytest.mark.asyncio
async def test_a_wrong_language_title_is_nulled_and_the_counterview_still_ships(safe):
    """Field-level (C-01), as the word cap and the safety gate already are. The
    verdicts passed; a bad title is not worth the whole artifact."""
    cv, _, _ = await _direct(
        safe, ENGLISH_BELIEF,
        _cv_payload(EN_VERDICT_1, EN_VERDICT_2, title="Φιλοδοξία και ξεκούραση"),
    )
    assert cv.status == "generated"
    assert cv.title is None


@pytest.mark.asyncio
async def test_a_short_english_title_survives(safe):
    """The title is the field most exposed to the short-text problem: 2-4 words by
    prompt rule, so almost always under EN_MIN_TOKENS. It must not be nulled."""
    cv, _, _ = await _direct(
        safe, ENGLISH_BELIEF,
        _cv_payload(EN_VERDICT_1, EN_VERDICT_2, title="Quiet ambition"),
    )
    assert cv.title == "Quiet ambition"


@pytest.mark.asyncio
async def test_a_wrong_language_still_stands_is_nulled_and_the_counterview_ships(safe):
    cv, _, _ = await _direct(
        safe, ENGLISH_BELIEF,
        _cv_payload(EN_VERDICT_1, EN_VERDICT_2,
                    still="Η φροντίδα σου για τους άλλους είναι αληθινή και αξίζει."),
    )
    assert cv.status == "generated"
    assert cv.still_stands is None


# ── the insight path: where the language must NOT come from the anchor ───────

async def _insight_path(monkeypatch, insight_content, messages, payload):
    complete = AsyncMock(return_value=payload)
    monkeypatch.setattr(cs.llm_client, "complete", complete)
    db = _db([
        _result(scalar=_insight(insight_content)),   # 1: load the insight
        _result(scalar=None),                        # 2: dedup — none yet
        _result(all_=messages),                      # 3: the conversation's user rows
    ])
    cv = await generate_counterview(
        db, USER_ID, insight_id=INSIGHT_ID, source="insight",
    )
    return cv, db, complete


@pytest.mark.asyncio
async def test_the_conversation_beats_the_insight_text_as_the_language_source(safe):
    """THE LAUNDERING TEST, and the reason this PR does not simply read
    anchor_text. The insight is in English; the person wrote Greek. #628 enforces
    language on dilemma-typed insights ONLY, so an English thread over a Greek
    conversation is a state the system can really be in — and reading the
    language off it would copy that error into a second, separately-stored
    artifact."""
    _, _, complete = await _insight_path(
        safe,
        "User keeps postponing a decision they have already made.",
        [_message(GREEK_BELIEF), _message("Δεν ξέρω τι να κάνω με τη δουλειά μου.")],
        _cv_payload(GREEK_VERDICT_1, GREEK_VERDICT_2),
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_the_message_query_is_the_only_one_and_no_query_was_added(safe):
    """The rows are already loaded for the F-15 safety gate, so the language costs
    nothing. Pinned because the counterview tests count execute() calls: three, as
    before this PR."""
    _, db, _ = await _insight_path(
        safe, "User keeps postponing a decision.",
        [_message(ENGLISH_BELIEF), _message("I keep going back and forth on it.")],
        _cv_payload(EN_VERDICT_1, EN_VERDICT_2),
    )
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_with_no_messages_the_anchor_is_the_fallback(safe):
    """Counterview has no minimum-message floor (unlike the insight mirror), so
    the list can be empty. Then the anchor is the best evidence left and must
    still produce a directive rather than nothing."""
    _, _, complete = await _insight_path(
        safe, GREEK_BELIEF, [], _cv_payload(GREEK_VERDICT_1, GREEK_VERDICT_2),
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_blank_messages_do_not_silently_become_the_source(safe):
    """Whitespace-only rows carry no letters, so dominant_language would tie at
    zero and answer English for a Greek person. They are filtered out and the
    anchor takes over."""
    _, _, complete = await _insight_path(
        safe, GREEK_BELIEF, [_message("   "), _message("")],
        _cv_payload(GREEK_VERDICT_1, GREEK_VERDICT_2),
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


# ═══════════════════════════════════════════════════════════════════════════
# (3) Counterview — go deeper
# ═══════════════════════════════════════════════════════════════════════════


def _cvmock(anchor, status="generated"):
    cv = MagicMock()
    cv.id = CV_ID
    cv.user_id = USER_ID
    cv.status = status
    cv.anchor_text = anchor
    cv.source = "direct"
    cv.still_stands = None
    cv.title = None
    return cv


async def _deeper(monkeypatch, anchor, first_cut, reply):
    complete = AsyncMock(return_value=json.dumps({"status": "generated", "verdict": reply}))
    monkeypatch.setattr(cs.llm_client, "complete", complete)
    db = _db([
        _result(scalar=_cvmock(anchor)),                                   # 1: the cv
        _result(all_=[SimpleNamespace(round=0, verdict=first_cut, position=0)]),  # 2: rounds
    ])
    cv = await generate_deeper(db, USER_ID, CV_ID, PERSONA)
    return cv, db, complete


@pytest.mark.asyncio
async def test_go_deeper_states_the_anchors_language(safe):
    _, _, complete = await _deeper(safe, GREEK_BELIEF, GREEK_VERDICT_1,
                                   "Η υπομονή σου έχει ημερομηνία λήξης που αρνείσαι να διαβάσεις.")
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_go_deeper_keeps_the_voice_substitution_and_appends_after_it(safe):
    """{voice} is filled by .replace() because the JSON below it would break
    .format(). The directive is appended after that, never through it."""
    _, _, complete = await _deeper(safe, ENGLISH_BELIEF, EN_VERDICT_1,
                                   "You are rehearsing the conversation instead of having it.")
    system = complete.call_args.kwargs["system"]
    assert "{voice}" not in system, "the placeholder must be filled"
    assert "Miyamoto Musashi" in system
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_a_wrong_language_deeper_line_is_dropped_and_nothing_is_written(safe):
    """THE CHEAPEST BLOCK OF THE SEVEN. No row is written, so the one-deepening
    cap (which counts persisted rounds) is untouched and the person can tap
    again."""
    cv, db, _ = await _deeper(safe, ENGLISH_BELIEF, EN_VERDICT_1, GREEK_VERDICT_2)
    assert _added(db, "CounterviewResponse") == []
    assert db.commit.await_count == 0, "a dropped line must not commit"
    assert cv is not None


@pytest.mark.asyncio
async def test_a_matching_deeper_line_is_written(safe):
    """The inverse regression: a guard that dropped everything would also pass the
    test above."""
    _, db, _ = await _deeper(safe, ENGLISH_BELIEF, EN_VERDICT_1,
                             "You protect the version of yourself that never risked anything.")
    assert len(_added(db, "CounterviewResponse")) == 1


# ═══════════════════════════════════════════════════════════════════════════
# (4) Counterview — the rebuttal exchange
# ═══════════════════════════════════════════════════════════════════════════


async def _respond(monkeypatch, anchor, user_text, reply, *, arq_queue=None):
    monkeypatch.setattr(cs, "_rebuttal_context", AsyncMock(return_value="Your case so far:"))
    complete = AsyncMock(return_value=json.dumps({"status": "generated", "verdict": reply}))
    monkeypatch.setattr(cs.llm_client, "complete", complete)
    db = _db([
        _result(scalar=_cvmock(anchor)),   # 1: the cv
        _result(scalar_one=0),             # 2: the cap count
        _result(scalar_one=0),             # 3: pre_count OR _write_turn's max(sequence)
        _result(scalar_one=_cvmock(anchor)),  # 4
        _result(scalar_one=_cvmock(anchor)),  # 5
        _result(scalar_one=1),             # 6: post_count, when a queue is passed
    ])
    cv = await respond_to_rebuttal(
        db, USER_ID, CV_ID, PERSONA, user_text, arq_queue=arq_queue,
    )
    return cv, db, complete


@pytest.mark.asyncio
async def test_the_rebuttal_reply_follows_the_persons_own_two_texts(safe):
    """The anchor AND the pushback, never `history` — history is this persona's
    own case so far, which is exactly the majority-model-output source #627
    proved is the bug."""
    _, _, complete = await _respond(
        safe, GREEK_BELIEF, "Μα δεν είναι τόσο απλό, έχω και άλλες ευθύνες.",
        "Οι ευθύνες σου δεν αποφασίζουν για σένα.",
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_a_wrong_language_reply_persists_an_empty_turn(safe):
    """The person's own words are kept and the cap is NOT consumed —
    count_generated_rebuttals counts 'generated' only — so they can push back
    again."""
    _, db, _ = await _respond(safe, ENGLISH_BELIEF, "But that is not the whole story here.",
                              GREEK_VERDICT_1)
    turns = _added(db, "CounterviewTurn")
    assert len(turns) == 1
    assert turns[0].status == "empty"
    assert turns[0].persona_response is None
    assert turns[0].user_text == "But that is not the whole story here."


@pytest.mark.asyncio
async def test_a_blocked_rebuttal_does_not_distil_the_persons_words_to_memory(safe):
    """THE NAMED COST OF THIS BLOCK, pinned so it is a decision and not a
    surprise. The memory enqueue fires only for a 'generated' turn, so blocking
    loses the distillation of what the person wrote. Already true of every LLM
    failure on this path; recorded because it is the reason the block is not
    free."""
    queue = AsyncMock()
    await _respond(safe, ENGLISH_BELIEF, "But that is not the whole story here.",
                   GREEK_VERDICT_1, arq_queue=queue)
    assert queue.enqueue_job.await_count == 0


@pytest.mark.asyncio
async def test_a_matching_reply_persists_a_generated_turn_and_does_enqueue(safe):
    """The inverse regression for both assertions above."""
    queue = AsyncMock()
    _, db, _ = await _respond(
        safe, ENGLISH_BELIEF, "But that is not the whole story here.",
        "Your other duties are not the ones deciding this for you.", arq_queue=queue,
    )
    turns = _added(db, "CounterviewTurn")
    assert [t.status for t in turns] == ["generated"]
    assert queue.enqueue_job.await_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# (5) The insight mirror
# ═══════════════════════════════════════════════════════════════════════════


def _mirror_payload(said, meant, thread):
    return json.dumps({
        "status": "generated",
        "moments": [{"said": said, "meant": meant}],
        "thread": thread,
    })


async def _mirror(monkeypatch, insight_content, messages, payload):
    complete = AsyncMock(return_value=payload)
    monkeypatch.setattr(ims.llm_client, "complete", complete)
    persona = SimpleNamespace(id="p1", slug="carl_jung", name="Carl Jung",
                              tradition="analytical psychology")
    db = _db([
        _result(scalar=_insight(insight_content)),                       # 1: insight
        _result(scalar=None),                                            # 2: mirror dedup
        _result(scalar=SimpleNamespace(mirror_host_slug="carl_jung")),   # 3: user
        _result(scalar=persona),                                         # 4: persona by slug
        _result(all_=messages),                                          # 5: user messages
        _result(scalar=persona),                                         # 6: persona by id
    ])
    mirror = await generate_insight_mirror(db, USER_ID, INSIGHT_ID)
    return mirror, db, complete


EN_CONVO = [
    _message("I keep waiting for the right moment to say something about it."),
    _message("I do not want to be the one who ends this, so I wait instead."),
]
EL_CONVO = [
    _message("Περιμένω συνέχεια τη σωστή στιγμή για να μιλήσω γι αυτό."),
    _message("Δεν θέλω να είμαι εγώ αυτός που το τελειώνει, οπότε περιμένω."),
]
EN_MEANT = "You are not weighing this anymore; you are waiting for it to be taken out of your hands."
EN_THREAD = "What you call patience may be the fear of being the one who caused the ending."
EL_MEANT = "Δεν ζυγίζεις πια την απόφαση, περιμένεις να στη πάρουν από τα χέρια."
EL_THREAD = "Αυτό που λες υπομονή ίσως είναι ο φόβος να είσαι εσύ η αιτία του τέλους."


@pytest.mark.asyncio
async def test_the_mirror_directive_is_appended_after_format_not_inside_it(monkeypatch):
    """This is the one of the seven that really is .format()ed: two real fields
    alongside three DOUBLED brace pairs for its JSON shape. All three things must
    be true at once — the fields filled, the JSON braces single in the output, and
    the directive present at the end."""
    _, _, complete = await _mirror(
        monkeypatch, "User keeps postponing a decision.", EN_CONVO,
        _mirror_payload("I keep waiting", EN_MEANT, EN_THREAD),
    )
    system = complete.call_args.kwargs["system"]
    assert "You are Carl Jung, analytical psychology." in system
    assert '{"status": "generated", "moments"' in system, "JSON braces must be unescaped"
    assert "{persona_name}" not in system
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_the_mirrors_language_comes_from_the_messages_not_the_thread(monkeypatch):
    """Same laundering test as the counterview's, at the second insight-seeded
    generator. The noticed thread is English; the person wrote Greek."""
    _, _, complete = await _mirror(
        monkeypatch, "User keeps postponing a decision they have already made.", EL_CONVO,
        _mirror_payload("Περιμένω συνέχεια", EL_MEANT, EL_THREAD),
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_a_wrong_language_thread_blocks_the_mirror_to_empty(monkeypatch):
    mirror, _, _ = await _mirror(
        monkeypatch, "User keeps postponing a decision.", EN_CONVO,
        _mirror_payload("I keep waiting", EN_MEANT, EL_THREAD),
    )
    assert mirror.status == "empty"
    assert mirror.payload is None


@pytest.mark.asyncio
async def test_a_wrong_language_meant_blocks_the_mirror_too(monkeypatch):
    """`meant` is the model's own prose, so it is checked exactly like the
    thread."""
    mirror, _, _ = await _mirror(
        monkeypatch, "User keeps postponing a decision.", EN_CONVO,
        _mirror_payload("I keep waiting", EL_MEANT, EN_THREAD),
    )
    assert mirror.status == "empty"


@pytest.mark.asyncio
async def test_said_is_never_checked_because_it_is_the_persons_own_quoted_words(monkeypatch):
    """DELIBERATE, both halves. "said" is the person's charged phrase quoted back,
    so a mismatch there would mean the quote was fabricated rather than
    mistranslated — a different defect, for a different guard. It is also trimmed
    to "one short line" and so usually carries no ratio signal at all.

    A person writing English can quote themselves in Greek; the mirror must still
    generate."""
    mirror, _, _ = await _mirror(
        monkeypatch, "User keeps postponing a decision.", EN_CONVO,
        _mirror_payload("δεν αντέχω άλλο", EN_MEANT, EN_THREAD),
    )
    assert mirror.status == "generated"
    assert mirror.payload["moments"][0]["said"] == "δεν αντέχω άλλο"


@pytest.mark.asyncio
async def test_a_matching_mirror_still_generates(monkeypatch):
    mirror, _, _ = await _mirror(
        monkeypatch, "User keeps postponing a decision.", EN_CONVO,
        _mirror_payload("I keep waiting", EN_MEANT, EN_THREAD),
    )
    assert mirror.status == "generated"
    assert mirror.payload["thread"] == EN_THREAD


# ═══════════════════════════════════════════════════════════════════════════
# (6) You vs You — the two selves (LOG) and the closing (BLOCK)
# ═══════════════════════════════════════════════════════════════════════════


def _yvy_result():
    """One canned result that satisfies every query stream() makes: the
    self-portrait context (none), the crisis count (zero) and the quote
    candidates (none)."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    r.scalar_one.return_value = 0
    r.all.return_value = []
    r.scalars.return_value.all.return_value = []
    return r


def _window():
    return {
        "start": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "end": datetime(2026, 7, 1, tzinfo=timezone.utc),
        "by_type": {"struggle": ["keeps postponing one decision"]},
    }


async def _yvy(monkeypatch, prompt, self_answer, closing_json):
    """Drive stream() end to end with both LLM paths stubbed. Returns
    (events, captured system prompts, the persisted row)."""
    systems = []

    async def fake_stream(system=None, messages=None, model=None, **kw):
        systems.append(system)
        yield self_answer

    complete = AsyncMock(return_value=closing_json)
    monkeypatch.setattr(scs.llm_client, "stream", fake_stream)
    monkeypatch.setattr(scs.llm_client, "complete", complete)
    monkeypatch.setattr(scs.safety_service, "check_input",
                        AsyncMock(return_value=_safety()))
    monkeypatch.setattr(scs.self_model_service, "build", AsyncMock(return_value={
        "unlocked": True, "total_signals": 9, "reason": None,
        "forming_preview": [], "then": _window(), "now": _window(),
    }))

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_yvy_result())
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    events = []
    async for ev in scs.self_comparison_service.stream(db, USER_ID, prompt):
        events.append(json.loads(ev[len("data: "):]))
    row = db.add.call_args.args[0]
    return events, systems, row, complete


EN_QUESTION = "What am I actually afraid of when I put off this decision?"
EL_QUESTION = "Τι φοβάμαι στ αλήθεια όταν αναβάλλω αυτή την απόφαση;"
EN_CLOSING = json.dumps({
    "observation": "Then, you framed this as whether you could afford to go. "
                   "Lately, you ask what staying is costing you.",
    "question": "Does that reading feel fair to you?",
    "then_quote_id": None, "now_quote_id": None,
    "hidden_continuity": None, "sentence_owed": None,
})
ID_CLOSING = json.dumps({
    "observation": "Dulu kamu bertanya apakah kamu mampu pergi dari pekerjaan itu. "
                   "Sekarang kamu bertanya apa yang kamu bayar untuk tinggal.",
    "question": "Apakah pembacaan itu terasa adil bagimu sekarang?",
    "then_quote_id": None, "now_quote_id": None,
    "hidden_continuity": None, "sentence_owed": None,
})


@pytest.mark.asyncio
async def test_both_selves_are_told_the_language_of_the_question_just_typed(monkeypatch):
    """The question, not the signals. The signals are memory rows written at other
    times; the person is asking THIS now, in the language they are reading in."""
    _, systems, _, _ = await _yvy(
        monkeypatch, EL_QUESTION, "Φοβάμαι ότι θα είμαι εγώ η αιτία.", EN_CLOSING,
    )
    assert len(systems) == 2, "one system prompt per self"
    for system in systems:
        assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_the_selves_directive_is_appended_after_format(monkeypatch):
    _, systems, _, _ = await _yvy(
        monkeypatch, EN_QUESTION, "I am afraid of being the one who caused it.", EN_CLOSING,
    )
    assert "{which_label}" not in systems[0] and "{signals}" not in systems[0]
    assert "You are their earlier self." in systems[0]
    assert systems[0].endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_a_wrong_language_self_is_LOGGED_AND_STILL_SHOWN(monkeypatch):
    """THE ONE LOG-ONLY RULING, and it is structural rather than chosen. Every
    chunk is yielded to the client as it arrives, so by the time the answer can be
    read as a whole the person has already watched it type itself out. There is
    nothing left to block, and a guard added here later would be dead code."""
    wrong = "Saya takut menjadi orang yang menyebabkan semuanya berakhir begitu saja."
    with patch("services.self_comparison_service.logger") as log:
        events, _, row, _ = await _yvy(monkeypatch, EN_QUESTION, wrong, EN_CLOSING)

    warnings = [c for c in log.warning.call_args_list
                if c.args and c.args[0] == "self_comparison_language_mismatch"]
    assert len(warnings) == 2, "both selves answered in the wrong language"
    assert warnings[0].kwargs["extra"]["expected_language"] == "English"

    chunks = [e for e in events if e.get("type") == "chunk"]
    assert chunks and all(e["data"] == wrong for e in chunks), "it was streamed anyway"
    assert row.payload["then"]["answer"] == wrong, "and persisted anyway"
    assert row.status == "ready"


@pytest.mark.asyncio
async def test_the_closing_is_told_the_same_language(monkeypatch):
    _, _, _, complete = await _yvy(
        monkeypatch, EL_QUESTION, "Φοβάμαι ότι θα είμαι εγώ η αιτία.", EN_CLOSING,
    )
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]
    assert complete.call_args.kwargs["system"].startswith(CLOSING_PROMPT)


@pytest.mark.asyncio
async def test_a_wrong_language_closing_blocks_and_leaves_the_block_empty(monkeypatch):
    """Unlike the selves this is ONE complete() call, so it can be checked before
    anything is shown. The frontend guards the whole closing on a truthy
    observation, so the defaults render as no closing at all — exactly what the
    except branch has always produced."""
    events, _, row, _ = await _yvy(
        monkeypatch, EN_QUESTION, "I am afraid of being the one who caused it.", ID_CLOSING,
    )
    closing = [e for e in events if e.get("type") == "closing"][0]
    assert closing["observation"] == ""
    assert closing["question"] == ""
    assert row.payload["closing"]["observation"] == ""


@pytest.mark.asyncio
async def test_a_matching_closing_is_still_shown(monkeypatch):
    """The inverse regression: a guard that emptied every closing would also pass
    the test above."""
    events, _, _, _ = await _yvy(
        monkeypatch, EN_QUESTION, "I am afraid of being the one who caused it.", EN_CLOSING,
    )
    closing = [e for e in events if e.get("type") == "closing"][0]
    assert closing["observation"].startswith("Then, you framed this")
    assert closing["question"] == "Does that reading feel fair to you?"


# ═══════════════════════════════════════════════════════════════════════════
# (7) The forming reflection, and the language its callers must supply
# ═══════════════════════════════════════════════════════════════════════════

EN_SIGNALS = ["keeps postponing one decision", "wants to be seen as reliable"]
EN_BULLETS = "- Returning often to the same decision\n- A pull toward solitude"
EL_BULLETS = "- Επιστρέφεις συχνά στην ίδια απόφαση\n- Μια έλξη προς τη μοναξιά"


async def _forming(monkeypatch, signals, language, raw):
    complete = AsyncMock(return_value=raw)
    monkeypatch.setattr(scs.llm_client, "complete", complete)
    out = await scs.self_comparison_service.forming_reflection(signals, language=language)
    return out, complete


@pytest.mark.asyncio
async def test_forming_reflection_will_not_run_without_being_told_the_language():
    """THE CONTRACT, enforced by the signature: keyword-only and no default, so a
    caller cannot silently fall back to whatever its own material happens to look
    like. Two of the three callers hold English-by-construction text."""
    with pytest.raises(TypeError):
        await scs.self_comparison_service.forming_reflection(EN_SIGNALS)


@pytest.mark.asyncio
async def test_the_language_is_the_argument_and_never_read_off_the_signals(monkeypatch):
    """THE ROW-6 DEFECT, pinned. These signals are English — as
    profile_to_statements and answer_statement output always is, for every user —
    while the person is Greek. Deriving from them would say English every time and
    look right often enough never to be noticed."""
    _, complete = await _forming(monkeypatch, EN_SIGNALS, "Greek", EL_BULLETS)
    assert "LANGUAGE: Write in Greek." in complete.call_args.kwargs["system"]


@pytest.mark.asyncio
async def test_the_forming_directive_is_appended(monkeypatch):
    _, complete = await _forming(monkeypatch, EN_SIGNALS, "English", EN_BULLETS)
    system = complete.call_args.kwargs["system"]
    assert system.startswith(FORMING_REFLECTION_PROMPT)
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_wrong_language_bullets_are_dropped(monkeypatch):
    out, _ = await _forming(monkeypatch, EN_SIGNALS, "English", EL_BULLETS)
    assert out == []


@pytest.mark.asyncio
async def test_matching_bullets_survive(monkeypatch):
    out, _ = await _forming(monkeypatch, EN_SIGNALS, "English", EN_BULLETS)
    assert out == ["Returning often to the same decision", "A pull toward solitude"]


@pytest.mark.asyncio
async def test_bullets_are_judged_together_not_one_by_one(monkeypatch):
    """"A pull toward solitude" is 0.250 on its own — below the floor and under
    EN_MIN_TOKENS. Joined with its siblings the set carries enough tokens to be
    measured, and measures English. Per-bullet checking would have been a coin
    flip on legitimate output."""
    assert english_function_word_ratio("A pull toward solitude") < 0.30
    out, _ = await _forming(monkeypatch, EN_SIGNALS, "English", EN_BULLETS)
    assert "A pull toward solitude" in out


# ── what each caller supplies ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_status_caller_reads_the_language_off_the_memory_rows():
    """The ONE caller whose signals are the person's own words: forming_preview is
    MemoryEntry.content (self_model_service._forming)."""
    from routers.self_comparison import get_self_comparison_status

    greek_rows = [
        "συνεχίζει να αναβάλλει μια απόφαση που έχει ήδη πάρει",
        "θέλει να τον βλέπουν ως αξιόπιστο άνθρωπο",
    ]
    forming = AsyncMock(return_value=[])
    user = SimpleNamespace(id=USER_ID, is_admin=False)
    with (
        patch("routers.self_comparison.self_model_service.build",
              new=AsyncMock(return_value={
                  "unlocked": False, "total_signals": 2, "reason": "forming",
                  "forming_preview": list(greek_rows), "then": None, "now": None,
              })),
        patch("routers.self_comparison.self_comparison_service.forming_reflection",
              new=forming),
    ):
        await get_self_comparison_status(db=AsyncMock(), auth=(user, "pro"))

    assert forming.call_args.kwargs["language"] == "Greek"


@pytest.mark.asyncio
async def test_the_onboarding_caller_falls_back_to_english_when_there_are_no_rows():
    """A person finishing the questionnaire has written nothing this system has
    read, so there is no evidence of their language anywhere. "English" there is a
    DOCUMENTED DEFAULT, not a derivation — pinned so the distinction survives."""
    from services.self_portrait_summary import person_language

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_yvy_result())
    assert await person_language(db, USER_ID) == "English"


@pytest.mark.asyncio
async def test_and_reads_the_rows_when_there_are_some():
    from services.self_portrait_summary import person_language

    r = MagicMock()
    r.scalars.return_value.all.return_value = [
        "συνεχίζει να αναβάλλει μια απόφαση που έχει ήδη πάρει",
    ]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=r)
    assert await person_language(db, USER_ID) == "Greek"
