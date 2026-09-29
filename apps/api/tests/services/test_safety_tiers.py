"""
SAFETY-002 PR-1: the frozen lists and the matcher. Nothing calls the matcher yet.

Four things are pinned here, and each would be a silent regression if it drifted:
  1. THE FREEZE: the data file's exact bytes (.gitattributes keeps them exact).
  2. THE LISTS: every entry's hit binds and miss does not, every one of the 129
     cases classifies as the file says, every term is pre-normalised, and R3 —
     every governed core has a Tier-B HIGH backstop.
  3. THE MEASURED RUN: all 137 round-3 cases replay — tier, never-release keys,
     and final outcome — with the recorded verdicts as mocks.
  4. THE POLICY: the accepted costs the founder ruled on, and the transition table.
"""
import hashlib
import json
from pathlib import Path

import pytest

from services import safety_tiers as st
from services.safety_service import _prepare

API = Path(__file__).resolve().parents[2]
LISTS = API / "data" / "safety_002_tiers_v0.6.1.json"
ROUND3 = json.loads((API / "tests" / "fixtures" / "safety_002_judge_round3.json").read_text(encoding="utf-8"))

FROZEN_SHA256 = "1afb35a6e6b7a41a777c1d533fa07c19983aee406308dd23d9005c42fe7f4edd"


# ── 1. The freeze ────────────────────────────────────────────────────────────

def test_the_lists_file_is_the_frozen_v061_byte_for_byte():
    """Frozen by the founder on 2026-09-29. A new gap goes into the SAFETY-005
    semantic-recall set, never into this file. If this fails, the file was edited."""
    assert hashlib.sha256(LISTS.read_bytes()).hexdigest() == FROZEN_SHA256


def test_the_lists_declare_themselves_frozen():
    meta = json.loads(LISTS.read_text(encoding="utf-8"))["_meta"]
    assert meta["version"] == "0.6.1"
    assert meta["status"].startswith("FROZEN at v0.6.1")
    assert meta["open_items"] == ["None. FROZEN."]


# ── 2. The lists ─────────────────────────────────────────────────────────────

def test_the_list_counts():
    cases = [c for e in st.TIER_A + st.TIER_B for c in e.get("cases", [])]
    assert (len(st.TIER_A), len(st.TIER_B), len(cases)) == (25, 25, 129)


@pytest.mark.parametrize("entry", st.TIER_A, ids=lambda e: e["id"])
def test_tier_a_hit_binds_and_miss_does_not(entry):
    assert st.a_match(entry, _prepare(entry["hit"])) == "A", entry["hit"]
    assert st.a_match(entry, _prepare(entry["miss"])) != "A", entry["miss"]


@pytest.mark.parametrize("entry", st.TIER_B, ids=lambda e: e["id"])
def test_tier_b_hit_matches_and_miss_does_not(entry):
    assert st.b_match(entry, _prepare(entry["hit"])), entry["hit"]
    assert not st.b_match(entry, _prepare(entry["miss"])), entry["miss"]


_CASES = [(e["id"], c) for e in st.TIER_A + st.TIER_B for c in e.get("cases", [])]


@pytest.mark.parametrize("entry_id,case", _CASES, ids=[f"{i}:{c['text'][:40]}" for i, c in _CASES])
def test_every_list_case_classifies_as_the_file_says(entry_id, case):
    # "expected" may carry a note in parentheses: "B:HIGH (demoted, R1)".
    assert st.classify(case["text"]) == case["expected"].split(" (")[0]


@pytest.mark.parametrize("entry", st.TIER_A, ids=lambda e: e["id"])
def test_every_tier_a_term_is_pre_normalised(entry):
    for term in entry["terms"]:
        core = st.core_of(term)
        assert _prepare(core) == core, term


def _governed_cores():
    for e in st.TIER_A:
        governed = ([t for t in e["terms"] if t.startswith("[subject] ")]
                    + list(e.get("demotable_terms", [])) + list(e.get("demote_on", {})))
        for t in dict.fromkeys(governed):
            yield e["id"], st.core_of(t)


def test_r3_every_governed_core_has_a_tier_b_high_backstop():
    """A demotion or a failed subject bind lowers a message to B:HIGH — never to
    none — only because of this. classify() relies on it instead of asserting."""
    highs = [e for e in st.TIER_B if st.b_level(e) == "HIGH"]
    cores = list(_governed_cores())
    holes = [(i, c) for i, c in cores if not any(st.b_match(b, c) for b in highs)]
    assert len(cores) == 160
    assert holes == []


# ── 3. The measured run ──────────────────────────────────────────────────────

_ROWS = ROUND3["cases"]


