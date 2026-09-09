"""The 2026-09-09 native review of the Greek and greeklish lexicons.

WHY THIS FILE EXISTS. TD-61 carried one sentence for two rotations: 210 entries
passing their tests and never read by a Greek speaker. They were read on
2026-09-09 (first pass ChatGPT, arbitration founder), and the review found that
the lists were wrong in a direction the existing tests could not see — because
every existing test asks "does this phrase fire?", and the review's findings are
all about phrases that fire when they SHOULD NOT.

TWO MECHANISM FACTS DROVE THE CHANGES, and both are pinned below:

  1. MEDIUM suppresses the persona exactly as HIGH does — `should_suppress_persona`
     is `level in ("medium","high","critical")` (safety_service.py). So a MEDIUM
     false positive replaces the philosopher with crisis copy. `δεν εχει νοημα`
     ("there's no point") was MEDIUM. In a philosophy app that is a Tuesday.
  2. An OUTPUT hit replaces the WHOLE persona response (conversation_service).
     So `πιο αποτελεσματικοσ τροποσ` ("the most effective way") in OUTPUT would
     erase an answer about how to talk to your father.

WHAT THIS FILE PINS THAT THE OTHERS DO NOT. test_safety_greek.py pins that the
gates fire. This pins the BAND each phrase lands in — which is the thing the
review changed, and the thing a later "let's be safer" edit would silently undo
by promoting a phrase back up. A test that only asserted "level != none" would
pass under both the old and the new lists and would therefore be worthless here.

The asymmetry still governs everything: a false positive shows a caring message
to someone safe, a false negative leaves someone in crisis with Nietzsche. These
moves are not a relaxation of that principle. They are the observation that
MEDIUM is not a soft band — it is a full persona suppression — so the phrases
that sit in it must earn it.
"""
import pytest

from services.safety_service import SafetyService


@pytest.fixture
def safety():
    return SafetyService()


# ── 1. Regression: the crisis phrases that started all of this still fire ─────
# If anything below this line ever changes these, the review went too far.

