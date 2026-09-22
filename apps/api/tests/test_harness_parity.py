"""The harness measures PRODUCTION'S prompt, byte for byte — or it measures nothing.

WHY THIS TEST IS THE LOAD-BEARING ONE IN THE HARNESS. Every number a run
produces is a statement about the prompt that was sent. If the harness assembles
that prompt even slightly differently from `conversation_service.stream_response`
— one directive in the wrong order, one block omitted, one appended newline —
the run still completes, the CSVs still fill, the rates still look plausible, and
every one of them is about a prompt the product never sends. Nothing in the
output would say so.

So the assertions below rebuild the first-turn prompt INLINE, spelling out the
pieces and their order as conversation_service.py:816-936 does, and compare it to
what `evals.harness.assemble_system` returns. The inline version is deliberately
written out rather than factored into a helper: a helper shared with the harness
would make this test tautological, and the thing being pinned is precisely that
two independent spellings agree.

It also pins the NEGATIVES — the directives production does NOT apply on a first
turn. Those are the easy mistake: adding the adaptive-length directive to the
harness "for realism" would silently move every brevity number.

NO API CALLS. This is string assembly; it belongs in CI, and it is the only part
of the harness that runs there.

Run: cd apps/api && pytest tests/test_harness_parity.py -v
"""
import pytest

from evals import harness
from evals.prompt_set import DEEP_PROBLEM_IDS, build_samples, prompt_set_hash
from personas import PERSONA_REGISTRY, get_persona
from services.conversation_service import (
    ADAPTIVE_LENGTH_LONG_MIN_WORDS,
    MODEL_FREE,
    MODEL_PRO,
    SEEDED_OPENING_DIRECTIVE,
    _deepen_directive,
    _length_directive_for_input,
)
from services.phenomenology_bridge_service import phenomenology_bridge_service
from services.prompt_builder import CACHE_SPLIT_SENTINEL, prompt_builder

SLUGS = sorted(PERSONA_REGISTRY)

# Real prompt-set text, not a paraphrase. A hand-written fixture drifts from the
# data it is meant to stand for, and the first version of this file did exactly
# that: it paraphrased P01 down to 35 words, which silently changed the sample
# from one adaptive-length tier to another and made the negative test below
# assert nothing.
_SAMPLES = build_samples()
MSG = next(s.user_message for s in _SAMPLES if s.problem_id.startswith("P01"))
LONG_MSG = max((s.user_message for s in _SAMPLES), key=lambda m: len(m.split()))


def _inline_production_system(persona, user_message, *, deep, bridge_on):
    """conversation_service.py:816-936, first turn, written out longhand."""
    bridge = None
    if bridge_on:
        bridge = phenomenology_bridge_service.lookup(
            user_message=user_message, persona_slug=persona.slug,
        )
    system = prompt_builder.build_system(
        persona=persona,
        memories=[],
        passages=[],
        phenomenology_bridge=bridge,
        profile=None,
        include_cache_sentinel=True,
    )
    if deep:
        system = system + "\n\n" + _deepen_directive(persona)
    return system


# ── parity, both modes, both bridge states ───────────────────────────────────

@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("deep", [False, True])
@pytest.mark.parametrize("bridge_on", [False, True])
def test_assembled_prompt_is_byte_identical_to_production(
    slug, deep, bridge_on, monkeypatch
):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", bridge_on)
    persona = get_persona(slug)

    expected = _inline_production_system(
        persona, MSG, deep=deep, bridge_on=bridge_on,
    )
    got, _bridge_term = harness.assemble_system(persona, MSG, deep=deep)

    assert got == expected, (
        f"{slug} deep={deep} bridge={bridge_on}: the harness and production "
        f"disagree about the prompt. Every number from a run made with this "
        f"harness would be about a prompt the product does not send."
    )


