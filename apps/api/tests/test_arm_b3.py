"""Arm B3 — arm B verbatim, plus exactly three changes, and a prompt-level ban.

THE CENTRAL TEST IN THIS FILE DERIVES B3 FROM ARM B. "Verbatim with exactly
these changes" is a claim, and a claim about text is the kind this project keeps
finding to be false a rotation later. So the three substitutions are data, the
test applies them to arm_b's strings, and asserts the result equals arm_b3's. An
edited comma fails CI instead of quietly making the brief untrue.

No API calls.

Run: cd apps/api && pytest tests/test_arm_b3.py -v
"""
import pytest

from evals import arm_b, arm_b2, arm_b3, harness, run as runner
from evals.prompt_set import build_samples
from personas import PERSONA_REGISTRY, get_persona

MSG = next(s.user_message for s in build_samples() if s.problem_id.startswith("P01"))
DASH = chr(8212)


def _derive(src: str, *, deep: bool) -> str:
    """arm B text -> shipped text, by exactly the documented substitutions.

    The register clause reaches ALL THREE variants (founder ruling, after the
    blind3 gate cleared). In FIRST_MESSAGE it REPLACES "Plain, intelligent
    language"; STANDARD and DEEP had nothing to replace, so it is inserted
    before their closing clause. Those two were never sampled by the harness —
    every §8.2 sample is a first message — so they ship on FIRST_MESSAGE's
    numbers plus one unmeasured sentence each.
    """
    out = src.replace(arm_b3.REGISTER_OLD, arm_b3.REGISTER_NEW)
    out = out.replace(arm_b3.CONCEAL_END, arm_b3.CONCEAL_END + arm_b3.CHALLENGE)
    if "Prefer clear speech" in out:
        out = out.replace("Prefer clear speech",
                          arm_b3.REGISTER_NEW + "; prefer clear speech")
    elif "no decorative profundity" in out:
        out = out.replace("Keep your own voice; no decorative profundity.",
                          "Keep your own voice. " + arm_b3.REGISTER_NEW
                          + "; no decorative profundity.")
    if deep:
        # production names the deep placeholders lo/hi/target like the others;
        # arm B used deep_lo/deep_hi. Normalise before comparing, so the test
        # measures the TEXT rather than a rename.
        out = out.replace("{deep_lo}", "{lo}").replace("{deep_hi}", "{hi}")
        out = out.replace("Write between {lo} and {hi} words.",
                          "Write between {lo} and {hi} words " + DASH + " about {target}.")
    else:
        out = out.replace("Write between {lo} and {hi} words.",
                          "Write between {lo} and {hi} words " + DASH + " about {target}.")
    return out


@pytest.mark.parametrize("name,deep", [("FIRST_MESSAGE", False), ("STANDARD", False),
                                       ("DEEP", True)])
def test_b3_is_arm_b_with_exactly_three_substitutions(name, deep):
    assert getattr(arm_b3, name) == _derive(getattr(arm_b, name), deep=deep)


def test_the_register_change_lands_in_all_three_variants():
    """Founder ruling after the blind3 gate cleared. STANDARD and DEEP had
    nothing to replace, so the clause is INSERTED there — and neither path was
    sampled by the harness, which reads first messages only."""
    for text in (arm_b3.FIRST_MESSAGE, arm_b3.STANDARD, arm_b3.DEEP):
        assert arm_b3.REGISTER_NEW in text
    assert arm_b3.REGISTER_OLD not in arm_b3.FIRST_MESSAGE


def test_every_registered_persona_yields_a_directive():
    """The graceful-degradation path must only ever fire on mocks. If a real
    persona returns "", reply_directive logs it as an error — and a reply ships
    with no length or stance rule at all."""
    from services import reply_directive as rd
    for slug, p in PERSONA_REGISTRY.items():
        for kw in (dict(first_message=True, deep=False),
                   dict(first_message=False, deep=False),
                   dict(first_message=True, deep=True)):
            assert rd.directive(p, **kw), (slug, kw)


def test_the_two_deep_length_sentences_cite_the_same_ceiling():
    """The deep path carries TWO length sentences, by decision.

    `_deepen_directive` says "up to about N words"; reply_directive's DEEP block
    says "Write between M and N words". Both must cite the same N
    (reflective_reply_max_words) — then it is redundancy, which is what arm B3's
    33 deep samples ran. If a future band edit moves one and not the other it
    becomes a contradiction, and this test is what catches that.

    Folding the two together is a logged follow-up, to be measured before ship.
    """
    import re
    from services.conversation_service import _deepen_directive
    from services import reply_directive as rd

    for slug, p in PERSONA_REGISTRY.items():
        ceiling = p.response_length_words.reflective_reply_max_words
        deepen = _deepen_directive(p)
        block = rd.directive(p, first_message=True, deep=True)

        from_deepen = int(re.search(r"up to about (\d+) words", deepen).group(1))
        from_block = int(re.search(r"Write between \d+ and (\d+) words", block).group(1))

        assert from_deepen == ceiling, slug
        assert from_block == ceiling, slug
        assert from_deepen == from_block, (
            f"{slug}: the two deep length sentences disagree "
            f"({from_deepen} vs {from_block}) — redundancy has become contradiction"
        )


