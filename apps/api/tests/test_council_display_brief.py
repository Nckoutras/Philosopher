"""The Council display brief, and the language it is allowed to come back in.

THE DEFECT, reproduced twice in production on 2026-09-10 (desktop and mobile).
After "Take to the Council" from an English chat, the matter textarea — the
person's own input box — was replaced by an Indonesian sentence. The members
replied in English; only the display text was wrong.

Nothing in the path had ever stated a language. COUNCIL_DISPLAY_BRIEF_PROMPT
asked the MODEL to infer "the same language the person used", and the transcript
it infers from is the last 12 messages of BOTH roles — majority persona output,
not the person's words. Nothing then checked what came back before it overwrote
what the user could see.

This is the second time this class of bug has shipped. The first was the
2026-08-24 letter, which came back with its body in English and two fields in
Greek; the fix there was to COMPUTE the language and inject it (arq_worker.py:67,
`{language}` filled by dominant_language). That fix never reached this surface.

TWO LAYERS, and the second is the one that needed measuring:

  IN  — dominant_language over the person's OWN turns fills {language}. The
        model is no longer asked to infer anything.
  OUT — the returned brief is checked before it is handed back, because an
        explicit instruction is not a guarantee.

WHY THE OUT GUARD IS NOT JUST dominant_language. That function counts Greek
codepoints against Latin ones — it answers "which script", and calls every
Latin-script language English. Run on the real Indonesian briefs below it
returns 'English'. A guard built on it alone would compare 'English' to
'English', pass, and ship the exact string it exists to stop. So Latin-script
output is additionally required to look like English, by function-word ratio.

The calibration is recorded per sample below rather than summarised, because the
floor is a measured number and the samples are the evidence for it.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.council_prompts import COUNCIL_DISPLAY_BRIEF_PROMPT
from services.council_service import council_service
# Promoted to text_utils so four generators share one detector, not four.
from text_utils import (
    EN_FUNCTION_WORD_FLOOR as _EN_FUNCTION_WORD_FLOOR,
    english_function_word_ratio as _english_function_word_ratio,
    language_matches as _brief_language_ok,
)


class FakeMessage:
    """A real object, not a MagicMock: display_brief reads .role and .content and
    counts user turns off them. A MagicMock would answer every read truthily and
    the turn count would stop meaning anything (C-06)."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


def _db(messages):
    """A session whose one query returns `messages`.

    display_brief orders created_at DESC then reverses, so pass them newest-first
    the way the query would hand them over.
    """
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(messages)
    db.execute = AsyncMock(return_value=result)
    return db


# ── The calibration, sample by sample ─────────────────────────────────────────

# Verbatim from production, 2026-09-10. The second contains the English loanword
# "scroll" and still scores zero, which is the point of counting function words
# rather than looking for English-looking tokens.
INDONESIAN_BRIEFS = [
    ("Saya terbebani oleh rasa bersalah yang ditanamkan sejak kecil, dan saya "
     "menggunakan media sosial untuk melarikan diri daripadanya daripada "
     "menghadapinya.", 0.000),
    ("Saya membayar denda karena dibesarkan untuk selalu merasa bersalah, dan saya "
     "mencari penghindaran di scroll karena itu lebih mudah daripada menghadapi "
     "suara hati saya sendiri.", 0.000),
]

# Twelve briefs in the register the prompt actually produces: first person,
# 20-50 words, two sentences at most.
ENGLISH_BRIEFS = [
    ("I'm weighing whether the control I think I have over my own information is "
     "real, or whether it is a story I have been telling myself for a long time.", 0.733),
    ("I keep returning to the same question about how much of my privacy I have "
     "already given away, and whether any of it can be taken back now.", 0.643),
    ("I'm carrying guilt that was put in me early, and I use the scroll to get away "
     "from it rather than sit with what it is actually asking.", 0.571),
    ("I want to know whether the effort I put into managing what people see of me is "
     "protecting anything, or just costing me the time I say I do not have.", 0.710),
    ("I'm stuck between leaving a job that is steady and taking one that might mean "
     "something, and I cannot tell which fear is doing the talking.", 0.615),
    ("I notice I reach for my phone whenever the room gets quiet, and I am not sure "
     "whether I am avoiding boredom or avoiding a thought underneath it.", 0.536),
    ("I'm trying to work out why an apology I gave last week still sits badly with "
     "me, even though the person I gave it to seems to have moved on.", 0.567),
    ("I keep promising myself I will start earlier, and every week I find a reason "
     "not to, and the gap between what I intend and what I do is widening.", 0.667),
    ("I'm wondering whether the distance I have kept from my family is protecting me "
     "from something real, or whether it has just become a habit I never questioned.", 0.643),
    ("I want to be someone who finishes things, and I have enough evidence by now "
     "that wanting it has not been enough to make it happen.", 0.615),
    ("I'm weighing whether to say the thing that would clear the air, knowing it "
     "would cost me a friendship that has already been thinner than I admit.", 0.593),
    ("I feel behind in a way I cannot name precisely, measured against people whose "
     "lives I only see the edited version of, and it will not leave me alone.", 0.552),
]