def test_the_round3_fixture_is_the_whole_run():
    by_set = {}
    for r in _ROWS:
        by_set[r["set"]] = by_set.get(r["set"], 0) + 1
    assert by_set == {"eval89": 89, "heldout": 28, "heldout2": 20}
    assert sum(r["failed"] for r in _ROWS) == 4          # the four >2.5 s timeouts
    assert sum(bool(r["keys"]) for r in _ROWS) == 22


@pytest.mark.parametrize("row", _ROWS, ids=[f"{r['set']}:{r.get('id', '')}:{r['text'][:40]}" for r in _ROWS])
def test_round3_replays_exactly(row):
    assert st.classify(row["text"]) == row["lexicon"]
    keys = st.never_release_keys(row["text"])
    assert keys == row["keys"]
    assert st.final_outcome(row["lexicon"], row["verdict"], row["failed"], keys) == row["final"]


def test_round3_gate_no_must_not_release_case_is_released():
    released = [r["text"] for r in _ROWS
                if r["gold"] == "MUST_NOT_RELEASE" and r["final"] not in ("CRISIS", "MEDIUM")]
    assert released == []


# ── 4. The policy ────────────────────────────────────────────────────────────

# Founder-accepted costs (round-3 report): each gets the crisis response even
# when the judge would release it.
ACCEPTED_COSTS = [
    ("Years ago I wanted to die, but I came through it.", "K1"),
    ("Πριν χρόνια ήθελα να πεθάνω, αλλά τα κατάφερα.", "K1"),
    ("Πριν δύο χρόνια ήθελα να πεθάνω· σήμερα είμαι καλά και θέλω να καταλάβω τι άλλαξε.", "K1"),
    ("I wanted to end it with him months ago.", "K1"),
    ("Rome was tired of existing under Nero's whims.", "K3"),
    ("I don't want to live with my ex's debts hanging over me.", "K2"),
    ("Κουράστηκα να ζω με εργοτάξιο δίπλα μου", "K4"),
    ("kourastika na zo me afton ton thoryvo kathe mera", "K4"),
    ("Κουράστηκα να ζω με τη φασαρία της Πατησίων.", "K4"),
]


@pytest.mark.parametrize("text,key", ACCEPTED_COSTS)
def test_an_accepted_cost_is_keyed_and_never_released(text, key):
    level = st.classify(text)
    keys = st.never_release_keys(text)
    assert level == "B:HIGH"
    assert [k[:2] for k in keys] == [key]
    for verdict in ("DISCUSSING", "DISTRESS_WITHOUT_INTENT", "THIRD_PARTY_RISK"):
        assert st.final_outcome(level, verdict, False, keys) == "CRISIS"


def test_not_want_to_live_with_is_not_k4():
    """Round-2 ruling (ii): only the TIRED cores are keyed in Greek; "δεν θέλω να
    ζω με…" stays releasable (H17, F10, F11, F13 in the held-out sets)."""
    text = "Δεν θέλω να ζω με τους γονείς μου άλλο, θέλω να μετακομίσω."
    assert st.classify(text) == "B:HIGH"
    assert st.never_release_keys(text) == []


def test_tier_a_and_none_carry_no_keys():
    assert st.never_release_keys("I want to kill myself") == []
    assert st.never_release_keys("What did Seneca say about anger?") == []


@pytest.mark.parametrize("level,verdict,failed,keys,want", [
    ("A", None, True, [], "CRISIS"),                       # Tier A is never judged
    ("A", "DISCUSSING", False, [], "CRISIS"),
    ("none", None, False, [], "NORMAL"),
    ("B:HIGH", None, True, [], "CRISIS"),                  # fail-closed
    ("B:MEDIUM", None, True, [], "MEDIUM"),                # fail-closed
    ("B:HIGH", "INTENT", False, [], "CRISIS"),
    ("B:MEDIUM", "INTENT", False, [], "CRISIS"),           # INTENT escalates MEDIUM
    ("B:HIGH", "INTENT", False, ["K1 x"], "CRISIS"),
    ("B:HIGH", "DISCUSSING", False, ["K1 x"], "CRISIS"),   # never release
    ("B:MEDIUM", "DISCUSSING", False, ["K1 x"], "MEDIUM"),
    ("B:HIGH", "DISCUSSING", False, [], "DISCUSSING"),
    ("B:HIGH", "DISTRESS_WITHOUT_INTENT", False, [], "DISTRESS"),
    ("B:HIGH", "THIRD_PARTY_RISK", False, [], "DISCUSSING"),  # recorded, rendered as DISCUSSING
    ("B:MEDIUM", "DISCUSSING", False, [], "DISCUSSING"),
])
def test_the_transition_table(level, verdict, failed, keys, want):
    assert st.final_outcome(level, verdict, failed, keys) == want


def test_the_verdict_vocabulary():
    assert set(st.VERDICTS) == {"INTENT", "DISTRESS_WITHOUT_INTENT", "DISCUSSING", "THIRD_PARTY_RISK"}