def test_deep_floor_matches_the_arm_that_was_run():
    """Pinned against arm B3's bands. A drift here means production sends a deep
    range no run ever measured."""
    from services.reply_directive import DEEP_FLOOR
    assert set(DEEP_FLOOR) == set(arm_b.BANDS)
    for slug, b in arm_b.BANDS.items():
        assert DEEP_FLOOR[slug] == b["deep"][0], slug
        assert (PERSONA_REGISTRY[slug].response_length_words.reflective_reply_max_words
                == b["deep"][1]), slug


@pytest.mark.parametrize("text", [arm_b3.FIRST_MESSAGE, arm_b3.STANDARD, arm_b3.DEEP])
def test_challenge_not_speculate_is_in_all_three(text):
    assert arm_b3.CHALLENGE.strip() in text


# ── what B3 must NOT have taken from B2 ─────────────────────────────────────

@pytest.mark.parametrize("text", [arm_b3.FIRST_MESSAGE, arm_b3.STANDARD, arm_b3.DEEP])
def test_b2s_question_rule_is_withdrawn(text):
    """B2's rule moved the metric (Sonnet 88% -> 52% ending on a question) and
    the reader still preferred arm B, 16 votes to 6. Of the six B2 replies the
    reader DID prefer, all six end on a question."""
    assert "the last sentence is a statement" not in text


@pytest.mark.parametrize("text", [arm_b3.FIRST_MESSAGE, arm_b3.STANDARD])
def test_arm_bs_own_question_wording_survives(text):
    """Arm B's sentence is part of the base, not part of the withdrawn rule."""
    assert "usually one natural, answerable question" in text
    assert "is never a closing seal" in text


@pytest.mark.parametrize("text", [arm_b3.FIRST_MESSAGE, arm_b3.STANDARD])
def test_b2s_varied_stance_sentence_is_not_in_b3(text):
    assert "Do not reach for the same opening every time" not in text


# ── the prompt-level ban ────────────────────────────────────────────────────

def test_the_ban_is_in_every_personas_forbidden_phrases():
    for slug, p in PERSONA_REGISTRY.items():
        for phrase in arm_b3.NOTICE_BAN:
            assert phrase in p.forbidden_phrases, (slug, phrase)


def test_the_ban_reaches_the_prompt(monkeypatch):
    """forbidden_phrases renders as "DO NOT USE: ..." in system_base.jinja2.
    Prompt level, not the post-check."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    system, _ = harness.assemble_system(get_persona("socrates"), MSG, deep=False, arm="b3")
    assert "DO NOT USE:" in system
    for phrase in arm_b3.NOTICE_BAN:
        assert phrase in system


def test_the_ban_did_not_touch_the_post_check():
    """Nothing in postprocessing was changed: these are discouraged in the
    prompt, never stripped or regenerated."""
    from services.postprocessing_service import check_persona_forbidden
    p = get_persona("socrates")
    r = check_persona_forbidden("What I notice is that you keep waiting.", p)
    assert r.passed, "the notice ban must NOT be a post-check rule"


# ── assembly ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", sorted(PERSONA_REGISTRY))
@pytest.mark.parametrize("deep", [False, True])
def test_b3_appends_its_directive_last(slug, deep, monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    p = get_persona(slug)
    base, _ = harness.assemble_system(p, MSG, deep=deep, arm="baseline")
    b3, _ = harness.assemble_system(p, MSG, deep=deep, arm="b3")
    assert b3 == base + "\n\n" + arm_b3.directive(slug, deep=deep, first_message=True)


def test_b3_reuses_the_locked_bands_and_targets():
    assert arm_b3.BANDS is arm_b.BANDS
    assert arm_b3.TARGETS is arm_b2.TARGETS


# ── the manifest must be able to tell the trees apart ───────────────────────

def test_persona_config_hash_covers_forbidden_phrases():
    """The first version hashed system_fragment plus three band numbers and
    missed forbidden_phrases, so adding the B3 ban left it byte-identical and
    B2-clean and B3 would have been indistinguishable in their manifests. It
    now hashes the RENDERED prompt, which covers whatever the template reads."""
    p = get_persona("socrates")
    saved = list(p.forbidden_phrases)
    before = runner.persona_config_hash()
    try:
        p.forbidden_phrases = [x for x in saved if x != "what I notice"]
        assert runner.persona_config_hash() != before
    finally:
        p.forbidden_phrases = saved
    assert runner.persona_config_hash() == before


def test_persona_config_hash_covers_the_bands_too():
    """They do not reach the prompt, but they drive check_brevity and
    _compute_max_tokens, so two runs differing only in bands are scored
    differently and must not collide."""
    spec = get_persona("socrates").response_length_words
    saved = spec.standard_reply_words
    before = runner.persona_config_hash()
    try:
        spec.standard_reply_words = (1, 2)
        assert runner.persona_config_hash() != before
    finally:
        spec.standard_reply_words = saved
    assert runner.persona_config_hash() == before


def test_persona_config_hash_is_not_date_dependent():
    """build_system stamps date.today(); the hash must not change overnight."""
    assert runner.persona_config_hash() == runner.persona_config_hash()
    from services.prompt_builder import prompt_builder
    rendered = prompt_builder.build_system(persona=get_persona("socrates"))
    assert "Current date:" in rendered, "fixture drift: the date line moved"
