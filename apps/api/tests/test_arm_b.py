"""Arm B — the directive is founder-approved COPY, and these tests treat it as copy.

The text in evals/arm_b.py was written and approved by the founder after the
blind read. It is not a docstring, it is not guidance, and it is not mine to
improve. The assertions below pin the clauses that carry the ruling, so that a
later tidy-up of wording fails in CI rather than silently changing what the
experiment asks for.

The most important test in the file is the one that asserts arm "baseline"
changes NOTHING. An A/B where the A arm drifted is not an A/B.

No API calls.

Run: cd apps/api && pytest tests/test_arm_b.py -v
"""
import pytest

from evals import arm_b, harness
from evals.prompt_set import build_samples
from personas import PERSONA_REGISTRY, get_persona

MSG = next(s.user_message for s in build_samples() if s.problem_id.startswith("P01"))


# ── the A arm must not move ─────────────────────────────────────────────────

@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_baseline_arm_appends_nothing(slug, deep, monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    persona = get_persona(slug)
    default, _ = harness.assemble_system(persona, MSG, deep=deep)
    explicit, _ = harness.assemble_system(persona, MSG, deep=deep, arm="baseline")
    assert default == explicit


def test_an_unknown_arm_raises_rather_than_silently_running_baseline(monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    with pytest.raises(ValueError, match="unknown arm"):
        harness.assemble_system(get_persona("socrates"), MSG, deep=False, arm="typo")


# ── the B arm appends exactly the directive, last ───────────────────────────

@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_tightened_appends_exactly_the_directive_and_nothing_else(slug, deep, monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    persona = get_persona(slug)
    base, _ = harness.assemble_system(persona, MSG, deep=deep, arm="baseline")
    tight, _ = harness.assemble_system(persona, MSG, deep=deep, arm="tightened")
    expected = arm_b.directive(slug, deep=deep, first_message=True)
    assert tight == base + "\n\n" + expected
    assert tight.rstrip().endswith(expected.rstrip()), "the directive must be LAST"


# ── the numbers ─────────────────────────────────────────────────────────────

def test_every_persona_has_a_band():
    assert set(arm_b.BANDS) == set(PERSONA_REGISTRY)


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
def test_bands_are_ordered_and_deep_is_wider(slug):
    b = arm_b.BANDS[slug]
    assert b["standard"][0] < b["standard"][1]
    assert b["deep"][0] < b["deep"][1]
    assert b["deep"][0] > b["standard"][1], "deep must start above the standard ceiling"


def test_mean_standard_target_matches_the_approval():
    """Two nearby figures, and they are not the same one.

    The UNROUNDED targets average 72.6 (that is the number in the approval).
    The midpoints of the ROUNDED bands average 72.7, because rounding lo and hi
    to 5 independently does not preserve the midpoint. Both are "~73", which is
    what the founder accepted; this pins the second, since the bands are what
    actually ship in the directive.
    """
    mids = [sum(b["standard"]) / 2 for b in arm_b.BANDS.values()]
    assert round(sum(mids) / len(mids), 1) == 72.7


def test_musashi_was_moved_to_the_stoic_group_by_ruling():
    """Founder ruling 2026-09-22. Scaling put him at 75-110/120-180; his shipped
    (30, 75) band is the second widest of the eleven and contradicts
    anchor_cuts_the_unnecessary. Scaling inherits an existing error faithfully,
    so this one is corrected rather than carried."""
    assert arm_b.BANDS["miyamoto_musashi"]["standard"] == (55, 80)
    assert arm_b.BANDS["miyamoto_musashi"]["deep"] == (85, 130)
    assert arm_b.BANDS["miyamoto_musashi"] == arm_b.BANDS["marcus_aurelius"]


def test_lao_tzu_is_lowest_and_orwell_highest():
    mids = {s: sum(b["standard"]) / 2 for s, b in arm_b.BANDS.items()}
    assert min(mids, key=mids.get) == "lao_tzu"
    assert max(mids, key=mids.get) == "george_orwell"


def test_arm_b_bands_are_all_above_the_shipped_first_message_cap():
    """The direction of arm B is UP, not down — the blind read chose the longer
    reply in 6 of 7 decided pairs. If a band ever falls back under the old cap,
    the arm has quietly become the length-only arm the blind read killed."""
    for slug, b in arm_b.BANDS.items():
        cap = PERSONA_REGISTRY[slug].response_length_words.first_message_max_words
        assert b["standard"][0] > cap, slug


# ── the copy ────────────────────────────────────────────────────────────────

CLAUSES = [
    "never tell them, directly or by implication, that they are hiding, avoiding, "
    "or failing to name something",
    "is never a closing seal",
    "Keep your own voice",
]


@pytest.mark.parametrize("clause", CLAUSES)
def test_the_ruling_clauses_survive_in_first_message_and_standard(clause):
    assert clause in arm_b.FIRST_MESSAGE
    assert clause in arm_b.STANDARD


def test_the_deep_variant_carries_the_concealment_ban_too():
    assert ("Never tell them, directly or by implication, that they are hiding, "
            "avoiding, or failing to name something") in arm_b.DEEP
    assert "never a closing seal" in arm_b.DEEP


def test_interpretation_is_permitted_not_forbidden():
    """Freud and Jung were the only two personas a blind reader identified every
    time, 4/4 each against five personas at 0/4. Their identifiability IS
    interpretation. The rule bans accusing the user of concealment, not reading
    beneath the surface, and an edit that blurs the two is a regression."""
    for text in (arm_b.FIRST_MESSAGE, arm_b.STANDARD):
        assert "You may offer an interpretation" in text
    assert "develop an interpretation" in arm_b.DEEP


def test_the_anti_oracle_clause_is_present_in_every_variant():
    assert "no decorative aphorisms or fortune-cookie phrasing" in arm_b.FIRST_MESSAGE
    assert "Prefer clear speech over poetic or oracular phrasing" in arm_b.STANDARD
    assert "no decorative profundity" in arm_b.DEEP


def test_placeholders_are_all_substituted():
    for slug in PERSONA_REGISTRY:
        for deep in (False, True):
            d = arm_b.directive(slug, deep=deep, first_message=True)
            assert "{" not in d and "}" not in d, (slug, deep)


def test_first_message_and_standard_use_the_same_numbers():
    """Founder ruling: FIRST uses the same range as STANDARD, because the
    separate first_message cap never reached a prompt."""
    for slug in PERSONA_REGISTRY:
        lo, hi = arm_b.BANDS[slug]["standard"]
        assert f"between {lo} and {hi} words" in arm_b.directive(
            slug, deep=False, first_message=True)
        assert f"between {lo} and {hi} words" in arm_b.directive(
            slug, deep=False, first_message=False)
