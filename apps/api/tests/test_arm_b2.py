"""Arm B2 — founder-approved copy, plus the scorers that make it measurable.

Same discipline as test_arm_b.py: the directive is COPY, and the clauses that
carry a ruling are pinned so a later tidy-up fails in CI rather than quietly
changing the experiment.

Two things here are not in the arm B file and matter more:

  - arm B's text must be FROZEN. It has been run, its numbers are on the record,
    and an edit would silently invalidate that run. A test asserts B2 did not
    reach back into it.
  - the stance matcher is now four families, and the NARROW one is kept. Every
    stance figure reported before B2 — baseline 6%, arm B 14% — was measured
    with the observation family alone, and so was the founder's 30-40% target.
    Retiring it would restate history without saying so.

No API calls.

Run: cd apps/api && pytest tests/test_arm_b2.py -v
"""
import pytest

from evals import arm_b, arm_b2, harness, scorers
from evals.prompt_set import build_samples
from personas import PERSONA_REGISTRY, get_persona

MSG = next(s.user_message for s in build_samples() if s.problem_id.startswith("P01"))


# ── arm B must not move ─────────────────────────────────────────────────────

def test_arm_b_text_is_frozen():
    """B2 is a new arm, not an edit of B. Arm B has been run at
    arm_directive_hash 03b6bac216b88c2a and its numbers are reported."""
    assert "never a closing seal" in arm_b.FIRST_MESSAGE
    assert "Plain, intelligent language" in arm_b.FIRST_MESSAGE
    assert "about" not in arm_b.FIRST_MESSAGE.split("words")[0]
    assert "b2" in arm_b.ARMS


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
def test_b2_and_b_are_different_directives(slug):
    assert arm_b2.directive(slug, deep=False) != arm_b.directive(slug, deep=False)
    assert arm_b2.directive(slug, deep=True) != arm_b.directive(slug, deep=True)


def test_baseline_still_appends_nothing(monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    p = get_persona("socrates")
    assert (harness.assemble_system(p, MSG, deep=False)[0]
            == harness.assemble_system(p, MSG, deep=False, arm="baseline")[0])


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_b2_appends_exactly_its_directive_last(slug, deep, monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    p = get_persona(slug)
    base, _ = harness.assemble_system(p, MSG, deep=deep, arm="baseline")
    b2, _ = harness.assemble_system(p, MSG, deep=deep, arm="b2")
    expected = arm_b2.directive(slug, deep=deep, first_message=True)
    assert b2 == base + "\n\n" + expected


# ── the numbers ─────────────────────────────────────────────────────────────

def test_targets_are_midpoints_rounded_to_five_ties_up():
    expected = {"lao_tzu": 55, "marcus_aurelius": 70, "socrates": 70, "epictetus": 70,
                "oscar_wilde": 70, "miyamoto_musashi": 70, "carl_jung": 75,
                "sigmund_freud": 75, "niccolo_machiavelli": 75,
                "simone_de_beauvoir": 85, "george_orwell": 100}
    assert {s: t["standard"] for s, t in arm_b2.TARGETS.items()} == expected
    assert all(t["standard"] % 5 == 0 and t["deep"] % 5 == 0
               for t in arm_b2.TARGETS.values())


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
def test_every_target_sits_inside_its_range(slug):
    for mode in ("standard", "deep"):
        lo, hi = arm_b.BANDS[slug][mode]
        assert lo <= arm_b2.TARGETS[slug][mode] <= hi


def test_b2_reuses_arm_bs_bands_rather_than_redefining_them():
    assert arm_b2.BANDS is arm_b.BANDS


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
def test_the_target_number_reaches_the_directive(slug):
    d = arm_b2.directive(slug, deep=False)
    lo, hi = arm_b.BANDS[slug]["standard"]
    assert f"between {lo} and {hi} words — about {arm_b2.TARGETS[slug]['standard']}" in d


# ── the copy, and the two founder edits ─────────────────────────────────────

ALL_THREE = (arm_b2.FIRST_MESSAGE, arm_b2.STANDARD, arm_b2.DEEP)


@pytest.mark.parametrize("text", ALL_THREE)
def test_challenge_not_speculate_is_present(text):
    """The sentence that separates Beauvoir's bad-faith anchor and Socrates'
    elenchus — challenging a STATED claim — from concealment insinuation."""
    assert ("You may challenge what they have said; do not speculate about what "
            "they have not.") in text


@pytest.mark.parametrize("text", ALL_THREE)
def test_the_question_rule_is_positive_not_negative(text):
    assert "the last sentence is a statement" in text
    assert "never a closing seal" not in text, "arm B's negative made it 15pt worse"


@pytest.mark.parametrize("text", ALL_THREE)
def test_register_names_slang_and_drops_intelligent(text):
    assert "in your own register — never contemporary slang" in text
    assert "Plain, intelligent language" not in text


@pytest.mark.parametrize("text", (arm_b2.FIRST_MESSAGE, arm_b2.STANDARD))
def test_stance_forms_are_named_but_never_quoted(text):
    """Founder edit. 'What I notice' was already 50% of stance hits; offering it
    as example one is how the formula survives being told to vary."""
    assert "a plain observation" in text
    assert "a distinction they have not drawn" in text
    assert "a reading you offer as yours" in text
    for quoted in ("What I notice is", "That is not X", "It reads to me as"):
        assert quoted not in text


@pytest.mark.parametrize("text", ALL_THREE)
def test_the_concealment_ban_survives(text):
    assert "hiding, avoiding, or failing to name something" in text


def test_placeholders_are_substituted():
    for slug in PERSONA_REGISTRY:
        for deep in (False, True):
            d = arm_b2.directive(slug, deep=deep)
            assert "{" not in d and "}" not in d


# ── the scorers ─────────────────────────────────────────────────────────────

def test_the_four_stance_families_each_fire():
    assert scorers.stance_hits("What I notice is the delay.") == ["observation"]
    assert scorers.stance_hits("I read this as fear, not prudence.") == ["reading_as_mine"]
    assert scorers.stance_hits("You're carrying something you did not choose.") \
        == ["direct_claim"]
    assert "distinction" in scorers.stance_hits("Those are two different things.")


def test_reading_as_mine_is_the_clean_before_after():
    """Measured over the 440 completions of baseline + arm B, this family fired
    ZERO times. B2 names it explicitly, so any hit at all is attributable."""
    assert "reading_as_mine" in scorers.STANCE_FAMILIES


def test_opening_present_counts_a_question_or_an_invitation():
    assert scorers.has_opening("What would you risk?")
    assert scorers.has_opening("Tell me what you would risk.")
    assert scorers.has_opening("The harder question is whether you meant it.")
    assert not scorers.has_opening("That is not fraud. It is distance.")


def test_ends_with_question_ignores_trailing_quotes_and_brackets():
    assert scorers.ends_with_question('Do you mean that?"')
    assert scorers.ends_with_question("Do you mean that?")
    assert not scorers.ends_with_question("You asked why? I think not.")


def test_both_stance_rates_are_reported_not_one():
    """The narrow family is kept because every stance figure reported before B2
    was measured with it, and so was the 30-40% target."""
    assert "stance_observation_rate" in scorers.SUMMARY_COLUMNS
    assert "stance_any_rate" in scorers.SUMMARY_COLUMNS
    assert "no_opening_rate" in scorers.SUMMARY_COLUMNS
    assert "ends_q_rate" in scorers.SUMMARY_COLUMNS