@pytest.mark.parametrize("slug", SLUGS)
def test_deep_appends_exactly_the_production_directive(slug, monkeypatch):
    """Not 'contains the directive' — the exact separator and position."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    persona = get_persona(slug)
    plain, _ = harness.assemble_system(persona, MSG, deep=False)
    deep, _ = harness.assemble_system(persona, MSG, deep=True)
    assert deep == plain + "\n\n" + _deepen_directive(persona)


# ── the negatives: what production does NOT apply on a first turn ────────────

def test_the_adaptive_length_directive_is_never_applied(monkeypatch):
    """production gates it behind `history_len > 1` (conversation_service.py:931).

    This matters more than it looks: 9 of the 10 eval problems are 50-65 words,
    which is the LONG tier, so a harness that applied it would attach an explicit
    word range to nine-tenths of the corpus and move every brevity number.
    """
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    persona = get_persona("lao_tzu")

    # Guard the guard: if LONG_MSG stopped being long-tier this test would pass
    # vacuously, asserting the absence of a directive that was never going to
    # appear.
    assert len(LONG_MSG.split()) >= ADAPTIVE_LENGTH_LONG_MIN_WORDS
    directive = _length_directive_for_input(LONG_MSG, persona)
    assert directive is not None

    for deep in (False, True):
        system, _ = harness.assemble_system(persona, LONG_MSG, deep=deep)
        assert directive not in system
        assert "LENGTH FOR THIS REPLY" not in system


def test_the_seeded_opening_directive_is_never_applied(monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    system, _ = harness.assemble_system(get_persona("socrates"), MSG, deep=False)
    assert SEEDED_OPENING_DIRECTIVE not in system
    assert "CROSS-MIND" not in system.upper()


# ── the cache sentinel round-trip ────────────────────────────────────────────

@pytest.mark.parametrize("slug", SLUGS)
def test_split_for_cache_reconstructs_the_prompt_byte_for_byte(slug, monkeypatch):
    """The harness stores the sentinel-free string as 'what was sent'. That is
    only true because prefix + suffix == the sentinel-free render."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    persona = get_persona(slug)
    system, _ = harness.assemble_system(persona, MSG, deep=False)
    assert system.count(CACHE_SPLIT_SENTINEL) == 1

    blocks = prompt_builder.split_system_for_cache(system)
    assert isinstance(blocks, list) and len(blocks) == 2
    assert blocks[0]["text"] + blocks[1]["text"] == system.replace(
        CACHE_SPLIT_SENTINEL, ""
    )


def test_the_harness_uses_productions_own_model_constants():
    """Not string literals. A model rename in conversation_service must not leave
    the harness measuring the previous model."""
    assert harness.ARMS_BY_PLAN == (
        ("free", "free", MODEL_FREE),
        ("pro", "pro", MODEL_PRO),
    )


# ── the prompt set ───────────────────────────────────────────────────────────

def test_the_set_is_110_samples_33_of_them_deep():
    samples = build_samples()
    assert len(samples) == 110, "10 problems x 11 personas (founder-locked)"
    assert len(PERSONA_REGISTRY) == 11
    deep = [s for s in samples if s.deep]
    assert len(deep) == 33, "3 deep problems x 11 personas"
    assert {s.problem_id for s in deep} == set(DEEP_PROBLEM_IDS)


def test_every_sample_id_is_unique():
    ids = [s.sample_id for s in build_samples()]
    assert len(set(ids)) == len(ids)


def test_every_persona_gets_every_problem():
    samples = build_samples()
    for slug in PERSONA_REGISTRY:
        assert len([s for s in samples if s.persona_slug == slug]) == 10


def test_prompt_set_hash_is_stable_and_content_sensitive():
    first = prompt_set_hash()
    assert first == prompt_set_hash()
    assert len(first) == 16


def test_every_sample_assembles_and_carries_its_personas_fragment(monkeypatch):
    """The cheap end-to-end: all 110 build, and each one actually contains the
    persona it claims. A registry-lookup slip would otherwise produce 110 valid
    prompts attributed to the wrong minds."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", True)
    for s in build_samples():
        persona = PERSONA_REGISTRY[s.persona_slug]
        system, _ = harness.assemble_system(
            persona, s.user_message, deep=s.deep,
        )
        assert persona.system_fragment in system
        assert (_deepen_directive(persona) in system) is s.deep
