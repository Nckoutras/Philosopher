"""The Listening judge: the quote audit, and the calibration sample.

No API calls. Everything here is the parts that must be right BEFORE money is
spent — the parser that decides what counts as a finding, and the selection rule
that decides what gets judged.

Run: cd apps/api && pytest tests/test_listening_judge.py -v
"""
import collections
import json
from pathlib import Path

import pytest

from evals import listening as L

B3 = Path(__file__).resolve().parent.parent / "evals/results/2026-09-22T12-59_b3"
REPLY = ("You keep saying the launch is next quarter. Three quarters have gone. "
         "That is not a plan slipping; it is a plan doing its job. What would you "
         "lose if it shipped?")


def _j(**over):
    base = {c: {"v": False, "q": ""} for c in L.CRITERIA}
    base.update(over)
    return json.dumps(base)


# ── the quote audit ─────────────────────────────────────────────────────────

def test_all_no_parses_clean():
    v, err = L.parse_verdict(_j(), REPLY)
    assert err == ""
    assert all(v[c][0] is False for c in L.CRITERIA)


def test_a_yes_with_a_verbatim_quote_is_accepted():
    q = "That is not a plan slipping; it is a plan doing its job."
    v, err = L.parse_verdict(_j(c={"v": True, "q": q}), REPLY)
    assert err == ""
    assert v["c"] == (True, q)


def test_a_yes_whose_quote_is_NOT_in_the_reply_is_a_parse_failure():
    """THE POINT OF THE WHOLE MECHANISM. A judge that flags a fault and cannot
    point at the words has not found the fault, and counting it would put
    unfalsifiable rows into the result."""
    v, err = L.parse_verdict(
        _j(a={"v": True, "q": "you are avoiding the real question"}), REPLY)
    assert v == {}
    assert "not verbatim" in err


def test_a_yes_with_no_quote_at_all_is_a_parse_failure():
    v, err = L.parse_verdict(_j(b={"v": True, "q": ""}), REPLY)
    assert v == {} and "no quote" in err


def test_whitespace_reflow_in_a_quote_is_tolerated():
    """A model that re-wraps a line has still quoted the reply. One that
    paraphrases has not, and the test above is what catches that."""
    q = "That is not a plan slipping;\n   it is a plan doing its job."
    v, err = L.parse_verdict(_j(c={"v": True, "q": q}), REPLY)
    assert err == "", err


def test_case_differences_are_tolerated():
    v, err = L.parse_verdict(
        _j(c={"v": True, "q": "THAT IS NOT A PLAN SLIPPING"}), REPLY)
    assert err == ""


def test_a_NO_may_carry_a_stray_quote_without_failing():
    """Only a yes is evidence. A no with leftover text is sloppy, not wrong, and
    failing it would discard a usable row."""
    v, err = L.parse_verdict(_j(d={"v": False, "q": "whatever"}), REPLY)
    assert err == "" and v["d"][0] is False


@pytest.mark.parametrize("bad", [
    "not json at all",
    '{"a":{"v":true,"q":"x"}}',                         # missing criteria
    '{"a":{"v":"yes","q":""},"b":{"v":false,"q":""},'
    '"c":{"v":false,"q":""},"d":{"v":false,"q":""},"e":{"v":false,"q":""}}',
])
def test_malformed_output_is_an_error_not_a_verdict(bad):
    v, err = L.parse_verdict(bad, REPLY)
    assert v == {} and err


def test_a_fenced_code_block_is_unwrapped():
    v, err = L.parse_verdict("```json\n" + _j() + "\n```", REPLY)
    assert err == "", err


def test_there_is_no_mild_tier():
    """Binary only, by founder ruling. A non-boolean v is refused rather than
    coerced — coercing "slightly" to True is exactly the silent judgement the
    ruling removed."""
    v, err = L.parse_verdict(
        '{"a":{"v":"mild","q":"x"},"b":{"v":false,"q":""},"c":{"v":false,"q":""},'
        '"d":{"v":false,"q":""},"e":{"v":false,"q":""}}', REPLY)
    assert v == {} and "not a boolean" in err


# ── what the judge is shown ─────────────────────────────────────────────────

def test_the_persona_is_not_named_to_the_judge():
    """Knowing a reply is Lao Tzu's would lean criterion (c) before it is made."""
    block = L.conversation_block("I am tired.", REPLY)
    for slug in ("lao_tzu", "Lao Tzu", "socrates", "Socrates"):
        assert slug not in block
    assert "I am tired." in block and REPLY in block


def test_the_rubric_states_the_inverted_criterion():
    assert "this is the one question where YES is the good answer" in L.RUBRIC


def test_the_rubric_does_not_ban_ending_on_a_question():
    """Three readings showed preferred replies ending on questions. If this
    sentence is ever removed, criterion (b) silently becomes 'ends with a
    question', which is the thing it was written NOT to be."""
    assert "Ending on a question is NOT itself a fault" in L.RUBRIC


# ── the calibration sample ──────────────────────────────────────────────────

@pytest.mark.skipif(not (B3 / "completions.jsonl").exists(),
                    reason="B3 completions.jsonl is gitignored; local runs only")
class TestSelection:
    def test_it_is_44_replies(self):
        assert len(L.select_calibration(B3)) == 44

    def test_four_per_persona(self):
        c = collections.Counter(r["persona_slug"] for r in L.select_calibration(B3))
        assert set(c.values()) == {4} and len(c) == 11

    def test_problems_are_spread_not_clustered(self):
        """The first version of the rule shuffled every persona with one shared
        seed, so every persona drew the SAME permutation: 11x P01, 11x P06,
        10x P07, 1x P09. Three problems carried three quarters of the set."""
        c = collections.Counter(r["problem_id"] for r in L.select_calibration(B3))
        assert max(c.values()) - min(c.values()) <= 2, dict(c)

    def test_the_eleven_blind3_replies_are_all_in(self):
        chosen = {r["sample_id"] for r in L.select_calibration(B3)}
        fixed = set(L.blind3_b3_sample_ids(B3))
        assert len(fixed) == 11
        assert fixed <= chosen

    def test_it_is_deterministic(self):
        a = [r["sample_id"] for r in L.select_calibration(B3)]
        b = [r["sample_id"] for r in L.select_calibration(B3)]
        assert a == b == sorted(a)

    def test_deep_replies_are_excluded(self):
        assert all(r["mode"] != "deep" for r in L.select_calibration(B3))

    def test_only_sonnet_replies(self):
        assert all(r["plan"] == "pro" for r in L.select_calibration(B3))


# ── cost, so a surprise bill is a failing test rather than a surprise ───────

def test_the_opus_price_is_the_current_one_not_the_retired_one():
    """$15/$75 is Opus 4.1, retired. Opus 5 is $5/$25, verified against the
    pricing page 2026-09-23. The first estimate in this workstream used the
    retired rate and was 3x too high."""
    assert (L.PRICE_IN, L.PRICE_OUT) == (5.0, 25.0)


def test_the_judge_is_deterministic_by_configuration():
    assert L.TEMPERATURE == 0.0
    assert L.JUDGE_MODEL == "claude-opus-5"
