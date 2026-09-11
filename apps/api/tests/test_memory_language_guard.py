"""The language a memory is written in, at the three generators that write one.

THE DATA. 20 of 20 memory_entries sampled for a Greek-writing user came back in
English, across all three sources. This is not a flaky model — it is three
prompts that never stated a language:

  MEMORY_EXTRACTION_PROMPT   said NOTHING about language, and demonstrates the
                             output shape with four worked examples, all English
                             ("User is experiencing conflict between career...").
                             A model given English examples, an English output
                             shape and no instruction does the predictable thing.
  DISTILL_TO_MEMORY_PROMPT   asked the model to match "the SAME language as the
                             input" — inference, the same thing that produced an
                             Indonesian council brief for an English chat (#626).
  SELF_PORTRAIT_SUMMARY      said nothing either.

Fixed the way the letter engine was fixed in August and the council brief in
#626: COMPUTE the language from the person's own words and say it. The directive
is APPENDED, not .format()ed — two of these three prompts carry literal braces
(the JSON shapes), so a format call raises KeyError on the JSON instead of
filling anything. test_the_directive_survives_prompts_containing_json_braces
pins that.

THE OUT LAYER IS NOT THE SAME EVERYWHERE, and the asymmetry is the point:

  memory writers   log, never block. A row in the wrong language is still a true
                   fact about the person; dropping it loses the fact as well as
                   the language, and nothing else records it. (Founder ruling,
                   2026-09-11: never block a write on detection failure.)
  portrait summary blocks. It is display text, and returning None is a path the
                   caller already has — negative-cache marker, prior summary or
                   the forming preview, retry after the cooldown. Nothing is lost.

NOT IN SCOPE, and not a gap: self_portrait's answer_statement/shift_statement are
f-string templates over an English-by-design question bank, so those rows are
English by construction. Founder decision 2026-09-11: the audience is
English-speaking and that copy is correct. No Greek set, no migration.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.memory_service import (
    DISTILL_TO_MEMORY_PROMPT,
    MEMORY_EXTRACTION_PROMPT,
    distill_to_memory,
    memory_service,
)
from services.self_portrait_prompts import SELF_PORTRAIT_SUMMARY_PROMPT
from text_utils import dominant_language, language_directive, language_matches

GREEK_TEXT = (
    "Νιώθω ότι δεν ελέγχω τίποτα στη δουλειά μου και αυτό με κρατάει ξύπνιο "
    "τα βράδια εδώ και εβδομάδες."
)
ENGLISH_TEXT = (
    "I feel that I control nothing at work and it has been keeping me awake at "
    "night for weeks now."
)

GREEK_STATEMENT = "Ο χρήστης νιώθει ότι δεν ελέγχει τίποτα στη δουλειά του."
ENGLISH_STATEMENT = "User feels that they control nothing at work."


# ── The directive itself ──────────────────────────────────────────────────────

def test_the_directive_names_the_language_and_forbids_the_others():
    assert "Write in Greek." in language_directive("Greek")
    assert "Write in English." in language_directive("English")
    assert "never translate" in language_directive("Greek")


@pytest.mark.parametrize("prompt,name", [
    (MEMORY_EXTRACTION_PROMPT, "MEMORY_EXTRACTION_PROMPT"),
    (SELF_PORTRAIT_SUMMARY_PROMPT, "SELF_PORTRAIT_SUMMARY_PROMPT"),
    (DISTILL_TO_MEMORY_PROMPT, "DISTILL_TO_MEMORY_PROMPT"),
])
def test_the_directive_survives_prompts_containing_json_braces(prompt, name):
    """Appending works on every prompt; .format() would raise on two of the three.

    This is the regression that would bite a later contributor who 'tidied' the
    injection to match the council prompt's {language} template — that prompt has
    no braces and these two do.
    """
    combined = prompt + language_directive("Greek")
    assert combined.endswith("mixes languages.")
    assert prompt in combined
    if "{" in prompt:
        with pytest.raises((KeyError, IndexError, ValueError)):
            prompt.format(language="Greek")


def test_the_extraction_prompt_still_carries_no_language_of_its_own():
    """The fix is the appended directive, not an edit to the prompt body. If
    someone later writes a language rule INTO the prompt, the computed one and
    the written one can disagree — which is the failure #626 was about."""
    body = MEMORY_EXTRACTION_PROMPT.lower()
    assert "same language" not in body
    assert "write in greek" not in body and "write in english" not in body


