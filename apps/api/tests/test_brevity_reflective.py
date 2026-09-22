"""BREV-001 step 1 — check_brevity and _compute_max_tokens learn the mode.

WHY THIS FILE EXISTS. `check_brevity` took only a POSITION ("first_message" |
"mid_session" | "late_session") and had no path to `reflective_reply_max_words`
at all. Deep-mode and go_deeper replies are instructed up to that band by
`_deepen_directive` — 2.17x-2.89x the standard ceiling — so scoring them
against the standard band reports a length failure the prompt itself asked for.
Measured over 50 production go_deeper replies: 15 over-ceiling become 3.

WHERE THE FIXTURES COME FROM. Real (persona, word_count) pairs from the
UAT2-004 dry run over all 826 Oregon assistant replies, 2026-04-26 to
2026-09-21, recomputed against PERSONA_REGISTRY rather than transcribed — the
transcription is what produced BREV-001's own 13-vs-12 correction.

THE REPLY BODIES ARE MEANINGLESS, AND THAT IS THE POINT. `check_brevity` reads
`len(reply.split())` and nothing else. These fixtures are N repetitions of a
placeholder word. Dressing them up as prose would imply the text matters to the
assertion; it does not, and a later reader would waste time looking for a signal
in the sentences.

Run: cd apps/api && pytest tests/test_brevity_reflective.py -v
"""
import pytest

from personas import get_persona
from services.postprocessing_service import (
    CheckAction,
    check_brevity,
    regenerate_or_trim,
    _compute_max_tokens,
)


def _reply(n: int) -> str:
    """A reply of exactly n words. The words carry no meaning — see module docstring."""
    return " ".join(["word"] * n)


# ── The 12 that must now PASS ────────────────────────────────────────────────
# Each is over its persona's STANDARD ceiling (lao_tzu 45, socrates 55) and
# under its REFLECTIVE ceiling (130 / 120). Before this change every one of them
# was a spurious REGENERATE on a reply the prompt had asked to be long.
REFLECTIVE_NOW_PASSING = (
    [("lao_tzu", w) for w in (51, 56, 62, 64, 72, 89, 112, 128)]
    + [("socrates", w) for w in (59, 62, 71, 88)]
)

# ── The 3 that must STILL FIRE ───────────────────────────────────────────────
# Over the reflective ceiling too. The fix must not become "deep mode has no
# ceiling".
REFLECTIVE_STILL_FIRING = [
    ("lao_tzu", 143),          # > 130
    ("marcus_aurelius", 127),  # > 120
    ("socrates", 176),         # > 120
]


@pytest.mark.parametrize("slug,words", REFLECTIVE_NOW_PASSING)
def test_reflective_reply_within_deep_band_passes(slug, words):
    persona = get_persona(slug)
    r = check_brevity(_reply(words), persona, "mid_session", reflective=True)
    assert r.passed is True
    assert r.action == CheckAction.PASS
    assert r.word_count == words
    assert r.target_band == (0, persona.response_length_words.reflective_reply_max_words)


@pytest.mark.parametrize("slug,words", REFLECTIVE_NOW_PASSING)
def test_the_same_reply_fails_without_the_flag(slug, words):
    """Pins that these fixtures are the fix's evidence, not incidental passes.

    Without `reflective=True` every one of them is over the standard ceiling and
    REGENERATEs. That asymmetry — red here before the change, green in the test
    above only after it — is what makes the fix legible to a later reader.
    """
    persona = get_persona(slug)
    r = check_brevity(_reply(words), persona, "mid_session")
    assert r.passed is False
    assert r.target_band == persona.response_length_words.standard_reply_words


@pytest.mark.parametrize("slug,words", REFLECTIVE_STILL_FIRING)
def test_reflective_reply_over_deep_band_still_fires(slug, words):
    persona = get_persona(slug)
    r = check_brevity(_reply(words), persona, "mid_session", reflective=True)
    assert r.passed is False
    assert r.action == CheckAction.REGENERATE
    assert r.word_count == words


