"""MEM2-C-1: the harness seams, the block order, and the aggregation.

The parity block follows tests/test_harness_parity.py's rule: the production
prompt is rebuilt INLINE, longhand, and compared to what the harness returns —
a shared helper would make the comparison tautological.

NO API CALLS.
"""
import pytest

from evals import callback_run as cr
from evals import harness
from evals.callback_judge import earlier_items
from evals.callback_samples import build_samples
from personas import PERSONA_REGISTRY
from services import reply_directive
from services.conversation_service import _adaptive_band_for_input
from services.memory_service import STANDING_TYPES
from services.prompt_builder import prompt_builder

SAMPLES = {s.sample_id: s for s in build_samples()}
SLUGS = sorted(PERSONA_REGISTRY)


@pytest.fixture(autouse=True)
def _no_bridge(monkeypatch):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)


def _inline_shipped(persona, msg, memories, history_len):
    """conversation_service.py:861-1009 for a NORMAL/none, non-deep turn, longhand."""
    system = prompt_builder.build_system(
        persona=persona, memories=list(memories), phenomenology_bridge=None,
        profile=None, include_cache_sentinel=True,
    )
    band = _adaptive_band_for_input(msg, persona) if history_len > 1 else None
    tail = reply_directive.directive(persona, first_message=(history_len <= 1),
                                     deep=False, band=band)
    return system + "\n\n" + tail if tail else system


# ── harness seams ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", SLUGS)
@pytest.mark.parametrize("scenario", ["R", "L1"])
def test_shipped_arm_is_production_with_memories_and_history(slug, scenario):
    s = SAMPLES[f"{scenario}::{slug}::en"]
    rows = cr.block_rows(s)
    got, _ = harness.assemble_system(
        PERSONA_REGISTRY[slug], s.user_message, deep=False, arm="shipped",
        memories=rows, history_len=len(s.history),
    )
    assert got == _inline_shipped(PERSONA_REGISTRY[slug], s.user_message, rows,
                                  len(s.history))


@pytest.mark.parametrize("slug", SLUGS)
def test_default_seams_leave_every_existing_arm_unchanged(slug):
    p = PERSONA_REGISTRY[slug]
    msg = SAMPLES[f"R::{slug}::en"].user_message
    for arm in ("baseline", "e"):
        a, _ = harness.assemble_system(p, msg, deep=False, arm=arm)
        b, _ = harness.assemble_system(p, msg, deep=False, arm=arm, memories=(),
                                       history_len=0, callback_block="")
        assert a == b


def test_callback_block_sits_between_the_memory_block_and_hard_rules():
    s = SAMPLES["R::lao_tzu::el"]
    block = cr.callback_for(s, "callback")
    system, _ = harness.assemble_system(
        PERSONA_REGISTRY["lao_tzu"], s.user_message, deep=False, arm="shipped",
        memories=cr.block_rows(s), history_len=0, callback_block=block,
    )
    mem = system.index("WHAT YOU KNOW ABOUT THIS PERSON")
    cb = system.index("ONE THING THEY SAID BEFORE")
    hard = system.index("HARD RULES (non-negotiable)")
    assert mem < cb < hard
    assert system.count("ONE THING THEY SAID BEFORE") == 1
    # removing the block restores the ruling6 prompt exactly
    plain, _ = harness.assemble_system(
        PERSONA_REGISTRY["lao_tzu"], s.user_message, deep=False, arm="shipped",
        memories=cr.block_rows(s), history_len=0,
    )
    assert system.replace(block + "\n\n\n", "", 1) == plain


def test_callback_arm_renders_the_variant_for_the_sample_language():
    en = cr.callback_for(SAMPLES["R::lao_tzu::en"], "callback")
    el = cr.callback_for(SAMPLES["R::lao_tzu::el"], "callback")
    assert "You said" in en and "Είπες" not in en
    assert "Είπες" in el and "You said" not in el


def test_a_filtered_run_loads_only_its_own_samples(tmp_path):
    """A --language el run writes scores.json for EL samples only. load_run must
    not reach for an EN sample's scores (KeyError before judge pre-flight)."""
    import json
    el = [s for s in build_samples() if s.language == "el"]
    stored = {s.sample_id: {"rows": {r.id: 0.5 for r in s.rows}} for s in el}
    (tmp_path / "scores.json").write_text(json.dumps(stored), encoding="utf-8")
    (tmp_path / "completions.jsonl").write_text("", encoding="utf-8")
    rows, by_id = cr.load_run(tmp_path)
    assert rows == []
    assert set(by_id) == set(stored)
    assert all(s.language == "el" for s in by_id.values())
    assert all(r.score == 0.5 for s in by_id.values() for r in s.rows)