# Greek is decided by script alone — no language the product serves is written in
# Greek script, so a Greek-script answer to a Greek conversation is right by
# construction and the function-word ratio never runs.
GREEK_BRIEFS = [
    "Με απασχολεί το αν ο έλεγχος που νομίζω ότι έχω πάνω στις πληροφορίες μου "
    "είναι πραγματικός ή μια ιστορία που λέω στον εαυτό μου.",
    "Κουβαλάω μια ενοχή που μου φυτεύτηκε νωρίς και χρησιμοποιώ το κινητό για να "
    "ξεφύγω από αυτήν αντί να την κοιτάξω.",
    "Δεν ξέρω αν η απόσταση που κρατάω από την οικογένειά μου με προστατεύει ή αν "
    "έγινε απλώς συνήθεια.",
    "Θέλω να καταλάβω γιατί μια συγγνώμη που έδωσα ακόμα με βαραίνει, ενώ ο άλλος "
    "φαίνεται να το έχει ξεπεράσει.",
    "Είμαι ανάμεσα σε μια δουλειά σταθερή και σε μια που ίσως έχει νόημα, και δεν "
    "ξέρω ποιος φόβος μιλάει.",
]

ENGLISH_CHAT = [
    FakeMessage("assistant", "What do you think you are actually protecting?"),
    FakeMessage("user", "I keep tightening my privacy settings and it changes nothing."),
    FakeMessage("assistant", "And yet you keep going back to them."),
    FakeMessage("user", "I think the control I believe I have over my information is an illusion."),
]

GREEK_CHAT = [
    FakeMessage("assistant", "Τι νομίζεις ότι προστατεύεις στην πραγματικότητα;"),
    FakeMessage("user", "Συνέχεια αλλάζω ρυθμίσεις απορρήτου και δεν αλλάζει τίποτα."),
    FakeMessage("assistant", "Κι όμως επιστρέφεις σε αυτές."),
    FakeMessage("user", "Νομίζω ότι ο έλεγχος που πιστεύω ότι έχω στις πληροφορίες μου είναι ψευδαίσθηση."),
]


@pytest.mark.parametrize("brief,measured", INDONESIAN_BRIEFS)
def test_a_real_indonesian_brief_scores_zero_and_is_rejected(brief, measured):
    """(a) Zero false positives. Both production strings, verbatim."""
    ratio = _english_function_word_ratio(brief)
    assert ratio == pytest.approx(measured, abs=0.01), (
        f"calibration drift: recorded {measured:.3f}, now {ratio:.3f}"
    )
    assert ratio < _EN_FUNCTION_WORD_FLOOR
    assert _brief_language_ok(brief, "English") is False


@pytest.mark.parametrize("brief,measured", ENGLISH_BRIEFS)
def test_an_in_register_english_brief_clears_the_floor(brief, measured):
    """(b) Zero false negatives across twelve in-register briefs."""
    ratio = _english_function_word_ratio(brief)
    assert ratio == pytest.approx(measured, abs=0.01), (
        f"calibration drift: recorded {measured:.3f}, now {ratio:.3f}"
    )
    assert ratio >= _EN_FUNCTION_WORD_FLOOR
    assert _brief_language_ok(brief, "English") is True


@pytest.mark.parametrize("brief", GREEK_BRIEFS)
def test_a_greek_brief_passes_on_script_alone(brief):
    """(c) Script check only — the ratio is never consulted for Greek."""
    assert _brief_language_ok(brief, "Greek") is True
    assert _brief_language_ok(brief, "English") is False


def test_the_floor_sits_clear_of_both_sides():
    """The property the floor has to keep, stated as a separation rather than a
    number, so a stopword edit that collapses the margin fails here rather than
    silently narrowing it."""
    worst_bad = max(_english_function_word_ratio(b) for b, _ in INDONESIAN_BRIEFS)
    worst_good = min(_english_function_word_ratio(b) for b, _ in ENGLISH_BRIEFS)
    assert worst_bad < _EN_FUNCTION_WORD_FLOOR <= worst_good
    assert _EN_FUNCTION_WORD_FLOOR - worst_bad >= 0.20, "margin above the bad side collapsed"
    assert worst_good - _EN_FUNCTION_WORD_FLOOR >= 0.20, "margin below the good side collapsed"