# ── distill_to_memory ─────────────────────────────────────────────────────────

async def _distill(text, returns):
    captured = {}

    async def fake_complete(system, user, model=None, max_tokens=512):
        captured["system"] = system
        return returns

    with patch("services.memory_service.llm_client.complete", new=fake_complete):
        out = await distill_to_memory(text)
    return out, captured.get("system", "")


@pytest.mark.asyncio
async def test_greek_input_tells_the_model_to_write_greek():
    _, system = await _distill(GREEK_TEXT, GREEK_STATEMENT)
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_english_input_tells_the_model_to_write_english():
    _, system = await _distill(ENGLISH_TEXT, ENGLISH_STATEMENT)
    assert "LANGUAGE: Write in English." in system


@pytest.mark.asyncio
async def test_a_greek_statement_for_greek_input_is_returned():
    out, _ = await _distill(GREEK_TEXT, GREEK_STATEMENT)
    assert out == GREEK_STATEMENT


@pytest.mark.asyncio
async def test_an_english_statement_for_greek_input_is_STILL_returned():
    """THE RULING. The guard logs; it does not drop the row. Losing the memory
    would cost the person a fact about themselves as well as the language."""
    with patch("services.memory_service.logger") as log:
        out, _ = await _distill(GREEK_TEXT, ENGLISH_STATEMENT)
    assert out == ENGLISH_STATEMENT, "a wrong-language memory must still be written"
    assert log.warning.called
    kwargs = log.warning.call_args.kwargs
    assert kwargs["extra"]["expected_language"] == "Greek"
    assert kwargs["extra"]["site"] == "distill_to_memory"


@pytest.mark.asyncio
async def test_a_matching_statement_logs_nothing():
    with patch("services.memory_service.logger") as log:
        await _distill(GREEK_TEXT, GREEK_STATEMENT)
    assert not log.warning.called


@pytest.mark.asyncio
async def test_trivial_text_still_short_circuits_before_any_llm_call():
    """Regression: the word-count pre-filter predates this fix and still holds."""
    called = False

    async def fake_complete(system, user, model=None, max_tokens=512):
        nonlocal called
        called = True
        return ENGLISH_STATEMENT

    with patch("services.memory_service.llm_client.complete", new=fake_complete):
        out = await distill_to_memory("too short")
    assert out is None
    assert called is False


# ── extract_and_store ─────────────────────────────────────────────────────────

def _db():
    """A session that accepts adds and flushes. add() is a plain recorder so a
    row's attributes stay readable (C-06: a MagicMock would absorb the writes)."""
    db = MagicMock()
    db.added = []
    db.add = lambda row: db.added.append(row)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


async def _extract(user_text, entries):
    import json as _json
    captured = {}

    async def fake_complete(system, user, model=None, max_tokens=512):
        captured["system"] = system
        return _json.dumps(entries)

    with patch("services.memory_service.llm_client.complete", new=fake_complete), \
         patch("services.memory_service.embedding_client.embed",
               new=AsyncMock(return_value=[0.0] * 1536)):
        db = _db()
        saved = await memory_service.extract_and_store(
            db, "u1", "conv-1", "p1", user_text, "assistant reply", source_turn=1,
        )
    return saved, captured.get("system", "")


@pytest.mark.asyncio
async def test_extraction_is_told_the_language_of_the_users_own_turn():
    _, system = await _extract(GREEK_TEXT, [])
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_extraction_reads_the_user_turn_not_the_assistant_reply():
    """The assistant's English reply is in the user block as context. It is not
    evidence of what language the PERSON writes in."""
    _, system = await _extract(GREEK_TEXT, [])
    assert "LANGUAGE: Write in Greek." in system
    assert "LANGUAGE: Write in English." not in system