def test_insert_refuses_without_a_unique_anchor():
    with pytest.raises(ValueError):
        harness._insert_callback("no anchor here", "x")


def test_ruling6_arm_never_renders_a_callback_and_L1_never_does():
    for s in SAMPLES.values():
        assert cr.callback_for(s, "ruling6") == ""
        if s.scenario == "L1":
            assert cr.callback_for(s, "callback") == ""


# ── block order and bands ────────────────────────────────────────────────────

def test_block_puts_standing_rows_first():
    s = SAMPLES["B::socrates::en"]
    rows = cr.block_rows(s)
    kinds = [r.entry_type in STANDING_TYPES for r in rows]
    assert kinds == sorted(kinds, reverse=True)


def test_stated_band_first_message_vs_second_turn():
    p = PERSONA_REGISTRY["lao_tzu"]
    assert cr.stated_band(SAMPLES["R::lao_tzu::en"]) == p.response_length_words.standard_reply_words
    l1 = SAMPLES["L1::lao_tzu::en"]
    band = _adaptive_band_for_input(l1.user_message, p)
    assert cr.stated_band(l1) == (band or p.response_length_words.standard_reply_words)


# ── aggregation ──────────────────────────────────────────────────────────────

def _comp(arm, sid, *, words=50, offered=True, lang="en", plan="pro"):
    s = SAMPLES[sid]
    return {"key": cr.completion_key(arm, plan, sid), "arm": arm, "plan": plan,
            "sample_id": sid, "scenario": s.scenario, "persona_slug": s.persona_slug,
            "language": lang, "when": "last week", "gate_offers": s.scenario != "L1",
            "offered": offered and arm == "callback" and s.scenario != "L1",
            "words": words, "in_band": 55 <= words <= 80, "error": None,
            "reply_language": "English"}


def _cb(key, call="1", **yes):
    row = {"key": key, "call": call, "raw_error": "", "items": yes.pop("items", "")}
    for c in ("cb", "ff", "es", "tm", "at", "cf", "sh"):
        row[f"{c}_v"] = "1" if yes.get(c) else "0"
        row[f"{c}_q"] = ""
    return row


def _scores():
    out = {}
    for sid in SAMPLES:
        out[sid] = {"candidate_row_cosine": 0.45, "recall_would_keep": []}
    return out


def test_aggregate_counts_callbacks_fidelity_repetition_and_misuse():
    sids = ["R::socrates::en", "R2::socrates::en", "B::socrates::en", "L2::socrates::en"]
    comps = [_comp("callback", sid) for sid in sids]
    cb = [
        _cb(comps[0]["key"], cb=1, ff=1, sh=1, items="A"),
        _cb(comps[1]["key"], cb=1, ff=0, items="A"),          # repeated, unfaithful
        _cb(comps[2]["key"], cb=1, items="C"),                 # B: refers to bait
        _cb(comps[3]["key"], es=1),                            # escalation, no callback
    ]
    # "C" is the second row after the candidate: a standing self-portrait tap
    b_items = dict(earlier_items(SAMPLES["B::socrates::en"]))
    assert b_items["C"].kind == "self_portrait"
    agg = cr.aggregate(comps, SAMPLES, cb, [], _scores())
    g = agg["groups"]["callback|pro|en"]
    assert g["callback_rate_on_offer"].startswith("50.0%")      # R, R2 of 4 offered
    assert g["fidelity_among_callbacks"].startswith("50.0%")
    assert g["repetition_R_then_R2"].startswith("100.0%")
    assert g["escalation_L2_after_affirmation"].startswith("100.0%")
    assert g["misuse_rate_in_B"].startswith("100.0%")
    assert g["misuse_by_kind"] == {"self_portrait": 1}


def test_parse_failures_are_excluded_not_counted_as_no():
    comp = _comp("callback", "R::socrates::en")
    bad = _cb(comp["key"], cb=1, items="A")
    bad["raw_error"] = "json: boom"
    agg = cr.aggregate([comp], SAMPLES, [bad], [], _scores())
    g = agg["groups"]["callback|pro|en"]
    assert g["judged"] == 0
    assert g["callback_rate_on_offer"] == "n/a (0)"
    assert agg["judge_failures"]["callback"] == 1