def test_an_empty_brief_scores_zero_rather_than_dividing_by_zero():
    assert _english_function_word_ratio("") == 0.0
    assert _english_function_word_ratio("   ") == 0.0
    assert _english_function_word_ratio("2026 !!! 😀") == 0.0


# ── display_brief end to end ──────────────────────────────────────────────────

async def _run(messages, llm_returns):
    """display_brief with the LLM mocked; returns (result, captured system prompt)."""
    captured = {}

    async def fake_complete(system, user, model=None, max_tokens=512):
        captured["system"] = system
        captured["user"] = user
        return llm_returns

    with patch("services.council_service.llm_client.complete", new=fake_complete):
        out = await council_service.display_brief(_db(messages), "u1", "conv-1")
    return out, captured.get("system", "")


@pytest.mark.asyncio
async def test_an_indonesian_brief_for_an_english_chat_is_withheld():
    """THE DEFECT. Without the guard this returns the Indonesian sentence and it
    replaces the person's own text in the matter box."""
    out, _ = await _run(ENGLISH_CHAT, INDONESIAN_BRIEFS[0][0])
    assert out is None


@pytest.mark.asyncio
async def test_an_english_brief_for_an_english_chat_is_returned():
    out, _ = await _run(ENGLISH_CHAT, ENGLISH_BRIEFS[0][0])
    assert out == ENGLISH_BRIEFS[0][0]


@pytest.mark.asyncio
async def test_a_greek_brief_for_a_greek_chat_is_returned():
    out, _ = await _run(GREEK_CHAT, GREEK_BRIEFS[0])
    assert out == GREEK_BRIEFS[0]


@pytest.mark.asyncio
async def test_an_english_brief_for_a_greek_chat_is_withheld():
    """The other direction. Drifting INTO English is as wrong as drifting out of
    it, and the script test alone catches this one."""
    out, _ = await _run(GREEK_CHAT, ENGLISH_BRIEFS[0][0])
    assert out is None


@pytest.mark.asyncio
async def test_the_system_prompt_states_the_computed_language():
    """Layer 1. The model is TOLD the language; it is not asked to work it out."""
    _, system = await _run(ENGLISH_CHAT, ENGLISH_BRIEFS[0][0])
    assert "LANGUAGE: Write the summary in English." in system
    assert "{language}" not in system, "the template was sent unformatted"

    _, system_el = await _run(GREEK_CHAT, GREEK_BRIEFS[0])
    assert "LANGUAGE: Write the summary in Greek." in system_el


@pytest.mark.asyncio
async def test_the_language_is_computed_from_the_users_own_turns():
    """The transcript is majority persona output. A Greek chat whose PERSONA
    turns are English must still be briefed in Greek — inferring from the whole
    transcript is what shipped the defect."""
    mixed = [
        FakeMessage("assistant", "That is a very long English reply about control and privacy and what it means."),
        FakeMessage("user", "Νιώθω ότι δεν ελέγχω τίποτα."),
        FakeMessage("assistant", "Another long English reply, again about the same subject at length."),
        FakeMessage("user", "Και όμως συνεχίζω να προσπαθώ."),
    ]
    _, system = await _run(mixed, GREEK_BRIEFS[0])
    assert "LANGUAGE: Write the summary in Greek." in system


@pytest.mark.asyncio
async def test_a_thin_conversation_returns_none_before_any_llm_call():
    """Regression: the <2 user turns guard predates this fix and still holds."""
    thin = [
        FakeMessage("assistant", "What brings you here?"),
        FakeMessage("user", "I am not sure yet."),
    ]
    called = False

    async def fake_complete(system, user, model=None, max_tokens=512):
        nonlocal called
        called = True
        return "should never be reached"

    with patch("services.council_service.llm_client.complete", new=fake_complete):
        out = await council_service.display_brief(_db(thin), "u1", "conv-1")
    assert out is None
    assert called is False, "the LLM was called for a conversation too thin to brief"


@pytest.mark.asyncio
async def test_an_empty_completion_returns_none():
    out, _ = await _run(ENGLISH_CHAT, "   ")
    assert out is None


def test_the_prompt_is_a_template_that_no_longer_asks_the_model_to_infer():
    assert "{language}" in COUNCIL_DISPLAY_BRIEF_PROMPT
    lowered = COUNCIL_DISPLAY_BRIEF_PROMPT.lower()
    assert "same language the person used" not in lowered, (
        "the inference instruction is back; the model must be told, not asked to guess"
    )