@pytest.mark.asyncio
async def test_a_wrong_language_row_is_still_persisted():
    entries = [{"type": "struggle", "content": ENGLISH_STATEMENT, "confidence": 0.9}]
    with patch("services.memory_service.logger") as log:
        saved, _ = await _extract(GREEK_TEXT, entries)
    assert len(saved) == 1, "the row must be written even in the wrong language"
    assert saved[0].content == ENGLISH_STATEMENT
    assert log.warning.called
    assert log.warning.call_args.kwargs["extra"]["site"] == "extract_and_store"


@pytest.mark.asyncio
async def test_a_matching_row_persists_and_logs_nothing():
    entries = [{"type": "struggle", "content": GREEK_STATEMENT, "confidence": 0.9}]
    with patch("services.memory_service.logger") as log:
        saved, _ = await _extract(GREEK_TEXT, entries)
    assert len(saved) == 1
    assert not log.warning.called


# ── generate_portrait ─────────────────────────────────────────────────────────

async def _portrait(signals, summary_text):
    """generate_portrait with everything upstream of the LLM call stubbed."""
    import services.self_portrait_summary as sps
    import json as _json

    captured = {}

    async def fake_complete(system, user, model=None, max_tokens=512):
        captured["system"] = system
        return _json.dumps({
            "summary": summary_text,
            "best_fit": [{"slug": "socrates", "why": "because"}],
        })

    persona = MagicMock()
    persona.slug = "socrates"
    persona.name = "Socrates"
    persona.portrait_url = "/personas/socrates.webp"

    rows = MagicMock()
    rows.scalars.return_value.all.return_value = [persona]
    db = MagicMock()
    db.execute = AsyncMock(return_value=rows)

    match = MagicMock()
    match.slug = "socrates"

    with patch.object(sps, "llm_client") as llm, \
         patch.object(sps, "answers_to_statements", return_value=["Asked X, they answered: Y."]), \
         patch.object(sps, "themes_from_answers", return_value=["work"]), \
         patch.object(sps, "compute_matches", return_value=[match]), \
         patch.object(sps, "_recent_signals", new=AsyncMock(return_value=signals)):
        llm.complete = fake_complete
        out = await sps.generate_portrait(db, "u1", {"q1": 0}, "clarity")
    return out, captured.get("system", "")


@pytest.mark.asyncio
async def test_the_portrait_language_comes_from_the_memory_signals():
    """Not from the quiz statements — those are English by design for everyone,
    so they carry no information about the person's language."""
    _, system = await _portrait([GREEK_STATEMENT], GREEK_STATEMENT)
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_a_portrait_with_no_signals_yet_defaults_to_english():
    _, system = await _portrait([], ENGLISH_STATEMENT)
    assert "LANGUAGE: Write in English." in system


@pytest.mark.asyncio
async def test_a_matching_portrait_is_returned():
    out, _ = await _portrait([GREEK_STATEMENT], GREEK_STATEMENT)
    assert out is not None
    assert out["text"] == GREEK_STATEMENT


@pytest.mark.asyncio
async def test_a_wrong_language_portrait_is_withheld():
    """UNLIKE the memory writers. Display text, and the caller already has a
    None path: negative cache, prior summary or forming preview, retry later."""
    out, _ = await _portrait([GREEK_STATEMENT], ENGLISH_STATEMENT)
    assert out is None


# ── The promotion did not change the detector ─────────────────────────────────

def test_language_matches_still_rejects_the_indonesian_string_that_started_this():
    """The helper moved from council_service to text_utils in this PR. Same
    behaviour, or the council guard silently weakened."""
    indonesian = (
        "Saya terbebani oleh rasa bersalah yang ditanamkan sejak kecil, dan saya "
        "menggunakan media sosial untuk melarikan diri daripadanya daripada "
        "menghadapinya."
    )
    assert dominant_language([indonesian]) == "English", "script detector changed"
    assert language_matches(indonesian, "English") is False
    assert language_matches(ENGLISH_STATEMENT, "English") is True
    assert language_matches(GREEK_STATEMENT, "Greek") is True