# ── first_message keeps priority over reflective ─────────────────────────────

@pytest.mark.parametrize("slug", ["socrates", "lao_tzu", "marcus_aurelius"])
def test_first_message_cap_wins_over_reflective(slug):
    """A deep-mode FIRST reply is instructed to the reflective band and must
    still keep its first-message cap. Reachable, not hypothetical: up to 27 of
    182 first replies sit in deep-mode conversations. This is the reason
    `reflective` is a separate flag and not a fourth conversation_position.
    """
    persona = get_persona(slug)
    spec = persona.response_length_words
    fm = spec.first_message_max_words
    assert fm is not None and spec.reflective_reply_max_words > fm

    r = check_brevity(_reply(50), persona, "first_message", reflective=True)
    assert r.target_band == (0, fm), "reflective must not override the first-message cap"
    assert r.passed is (50 <= fm)


def test_reflective_is_ignored_when_the_persona_has_no_deep_band():
    """Graceful degradation: reflective=True with no reflective_reply_max_words
    falls through to the standard band rather than erroring or skipping."""
    from personas._models import ResponseLengthSpec
    persona = get_persona("marcus_aurelius")
    original = persona.response_length_words
    persona.response_length_words = ResponseLengthSpec(standard_reply_words=(20, 55))
    try:
        r = check_brevity(_reply(100), persona, "mid_session", reflective=True)
        assert r.target_band == (20, 55)
        assert r.passed is False
    finally:
        persona.response_length_words = original


# ── _compute_max_tokens carries the same branch ──────────────────────────────

@pytest.mark.parametrize("slug", ["lao_tzu", "socrates", "marcus_aurelius", "george_orwell"])
def test_compute_max_tokens_uses_the_deep_band_when_reflective(slug):
    """Without this branch a regenerated reflective reply is capped at
    standard_ceiling x 1.4 x headroom. For Lao Tzu that is 88 tokens against a
    ~182-token target — truncation mid-sentence, not a length failure.
    """
    persona = get_persona(slug)
    spec = persona.response_length_words

    plain = _compute_max_tokens(persona, "mid_session", 0)
    deep = _compute_max_tokens(persona, "mid_session", 0, reflective=True)

    assert plain == int(spec.standard_reply_words[1] * 1.4 * 1.4)
    assert deep == int(spec.reflective_reply_max_words * 1.4 * 1.4)
    assert deep > int(spec.reflective_reply_max_words * 1.4), "must clear the word target"


def test_compute_max_tokens_first_message_still_wins():
    persona = get_persona("socrates")
    fm = persona.response_length_words.first_message_max_words
    got = _compute_max_tokens(persona, "first_message", 0, reflective=True)
    assert got == int(fm * 1.4 * 1.4)


# ── the flag must not reopen the door brevity_triggers=False closed ──────────

async def test_reflective_does_not_make_brevity_gate(monkeypatch):
    """An over-band reply with no lexicon hit must return BYTE-IDENTICAL with
    zero LLM calls, exactly as tests/test_brevity_inert_in_batch.py asserts —
    and must keep doing so with reflective=True. Brevity staying inert in
    production is the boundary of this change; BREV-001 step 3 owns the rest.
    """
    persona = get_persona("lao_tzu")
    reply = _reply(400)  # far over BOTH the standard (45) and reflective (130) ceilings

    calls = []

    class _Boom:
        async def complete(self, *a, **kw):
            calls.append(kw)
            raise AssertionError("regenerate_or_trim must not call the LLM here")

    import services.llm_client as _llm
    monkeypatch.setattr(_llm, "llm_client", _Boom())

    out, history = await regenerate_or_trim(
        reply, persona, "SYSTEM", "user text",
        brevity_triggers=False, reflective=True,
    )

    assert out == reply
    assert calls == []
    brv = next(r for r in history if r.check_name == "brevity")
    assert brv.action == CheckAction.REGENERATE, "still COMPUTED, just not gating"
    assert brv.target_band == (0, persona.response_length_words.reflective_reply_max_words)
