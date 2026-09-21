"""Pins two classes of defect in text the model reads on every turn.

WHY THIS FILE EXISTS. `sentence_structure`, `system_fragment` and
`forbidden_phrases` are all injected into the assembled system prompt
(`prompts/system_base.jinja2:18,21,25`). A wrong quotation in any of them is not
a documentation error — it is an instruction to the model, delivered on every
request. Two were shipped:

  1. `fortuna favours the bold` is VIRGIL (Aeneid X: "audentis Fortuna iuvat"),
     not Machiavelli. A persona whose own anti_flexing response_rule instructs
     him to correct the ends-justify-the-means misattribution cannot himself be
     primed with one.
  2. `better feared than hated` garbles Prince ch. 17. The dichotomy is feared
     vs LOVED ("it is much safer to be feared than loved"); hatred is the thing
     to avoid entirely ("he at any rate avoids hatred"), not the opposite pole.

TWO KINDS OF TEST LIVE HERE, and they are labelled because the difference
matters when reading a run:

  FIX-PINNING tests fail against the code as it was before this change. They are
  the ones that prove the fix landed.
  GUARD tests pass both before and after. They pin a decision (Jung's entry
  stays) or a standing property (Lao Tzu keeps New Age coverage) that a later
  edit could quietly break. A guard passing before the fix is expected and is
  NOT evidence the fix works — see the FIX-PINNING set for that.

Run: cd apps/api && pytest tests/test_prompt_text_attribution.py -v
"""
import pytest

from personas import get_persona
from services.prompt_builder import PromptBuilder


@pytest.fixture
def builder():
    return PromptBuilder()


def _assembled(builder, slug: str) -> str:
    """The prompt as the model receives it, not the raw config field.

    Deliberately goes through build_system: the defect was in fields that only
    reach the model after template assembly, so asserting on the dataclass
    attribute would test a different thing than the one that broke.
    """
    return builder.build_system(persona=get_persona(slug))


# ── FIX-PINNING — these fail against the pre-fix tree ─────────────────────────

VIRGIL_VARIANTS = (
    "fortuna favours the bold",
    "fortuna favors the bold",
    "fortune favours the bold",
    "fortune favors the bold",
)


def test_machiavellis_prompt_carries_the_virgil_line_only_as_a_counterexample(builder):
    """FIX-PINNING. 'fortuna favours the bold' is Virgil (Aeneid X), not
    Machiavelli, and must not appear in anything that INSTRUCTS the model.

    It legitimately survives in one place: the WRONG half of a
    voice_calibration_example (`niccolo_machiavelli.py:100`), which exists to
    show the model the caricature it must avoid. Deleting it there would weaken
    the calibration, so the assertion is scoped rather than blanket — every
    occurrence must sit on a `WRONG:` line.

    A blanket "not in prompt" assertion was tried first and failed against the
    FIXED tree for exactly this reason. Recorded here because the assembled
    prompt deliberately contains bad text, which makes whole-prompt substring
    assertions the wrong instrument for this class of defect.
    """
    prompt = _assembled(builder, "niccolo_machiavelli")
    offenders = [
        line for line in prompt.splitlines()
        if any(v in line.lower() for v in VIRGIL_VARIANTS)
        and not line.lstrip().startswith("WRONG:")
    ]
    assert offenders == [], f"Virgil line present outside a WRONG exemplar: {offenders}"


def test_machiavellis_instruction_fields_do_not_carry_the_virgil_line(builder):
    """FIX-PINNING. The two fields the defect actually lived in, asserted
    directly so the scoping above cannot hide a regression in either.
    """
    p = get_persona("niccolo_machiavelli")
    for field_name in ("sentence_structure", "system_fragment"):
        text = getattr(p, field_name).lower()
        for variant in VIRGIL_VARIANTS:
            assert variant not in text, f"{field_name} still carries {variant!r}"