@pytest.mark.parametrize("text", [
    "θέλω να αυτοκτονήσω",
    "θελω να αυτοκτονησω",
    "tha autoktoniso",
])
async def test_the_original_crisis_phrases_are_still_high(safety, text):
    result = await safety.check_input(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


# ── 2. Added to HIGH ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "θα αυτοκτονήσω",
    "θα τελειώσω τη ζωή μου",
    "βάζω τέλος στη ζωή μου",
    "κόβομαι",
    "χαράζω τα χέρια μου",
    "tha autoktoniso",
    "tha aftoktoniso",
    "tha teleioso ti zoi mou",
    "vazo telos sti zoi mou",
])
async def test_added_high_phrases_classify_high(safety, text):
    result = await safety.check_input(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


# ── 3. Added to MEDIUM ────────────────────────────────────────────────────────
# Greeklish feminine forms of "I feel invisible", and the greeklish form of
# "would be better without me" which had a Greek entry but no latin one.

@pytest.mark.parametrize("text", [
    "tha itan kalytera xoris emena",
    "niotho aorati",
    "niw8w aorati",
])
async def test_added_medium_phrases_classify_medium(safety, text):
    result = await safety.check_input(text)
    assert result.level == "medium", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is True


# ── 4. Added to LOW ───────────────────────────────────────────────────────────
# Real distress, logged, persona kept. The point of the band.

@pytest.mark.parametrize("text", [
    "είμαι άχρηστος",
    "είμαι άχρηστη",
    "δεν αξίζω τίποτα",
    "νιώθω ότι είμαι βάρος",
    "eimai axristos",
    "eimai axristi",
    "den axizo tipota",
    "niotho oti eimai baros",
])
async def test_added_low_phrases_classify_low_and_keep_the_persona(safety, text):
    result = await safety.check_input(text)
    assert result.level == "low", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is False


# ── 5. Moved DOWN to LOW ──────────────────────────────────────────────────────
# The heart of the review. Each of these used to suppress the persona. The
# assertion is on the band AND on should_suppress_persona, because the band name
# is the mechanism and the flag is the consequence a user would feel.

@pytest.mark.parametrize("text", [
    "δεν έχει νόημα",
    "δεν βλέπω νόημα",
    "απελπισία",
    "απελπισμένος",
    "απελπισμένη",
    "τα παράτησα όλα",
    "αντίο για πάντα",
    "den exei noima",
    "den vlepo noima",
    "den vlepw noima",
    "apelpisia",
    "apelpismenos",
    "apelpismeni",
    "antio gia panta",
])
async def test_moved_phrases_are_now_low_and_no_longer_suppress(safety, text):
    result = await safety.check_input(text)
    assert result.level == "low", f"{text!r} -> {result.level}"
    assert result.should_suppress_persona is False


# ── 6. The TIPOTA split — this pair IS the ruling ─────────────────────────────
# "δεν εχει νοημα" moved to LOW, but "τιποτα δεν εχει νοημα" stayed in MEDIUM.
# That only works because bands are scanned HIGH -> MEDIUM -> LOW and the first
# hit wins: the longer MEDIUM entry matches before the shorter LOW one is
# reached. Reorder the scan, or delete the TIPOTA entries as "redundant", and
# this pair is what fails.

async def test_nothing_matters_still_suppresses(safety):
    result = await safety.check_input("τίποτα δεν έχει νόημα πια")
    assert result.level == "medium"
    assert result.should_suppress_persona is True


async def test_generic_meaning_talk_keeps_the_philosopher(safety):
    """The sentence the review existed to protect.

    "There's no point continuing this job" is a person thinking about work, in
    an app whose entire proposition is thinking about work with a philosopher.
    Before 2026-09-09 it silently replaced Marcus Aurelius with crisis copy.
    """
    result = await safety.check_input("δεν έχει νόημα να συνεχίσω αυτή τη δουλειά")
    assert result.level == "low"
    assert result.should_suppress_persona is False


async def test_the_greeklish_tipota_form_also_still_suppresses(safety):
    result = await safety.check_input("den exei noima tipota pia")
    assert result.level == "medium"
    assert result.should_suppress_persona is True


# ── 7. Removed from OUTPUT ────────────────────────────────────────────────────
# Each of these erased an entire persona response. None is lethal on its own.

@pytest.mark.parametrize("text", [
    "ο πιο ανώδυνος τρόπος είναι να ξεκινήσεις νωρίς",
    "μια ανώδυνη μέθοδος για να μάθεις πιάνο",
    "ο λιγότερο επώδυνος δρόμος είναι η ειλικρίνεια",
    "ένας τρόπος για να τελειώσει αυτή η κουβέντα",
    "πώς να πηδήξεις πάνω από τον φόβο σου",
    "πού να αγοράσεις ένα καλό βιβλίο",
    "anodynos tropos gia na arxiseis",
    "anwdynos tropos na to peis",
    "anodyni methodos gia na mathis",
    "ligotero epodynos dromos einai i eilikrineia",
    "tropos gia na teleiosei afti i kouventa",
])
async def test_removed_output_phrases_no_longer_suppress(safety, text):
    result = await safety.check_output(text)
    assert result.level == "none", f"{text!r} -> {result.level} ({result.raw_flags})"


async def test_the_sentence_about_talking_to_your_father_survives(safety):
    """The worked example from the review, asserted rather than described.

    `πιο αποτελεσματικοσ τροποσ` was in OUTPUT, and an OUTPUT hit replaces the
    whole response — so a philosopher answering a question about a difficult
    parent had its answer deleted and a crisis message shown instead.
    """
    result = await safety.check_output(
        "ο πιο αποτελεσματικός τρόπος να μιλήσεις στον πατέρα σου"
    )
    assert result.level == "none", result.raw_flags


# ── 8. Added to OUTPUT ────────────────────────────────────────────────────────
# The removals above are not a retreat: explicit method-seeking still dies.

@pytest.mark.parametrize("text", [
    "πώς να αυτοκτονήσεις",
    "πως να αυτοκτονησεις",
    "pos na autoktoniseis",
])
async def test_added_output_phrases_still_suppress(safety, text):
    result = await safety.check_output(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
    assert result.category == "output_harm"


# ── 9. The over-trigger entries stay, deliberately ────────────────────────────

@pytest.mark.parametrize("text", ["αυτοκτονία", "αυτοκτονώ"])
async def test_the_over_trigger_entries_are_kept(safety, text):
    """Ruled in deliberately: these fire on academic or third-person discussion.

    Under the asymmetry that governs the whole lexicon, a philosophy student
    reading a caring message is a smaller cost than a person in crisis reading
    Nietzsche. The review did not touch them, and this pins that it did not.
    """
    result = await safety.check_input(text)
    assert result.level == "high", f"{text!r} -> {result.level}"
