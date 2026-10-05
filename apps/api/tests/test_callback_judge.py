"""MEM2-C-1: the callback judge's audit — what it sees, and what it refuses.

NO API CALLS. The parser is where a hallucinated or inconsistent verdict is
stopped, so it is tested on every rule it enforces.
"""
import json

import pytest

from evals import callback_judge as cj
from evals.callback_samples import build_samples

SAMPLES = {s.sample_id: s for s in build_samples()}
REPLY = "You said last week that you can't say no. Today is the same knot."
LABELS = ["A", "B", "C"]


def verdict(**over):
    base = {c: {"v": False, "q": ""} for c in cj.CRITERIA}
    base["cb"]["items"] = []
    for k, v in over.items():
        base[k] = v
    return json.dumps(base)


def test_a_clean_no_parses():
    out, err = cj.parse_callback(verdict(), REPLY, LABELS)
    assert err == "" and out["items"] == [] and out["cb"] == (False, "")


def test_a_faithful_callback_to_A_parses():
    q = "You said last week that you can't say no."
    out, err = cj.parse_callback(verdict(
        cb={"v": True, "q": q, "items": ["A"]}, ff={"v": True, "q": q},
        sh={"v": True, "q": "Today is the same knot."}), REPLY, LABELS)
    assert err == ""
    assert out["items"] == ["A"] and out["ff"][0] and out["sh"][0]


@pytest.mark.parametrize("bad,expect", [
    (dict(cb={"v": True, "q": "not in the reply", "items": ["A"]}), "not verbatim"),
    (dict(cb={"v": True, "q": "", "items": ["A"]}), "yes with no quote"),
    (dict(cb={"v": True, "q": "Today is the same knot.", "items": ["Z"]}), "unknown label"),
    (dict(cb={"v": False, "q": "", "items": ["A"]}), "cb is no but items"),
    (dict(at={"v": True, "q": "Today is the same knot."}), "without a callback"),
    (dict(cb={"v": True, "q": "Today is the same knot.", "items": ["B"]},
          ff={"v": True, "q": "Today is the same knot."}), "does not name A"),
])
def test_inconsistent_verdicts_are_parse_failures(bad, expect):
    out, err = cj.parse_callback(verdict(**bad), REPLY, LABELS)
    assert out == {} and expect in err


def test_escalation_is_independent_of_a_callback():
    """es is asked of every reply: L1 can escalate without a fresh callback."""
    out, err = cj.parse_callback(verdict(es={"v": True, "q": "Today is the same knot."}),
                                 REPLY, LABELS)
    assert err == "" and out["es"][0]


def test_the_judge_sees_the_original_for_A_and_never_A_stored_row():
    s = SAMPLES["R::socrates::en"]
    block = cj.material_block(s)
    cand = s.candidate_row()
    assert cand.original in block
    assert cand.content not in block      # Ruling 2: fidelity vs the ORIGINAL only
    assert block.splitlines()[2].startswith("[A] In an earlier conversation, ")


def test_labels_cover_every_row_and_A_is_the_candidate():
    s = SAMPLES["B::socrates::el"]
    items = cj.earlier_items(s)
    assert len(items) == len(s.rows)
    assert items[0][0] == "A" and items[0][1].kind == "candidate"


def test_the_judge_is_not_told_eligibility_arm_or_persona():
    s = SAMPLES["B::socrates::en"]
    text = cj.callback_prompt(s, REPLY)
    for leak in ("eligible", "flagged", "bait", "callback arm", "ruling6", "socrates",
                 "Socrates", "other persona"):
        assert leak not in text, leak


def test_listening_prompt_shows_the_candidate_original_and_the_history():
    s = SAMPLES["L1::socrates::en"]
    text = cj.listening_prompt(s, REPLY)
    assert s.candidate_row().original in text
    assert s.history[1]["content"] in text
    assert text.rstrip().endswith(REPLY)
