"""UAT2-004 — brevity must stay inert when `regenerate_or_trim` runs in production.

THE RISK THIS FILE GUARDS. `regenerate_or_trim` runs all three checks, and
before UAT2-004 brevity could force work in two separate places:

  1. `all_ok` — a brevity REGENERATE blocks it, so the reply is regenerated,
     up to MAX_REGEN_ATTEMPTS times.
  2. `_deterministic_strip` — its tail TRUNCATES the reply at a sentence
     boundary whenever a brevity result failed. That is the same function
     UAT2-001 Ruling D stopped calling on the streaming path, for the same
     reason: it edits text the reader is going to see.

Neither was a problem while the function had no production caller. Site 4 gives
it one. Measured over all 826 Oregon replies, brevity is outside its band on
18.5% of them — against 1.09% for the persona lexicon — so without the flag,
wiring this in would regenerate and then truncate close to a fifth of every
surface it touches, silently, on a check that `conversation_service` has
deliberately kept inert since #684.

`brevity_triggers=False` is the flag. These are the assertions that it works.

WHICH TESTS PROVE WHAT — measured, not intended. Revert-verified twice: once by
removing the parameter (4 fail on TypeError, which proves only that it is new)
and once by keeping the signature and neutering `gating` to `results`, which is
the real test of the semantics. Under the second, 2 fail and 3 pass. The two
that fail — byte-identical return, and length absent from the directive — are
the FIX-PINNING pair. The other three are GUARDs and are labelled as such.

Run: cd apps/api && pytest tests/test_brevity_inert_in_batch.py -v
"""
import pytest

from personas import get_persona
from services.postprocessing_service import CheckAction, regenerate_or_trim


OVER_BAND = " ".join(["water finds its own level and asks nothing"] * 30)


@pytest.fixture
def no_llm(monkeypatch):
    """Any regeneration attempt is a test failure, and is recorded as one."""
    calls = []

    async def _boom(*args, **kwargs):
        calls.append(kwargs)
        raise AssertionError("regeneration attempted when none was expected")

    import services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "complete", _boom)
    return calls


@pytest.mark.asyncio
async def test_over_length_reply_is_returned_byte_identical(no_llm):
    """FIX-PINNING. The load-bearing assertion of the whole wiring.

    A reply far over the ceiling with no lexicon hit must come back unchanged —
    not merely un-regenerated, but un-TRUNCATED, which is the failure mode that
    would have reached a reader.
    """
    persona = get_persona("lao_tzu")  # standard band (45, 65) since the B2 change
    assert len(OVER_BAND.split()) > 45

    final, history = await regenerate_or_trim(
        OVER_BAND, persona, "SYSTEM", "USER", brevity_triggers=False,
    )

    assert final == OVER_BAND, "reply was mutated despite brevity_triggers=False"
    assert no_llm == [], "an LLM call was made despite brevity_triggers=False"


@pytest.mark.asyncio
async def test_brevity_is_still_computed_and_logged_not_deleted(no_llm):
    """GUARD (green with the mechanism neutered). Inert must mean 'does not
    act', not 'does not run'.

    The word count and band feed `brevity_passed_but_mid_sentence`, which is
    real observability. A flag that skipped the check entirely would pass the
    test above and quietly cost that signal.
    """
    persona = get_persona("lao_tzu")
    _, history = await regenerate_or_trim(
        OVER_BAND, persona, "SYSTEM", "USER", brevity_triggers=False,
    )

    brevity = [r for r in history if r.check_name == "brevity"]
    assert brevity, "brevity was not computed at all"
    assert brevity[0].word_count == len(OVER_BAND.split())
    assert brevity[0].target_band == get_persona(
        "lao_tzu").response_length_words.standard_reply_words
    assert brevity[0].action == CheckAction.REGENERATE, (
        "the check itself must still report what it found — only the caller ignores it"
    )


@pytest.mark.asyncio
async def test_persona_lexicon_still_triggers_when_brevity_is_off(monkeypatch):
    """GUARD (green with the mechanism neutered, per revert-verify). Turning
    brevity off must not turn the persona check off — that is the entire point
    of wiring site 4. It passes either way, so it is evidence about blast
    radius, not that the flag works. The two FIX-PINNING tests above are that.
    """
    persona = get_persona("carl_jung")
    reply = "I spent years at Bollingen, in a tower I built with my own hands."
    calls = []

    async def _clean(*args, **kwargs):
        calls.append(kwargs)
        return "The tower was a necessary descent, not a melancholy one."

    import services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "complete", _clean)

    final, history = await regenerate_or_trim(
        reply, persona, "SYSTEM", "USER", brevity_triggers=False,
    )

    assert calls, "persona lexicon hit did not trigger a regeneration"
    assert final != reply
    assert any(
        r.check_name == "persona_forbidden" and r.action == CheckAction.REGENERATE
        for r in history
    )


@pytest.mark.asyncio
async def test_regeneration_directive_says_nothing_about_length(monkeypatch):
    """FIX-PINNING. `_build_regen_directive` appends a "Your reply was N words"
    clause from the brevity result. With brevity off it must not appear, or the
    model is being pushed on length by a check that is supposed to be inert.
    """
    persona = get_persona("carl_jung")
    reply = "I spent years at Bollingen. " + OVER_BAND  # both a hit AND over band
    seen = {}

    async def _capture(*args, **kwargs):
        seen["system"] = kwargs.get("system", "")
        return "A tower, built by hand, is still a kind of argument."

    import services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "complete", _capture)

    await regenerate_or_trim(
        reply, persona, "SYSTEM", "USER", brevity_triggers=False,
    )

    assert "Bollingen" in seen["system"], "the lexicon hit should be named"
    assert "words" not in seen["system"].lower(), (
        f"brevity leaked into the directive: {seen['system']}"
    )


@pytest.mark.asyncio
async def test_default_still_lets_brevity_gate(monkeypatch):
    """GUARD (green before and after). The default is unchanged, which is what
    keeps `scripts/voice_test_socrates.py` and the 112 pre-existing tests
    honest. Same input, flag omitted, must regenerate.
    """
    persona = get_persona("lao_tzu")

    async def _short(*args, **kwargs):
        return "The grip is the wound now."

    import services.llm_client as llm_mod
    monkeypatch.setattr(llm_mod.llm_client, "complete", _short)

    final, _ = await regenerate_or_trim(OVER_BAND, persona, "SYSTEM", "USER")
    assert final != OVER_BAND, "brevity should still gate when the flag is absent"
