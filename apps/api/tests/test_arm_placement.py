"""Arms H1 / H2 — the SAME directive text, moved.

The placement experiment exists because of MODEL-001: Haiku substantially
ignores a directive appended last. Across three arms its in-band rate went 43%
(arm B) -> 14% (B3), and B3's explicit "about N words" made it WORSE, which is
not what a model reading the instruction would do. Deep mode is the sharper
form: 31 of 33 deep replies over the reflective ceiling.

So the hypothesis under test is POSITION, and the whole value of the arms
depends on the TEXT being untouched. That is what this file pins: H1 is
byte-identical to B3 with the directive moved to the front, and H2 is H1 with a
second copy appended. If someone edits the wording to "help", the experiment
stops measuring placement and these tests fail instead.

No API calls. Run: cd apps/api && pytest tests/test_arm_placement.py -v
"""
import pytest

from evals import arm_b, arm_b3, harness
from evals.prompt_set import build_samples
from personas import PERSONA_REGISTRY, get_persona

MSG = next(s.user_message for s in build_samples() if s.problem_id.startswith("P01"))


@pytest.fixture(autouse=True)
def _no_bridge(monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_h1_is_b3_with_the_directive_moved_to_the_top(slug, deep):
    """Same bytes, different order — and therefore the same input token count."""
    p = get_persona(slug)
    base, _ = harness.assemble_system(p, MSG, deep=deep, arm="baseline")
    h1, _ = harness.assemble_system(p, MSG, deep=deep, arm="h1")
    block = arm_b3.directive(slug, deep=deep, first_message=True)
    assert h1 == block + "\n\n" + base

    b3, _ = harness.assemble_system(p, MSG, deep=deep, arm="b3")
    assert len(h1) == len(b3), "H1 must cost exactly what B3 cost"
    assert sorted(h1) == sorted(b3)


@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_h2_is_h1_plus_the_same_block_appended(slug, deep):
    p = get_persona(slug)
    h1, _ = harness.assemble_system(p, MSG, deep=deep, arm="h1")
    h2, _ = harness.assemble_system(p, MSG, deep=deep, arm="h2")
    block = arm_b3.directive(slug, deep=deep, first_message=True)
    assert h2 == h1 + "\n\n" + block
    assert h2.count(block) == 2, "H2 is top AND last, exactly twice"


@pytest.mark.parametrize("arm", ["h1", "h2"])
def test_the_arms_start_with_the_directive_not_the_persona(arm):
    h, _ = harness.assemble_system(get_persona("socrates"), MSG, deep=False, arm=arm)
    assert h.startswith("FIRST MESSAGE\nWrite between ")


@pytest.mark.parametrize("arm", ["h1", "h2"])
def test_the_wording_is_untouched(arm):
    """The experiment is about position. Any edit to the text makes the two arms
    incomparable with the three already-stored runs."""
    from services import reply_directive as rd
    h, _ = harness.assemble_system(get_persona("socrates"), MSG, deep=False, arm=arm)
    assert rd.CHALLENGE in h
    assert rd.REGISTER in h
    assert rd.CONCEAL_BAN in h


def test_the_deep_path_carries_three_length_sentences_in_h2(monkeypatch):
    """STATED, NOT ACCIDENTAL. Founder accepted this for the experiment.

    Deep already carries two by decision (_deepen_directive + the DEEP block);
    H2 appends a third copy. All three cite reflective_reply_max_words, so it
    stays redundancy rather than contradiction — and this test is what keeps it
    that way if a band moves.
    """
    import re
    for slug, p in PERSONA_REGISTRY.items():
        h2, _ = harness.assemble_system(p, MSG, deep=True, arm="h2")
        ceiling = p.response_length_words.reflective_reply_max_words
        cited = {int(m) for m in re.findall(r"Write between \d+ and (\d+) words", h2)}
        cited |= {int(m) for m in re.findall(r"up to about (\d+) words", h2)}
        assert cited == {ceiling}, (slug, cited, ceiling)


def test_the_placement_arms_are_registered():
    assert "h1" in arm_b.ARMS and "h2" in arm_b.ARMS


# ── the plan restriction these arms run under ───────────────────────────────

def test_plans_restricts_to_one_model():
    """H1/H2 are Haiku-only. A bug here doubles the bill and re-measures Sonnet,
    whose numbers are already locked."""
    free = [t for t in harness.ARMS_BY_PLAN if t[1] == "free"]
    assert len(free) == 1 and free[0][2] == harness.MODEL_FREE


def test_an_unknown_plan_refuses_rather_than_running_both():
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(harness.generate_all(build_samples()[:1], plans=("premium",)))
