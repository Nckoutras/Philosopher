"""The runner's pre-flight: the two gates that exist to stop a wasted spend,
and the ordering invariant the manifest claims.

None of this calls a model. `generate` is stubbed; what is under test is the
scheduling, the refusal and the record.

Run: cd apps/api && pytest tests/test_eval_runner.py -v
"""
import json

import pytest

from evals import harness, run as runner
from evals.prompt_set import build_samples


# ── the bridge gate ──────────────────────────────────────────────────────────

def test_bridge_gate_refuses_on_mismatch(monkeypatch, capsys):
    """Refuses BEFORE anything is sent.

    The bridge changes the system prompt on 9 of 10 problems, so a run made with
    the wrong flag is a different corpus — valid-looking, fully scored, and
    comparable to nothing. compare.py would catch it, but only after the money
    was spent.
    """
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    assert runner._check_bridge("true") == 2
    err = capsys.readouterr().err
    assert "REFUSING" in err
    assert "Nothing has been sent" in err


@pytest.mark.parametrize("env,require", [(True, "true"), (False, "false")])
def test_bridge_gate_passes_when_they_agree(monkeypatch, env, require):
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", env)
    assert runner._check_bridge(require) == 0


def test_bridge_gate_is_opt_in(monkeypatch):
    """Omitting the flag must not block anyone — it is a guard, not a policy."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", False)
    assert runner._check_bridge(None) == 0


# ── generation order vs row order ────────────────────────────────────────────

async def test_generation_is_persona_major_but_rows_are_sample_id_ordered(monkeypatch):
    """Two different orders, and only the second is part of the measurement.

    Persona-major generation keeps the 10 Sonnet calls that share a cacheable
    prefix inside the 5-minute TTL. The returned list must not inherit that
    scheduling, or every downstream file would be ordered by a cost optimisation.
    """
    seen_order = []

    async def fake_generate(sample, plan, model, arm="baseline"):
        # `arm` is threaded through generate_all as a 4th positional argument;
        # a stub that omits it fails with a TypeError that looks like an
        # ordering bug rather than a signature drift.
        assert arm == "baseline"
        seen_order.append((sample.persona_slug, plan, sample.problem_id))
        return harness.Completion(
            sample_id=sample.sample_id, problem_id=sample.problem_id,
            persona_slug=sample.persona_slug, mode=sample.mode,
            plan=plan, model=model, user_message=sample.user_message,
            reply="x", system_prompt="", bridge_matched=None,
        )

    monkeypatch.setattr(harness, "generate", fake_generate)
    samples = build_samples()
    out = await harness.generate_all(samples, concurrency=1)

    assert len(out) == len(samples) * 2 == 220

    # scheduled persona-major
    assert seen_order == sorted(seen_order)
    # returned sample_id-major
    keys = [(c.sample_id, c.plan) for c in out]
    assert keys == sorted(keys)
    # and the two orders genuinely DIFFER, or this test proves nothing
    scheduled_ids = [f"{prob}::{slug}" for slug, _plan, prob in seen_order]
    returned_ids = [c.sample_id.rsplit("::", 1)[0] for c in out]
    assert scheduled_ids != returned_ids


# ── the dry-run manifest ─────────────────────────────────────────────────────

async def test_dry_run_writes_a_manifest_and_sends_nothing(monkeypatch, tmp_path):
    """A pre-flight that exists only in terminal scrollback is not a record."""
    monkeypatch.setattr(harness, "PHENOMENOLOGY_BRIDGE_ENABLED", True)

    async def explode(*a, **kw):
        raise AssertionError("--dry-run must not send anything")

    monkeypatch.setattr(harness, "generate", explode)
    monkeypatch.setattr(harness, "generate_all", explode)

    args = runner.argparse.Namespace(
        arm="baseline", note="test", out=str(tmp_path), persona=None,
        limit=None, concurrency=1, dry_run=True, rescore=None,
        require_bridge="true",
    )
    assert await runner._main_async(args) == 0

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dry_run"] is True
    assert manifest["arm"] == "baseline"
    assert manifest["arm_directive_hash"] is None, "baseline appends no directive"
    assert manifest["arm_bands"] is None
    assert manifest["phenomenology_bridge_enabled"] is True
    assert manifest["n_samples"] == 110
    assert manifest["cost"] == {}, "a dry run has no cost block"
    assert manifest["input_profile"]["completions_that_would_be_sent"] == 220
    # 9 of the 10 problems carry an expected_phenomenology_match, so with the
    # bridge on most samples should resolve one. A zero here would mean the
    # bridge is wired but inert.
    assert manifest["input_profile"]["samples_with_bridge_match"] > 0

    # the keys compare.py gates on must all be present, or a later diff cannot
    # refuse and will silently compare incomparable runs
    for key in ("prompt_set_hash", "models", "phenomenology_bridge_enabled",
                "deep_problem_ids", "personas"):
        assert key in manifest, key

    assert not (tmp_path / "completions.jsonl").exists()
    assert not (tmp_path / "scores.csv").exists()


def test_the_manifest_records_both_orders():
    manifest = runner._manifest("a", "", build_samples(), [], dry_run=True)
    assert "persona-major" in manifest["generation_order"]
    assert "sample_id" in manifest["row_order"]