def test_machiavellis_prompt_does_not_garble_the_feared_loved_dichotomy(builder):
    """FIX-PINNING. Prince ch. 17 contrasts feared with LOVED, not with hated."""
    prompt = _assembled(builder, "niccolo_machiavelli").lower()
    assert "feared than hated" not in prompt


def test_machiavellis_prompt_states_the_real_dichotomy(builder):
    """FIX-PINNING. The correction must be present, not merely the error absent.

    Without this, deleting the clause outright would also pass the two tests
    above while losing the aphorism the persona is supposed to carry.
    """
    prompt = _assembled(builder, "niccolo_machiavelli").lower()
    assert "feared than loved" in prompt


def test_lao_tzu_does_not_forbid_the_bare_word_energy(builder):
    """FIX-PINNING. UAT2-001 Ruling C removed `energy` from the universal
    lexicon because word boundaries cannot save a token that IS an ordinary
    English word. forbidden_phrases is a SECOND path that Ruling C did not
    touch, and Lao Tzu was the only persona still carrying the bare token there.
    """
    phrases = get_persona("lao_tzu").forbidden_phrases
    assert "energy" not in [p.strip().lower() for p in phrases]


def test_lao_tzu_still_forbids_the_new_age_energy_phrases(builder):
    """FIX-PINNING. The collision is removed by narrowing, not by dropping the
    register: the New Age sense stays covered in the one live mechanism.
    """
    lowered = [p.strip().lower() for p in get_persona("lao_tzu").forbidden_phrases]
    assert "your energy" in lowered
    assert "energy field" in lowered


# ── GUARDS — expected to pass before AND after; they pin decisions ────────────

def test_lao_tzus_prompt_keeps_the_rest_of_the_new_age_register(builder):
    """GUARD. The argument for removing the bare token is that these four
    remain. If a later edit thins them out, the argument stops holding.
    """
    prompt = _assembled(builder, "lao_tzu").lower()
    for phrase in ("manifest", "vibration", "the universe is telling you", "trust the process"):
        assert phrase in prompt, f"lao_tzu prompt no longer forbids {phrase!r}"


def test_jungs_energy_entry_is_left_exactly_as_it_was(builder):
    """GUARD. Founder ruling 2026-09-21: Jung's entry stays untouched.

    It is NOT the bare word and NOT prompt-injected — it sits in
    forbidden_lexicon_persona_specific, which reaches the model through nothing.
    It is also unmatchable as written (see the sibling test), and its real fix
    belongs to UAT2-004 — making check_persona_forbidden run at all — not here.
    """
    lex = get_persona("carl_jung").forbidden_lexicon_persona_specific
    assert '"energy" (as adjective)' in lex.phrases


def test_jung_never_forbade_the_bare_word_in_his_prompt(builder):
    """GUARD. Jung's system_fragment instructs him to reframe via 'the energy
    beneath the complaint'. A working bare-`energy` ban would have contradicted
    his own instruction. It never did, because the entry is in the other list.
    """
    phrases = [p.strip().lower() for p in get_persona("carl_jung").forbidden_phrases]
    assert "energy" not in phrases


def test_jungs_energy_entry_cannot_match_any_real_use_of_the_word(builder):
    """GUARD, and the evidence for the ruling. The entry is an annotation to a
    human — quote marks and parenthetical included — so the matcher can only
    fire on a reply containing that literal string.
    """
    from services.postprocessing_service import check_persona_forbidden

    jung = get_persona("carl_jung")
    for reply in (
        "The energy beneath the complaint is worth noticing.",
        "Your energy is blocked.",
        "There is an energy here.",
    ):
        result = check_persona_forbidden(reply, jung)
        matched = [h.matched_text for h in result.hits]
        assert '"energy" (as adjective)' not in matched, (
            f"entry unexpectedly fired on {reply!r} — if this now matches, the "
            f"ruling that it is inert no longer holds"
        )
