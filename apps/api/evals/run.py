"""Run one arm of the §8.2 eval suite.

    cd apps/api && python -m evals.run --arm baseline

110 samples x 2 plans = 220 completions. Haiku 4.5 for the free path, Sonnet 4.6
for the pro path, because those are production's two paths and `model_used` is
NULL on every stored row (BUG-024 GAP 1), so this is the only instrument that can
separate them.

Measured cost, at the observed input profile (~3.4k system + ~80 user tokens,
~120-200 output): about $0.50 on Haiku and $1.45 on Sonnet per 110, so roughly
$1.95 for a full run of both. A two-arm A/B is under $4.

OUTPUT — deliberately boring, four files in a dated folder:

    results/<UTC-stamp>_<arm>/
        manifest.json      what this run was; compare.py refuses on a mismatch
        completions.jsonl  the raw text, so a later scorer can be re-run free
        scores.csv         one row per completion
        summary.csv        one row per (persona, mode, plan) — the diffable thing

completions.jsonl is the archive and the reason a scoring change never costs
money twice: `--rescore <dir>` re-reads it and rewrites the two CSVs.

NEVER RUNS IN CI. pyproject sets testpaths = ["tests"], so nothing under
apps/api/evals is collected. This module makes real API calls and costs money.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from personas import PERSONA_REGISTRY

from . import arm_b, harness
from .prompt_set import DEEP_PROBLEM_IDS, Sample, build_samples, prompt_set_hash
from .scorers import (
    CSV_COLUMNS,
    SUMMARY_COLUMNS,
    Scores,
    score,
    summarise,
    to_row,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# $ per million tokens. Verified against the current model table, 2026-09-22.
PRICES = {
    harness.MODEL_FREE: (1.0, 5.0),    # Haiku 4.5
    harness.MODEL_PRO: (3.0, 15.0),    # Sonnet 4.6
}
# The four input buckets price differently; "total" in the sink is volume, not
# cost (see llm_client.stream's docstring).
BUCKET_MULTIPLIER = {"input": 1.0, "cache_creation": 1.25, "cache_read": 0.1}


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    """Is the working tree dirty, EXCLUDING the harness's own output?

    A run writes results/<stamp>/ and neither summary.csv nor manifest.json is
    gitignored (they are the artefacts a finding cites). Counting them would
    make every run after the first report git_dirty: true, and compare.py's
    "no provenance" warning would fire on every diff forever — a warning that
    always fires is one that is correctly ignored by the third viewing.

    So this answers the question the flag is actually for: has the CODE that
    produced this run been modified since its commit?
    """
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return False
    ignore = "apps/api/evals/results/"
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if path and not path.startswith(ignore):
            return True
    return False


def _cost(completions) -> dict:
    """Actual spend from recorded usage — not an estimate.

    Output tokens are total minus the three input buckets, per llm_client's
    documented identity.
    """
    per_model: dict[str, dict] = {}
    for c in completions:
        if not c.tokens:
            continue
        t = c.tokens
        acc = per_model.setdefault(c.model, {
            "input": 0, "cache_creation": 0, "cache_read": 0, "output": 0, "usd": 0.0,
        })
        inp = t.get("input", 0)
        cw = t.get("cache_creation", 0)
        cr = t.get("cache_read", 0)
        out = t.get("total", 0) - (inp + cw + cr)
        acc["input"] += inp
        acc["cache_creation"] += cw
        acc["cache_read"] += cr
        acc["output"] += out

    for model, acc in per_model.items():
        in_price, out_price = PRICES.get(model, (0.0, 0.0))
        billed_in = sum(acc[b] * BUCKET_MULTIPLIER[b] for b in BUCKET_MULTIPLIER)
        acc["usd"] = round(
            billed_in / 1e6 * in_price + acc["output"] / 1e6 * out_price, 4
        )
    per_model["_total_usd"] = round(
        sum(v["usd"] for v in per_model.values() if isinstance(v, dict)), 4
    )
    return per_model


def _manifest(arm: str, note: str, samples, completions, *, dry_run: bool,
              git_dirty: bool | None = None) -> dict:
    """The record of what a run WAS. compare.py refuses on a mismatch of the
    gated keys, so this is not documentation — it is the comparability check."""
    return {
        "arm": arm,
        "note": note,
        "dry_run": dry_run,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        # Captured BEFORE the run writes anything. Computing it here would be
        # true on every real run, because summary.csv and the results directory
        # are untracked by design — a provenance flag that is always set is not
        # a flag, and compare.py's warning on it would be correctly ignored by
        # the third time anyone saw it.
        "git_dirty": _git_dirty() if git_dirty is None else git_dirty,
        "prompt_set_hash": prompt_set_hash(),
        "n_samples": len(samples),
        "n_completions": len(completions),
        "deep_problem_ids": sorted(DEEP_PROBLEM_IDS),
        "personas": sorted(PERSONA_REGISTRY),
        "models": sorted({c.model for c in completions}) if completions
                  else sorted({m for _, _, m in harness.ARMS_BY_PLAN}),
        "phenomenology_bridge_enabled": harness.PHENOMENOLOGY_BRIDGE_ENABLED,
        # RECORDED, NOT GATED. Two arms are SUPPOSED to differ here, so
        # compare.py must not refuse on it. It is recorded so that re-running
        # the SAME arm after the directive was reworded is detectable — the
        # prompt_set_hash lesson applied to the thing the arm itself changes.
        "arm_directive_hash": (
            hashlib.sha256(
                (arm_b.FIRST_MESSAGE + arm_b.STANDARD + arm_b.DEEP
                 + arm_b.bands_note()).encode("utf-8")
            ).hexdigest()[:16] if arm in arm_b.ARMS and arm != "baseline" else None
        ),
        "arm_bands": arm_b.bands_note() if arm != "baseline" else None,
        "arm_bands_note": (
            "Scaled from each persona's current standard band midpoint by 1.7742 so "
            "the mean target is 75 words, order preserved; lo = 0.8x target, hi = "
            "1.2x target, rounded to 5; deep target = 1.6x standard. ONE EXCEPTION: "
            "miyamoto_musashi scales to 75-110/120-180 and was moved by founder "
            "ruling to 55-80/85-130, because his shipped (30, 75) band is the second "
            "widest of the eleven and contradicts his own anchor_cuts_the_unnecessary "
            "and his system_fragment's 'Short lines. One point per reply - cut the "
            "rest'. Scaling inherits an existing error faithfully; this corrects it. "
            "Mean standard target is therefore 72.6, not 75.0. FIRST MESSAGE uses the "
            "same range as STANDARD: first_message_max_words never reached a prompt, "
            "so expect fm_over near 100% as a design artefact, not a regression."
            if arm != "baseline" else None
        ),
        "postprocessing_enabled_env": os.getenv("POSTPROCESSING_ENABLED"),
        # Two different orders, and only the second is part of the measurement.
        "generation_order": "persona-major (persona, plan, problem) — a cost "
                            "optimisation for Sonnet's per-persona prefix cache; "
                            "Haiku cannot cache, its minimum prefix is above ours",
        "row_order": "sample_id, then plan — every output file is ordered "
                     "independently of how generation was scheduled",
        "errors": sum(1 for c in completions if c.error),
        "cost": _cost(completions) if completions else {},
        # Read this before trusting a number in summary.csv.
        "caveats": [
            "Rates only. No pass/fail: the spec's thresholds were written "
            "2026-04-27 against a six-persona config whose per-persona bands "
            "match no current persona, and are unanchored until a baseline "
            "exists (founder ruling D4, 2026-09-22).",
            "fm_over_rate scores against first_message_max_words, which reaches "
            "NO PROMPT. std_over_rate scores against the band the persona's own "
            "system_fragment states. The gap between them is BREV-002.",
            "anti_flex_rate covers 77 full / 9 partial / 4 framed topics. A zero "
            "means no hit on what is covered, never 'no flexing'.",
        ],
    }


def _write(out: Path, arm: str, samples, completions, scores: list[Scores],
           note: str, *, git_dirty: bool | None = None):
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "completions.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for c in completions:
            fh.write(json.dumps({
                "sample_id": c.sample_id, "problem_id": c.problem_id,
                "persona_slug": c.persona_slug, "mode": c.mode,
                "plan": c.plan, "model": c.model,
                "user_message": c.user_message, "reply": c.reply,
                "bridge_matched": c.bridge_matched, "tokens": c.tokens,
                "error": c.error,
                "system_prompt_chars": len(c.system_prompt),
            }, ensure_ascii=False) + "\n")

    with open(out / "scores.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for s in scores:
            w.writerow(to_row(s))

    rows = summarise(scores)
    with open(out / "summary.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        w.writerows(rows)

    manifest = _manifest(arm, note, samples, completions, dry_run=False,
                         git_dirty=git_dirty)
    with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest, rows


def _check_bridge(require: str | None) -> int:
    """Refuse BEFORE anything is sent if the environment disagrees.

    The bridge changes the system prompt on 3 of the 10 problems (measured; the
    `expected_phenomenology_match` field claims 9 and is wrong about 8 of them),
    so a run made with the wrong flag is a different corpus — valid-looking,
    fully scored, and comparable to nothing. The manifest records the flag and
    compare.py refuses on a mismatch, but that only tells you AFTER you have paid
    for the run. This tells you before.

    THE FLAG CANNOT LIVE IN apps/api/.env, and this message used to say it could.
    Two independent reasons:

      1. config.Settings forbids extra fields, and PHENOMENOLOGY_BRIDGE_ENABLED
         is not one of them. Putting it in .env makes `from config import config`
         raise pydantic ValidationError(extra_forbidden) — which is an import-time
         crash for anything that touches config, including this runner.
      2. Even if it were permitted, pydantic reads .env into the Settings object;
         it does not populate os.environ. conversation_service.py:214 and this
         harness both read the flag with os.getenv, so a .env entry would be
         invisible to them regardless.

    It must be a real environment variable, which is exactly what it is in
    production (Render sets it on philosopher-api). apps/api/.env carries the
    API key, which IS a declared Settings field.
    """
    if require is None:
        return 0
    want = require == "true"
    if want == harness.PHENOMENOLOGY_BRIDGE_ENABLED:
        return 0
    print(
        f"REFUSING: --require-bridge {require} but "
        f"PHENOMENOLOGY_BRIDGE_ENABLED resolves to "
        f"{harness.PHENOMENOLOGY_BRIDGE_ENABLED}. Nothing has been sent.",
        file=sys.stderr,
    )
    print(
        "  It must be a real ENVIRONMENT VARIABLE, not a line in apps/api/.env: "
        "config.Settings forbids extra fields, so a .env entry raises "
        "ValidationError at import, and pydantic would not populate os.environ "
        "anyway. Production sets it on philosopher-api (true, verified "
        "2026-09-22). Locally:",
        file=sys.stderr,
    )
    print(
        "      PHENOMENOLOGY_BRIDGE_ENABLED=true python -m evals.run ...",
        file=sys.stderr,
    )
    return 2


def _select(samples: list[Sample], personas, limit) -> list[Sample]:
    if personas:
        wanted = set(personas)
        samples = [s for s in samples if s.persona_slug in wanted]
    if limit:
        samples = samples[:limit]
    return samples


async def _main_async(args) -> int:
    # Before anything is written. See _manifest's note on git_dirty.
    dirty_at_start = _git_dirty()
    samples = _select(build_samples(), args.persona, args.limit)

    if args.dry_run:
        # Assemble every prompt and send nothing. Proves the harness runs, prints
        # the input profile, and WRITES A MANIFEST — a pre-flight that exists
        # only in terminal scrollback is not a record, and this repository's
        # standing complaint is claims that were never written down.
        chars = bridged = 0
        for s in samples:
            system, bridge = harness.assemble_system(
                PERSONA_REGISTRY[s.persona_slug], s.user_message, deep=s.deep,
                arm=args.arm,
            )
            chars += len(system)
            bridged += 1 if bridge else 0
        mean_chars = chars // max(1, len(samples))

        manifest = _manifest(args.arm, args.note, samples, [], dry_run=True,
                             git_dirty=dirty_at_start)
        manifest["input_profile"] = {
            "mean_system_prompt_chars": mean_chars,
            "approx_tokens_chars_over_3_6": int(mean_chars / 3.6),
            "samples_with_bridge_match": bridged,
            "completions_that_would_be_sent":
                len(samples) * len(harness.ARMS_BY_PLAN),
        }
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
        out = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}_{args.arm}_dryrun"
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

        print(f"dry run: {len(samples)} samples, "
              f"{len(samples) * len(harness.ARMS_BY_PLAN)} completions would be sent")
        print(f"mean system prompt: {mean_chars} chars "
              f"(~{int(mean_chars / 3.6)} tokens)")
        print(f"samples with a bridge match: {bridged}/{len(samples)}")
        print(f"phenomenology_bridge_enabled={harness.PHENOMENOLOGY_BRIDGE_ENABLED}")
        print(f"prompt_set_hash={prompt_set_hash()}")
        print(f"\nwrote {out / 'manifest.json'}")
        return 0

    def progress(done, total, c):
        mark = "!" if c.error else "."
        sys.stderr.write(mark)
        if done % 50 == 0 or done == total:
            sys.stderr.write(f" {done}/{total}\n")
        sys.stderr.flush()

    completions = await harness.generate_all(
        samples, concurrency=args.concurrency, progress=progress, arm=args.arm,
    )
    by_id = {s.sample_id: s for s in samples}
    scores = [score(c, by_id[c.sample_id]) for c in completions]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
    out = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}_{args.arm}"
    manifest, rows = _write(out, args.arm, samples, completions, scores, args.note,
                            git_dirty=dirty_at_start)

    print(f"\nwrote {out}")
    print(f"  completions {manifest['n_completions']}  errors {manifest['errors']}")
    print(f"  cost ${manifest['cost'].get('_total_usd', 0)}")
    return 1 if manifest["errors"] else 0


def _rescore(directory: str) -> int:
    """Re-run the scorers over a stored run. Free; no API calls."""
    out = Path(directory)
    by_id = {s.sample_id: s for s in build_samples()}
    completions = []
    with open(out / "completions.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            completions.append(harness.Completion(
                sample_id=d["sample_id"], problem_id=d["problem_id"],
                persona_slug=d["persona_slug"], mode=d["mode"],
                plan=d["plan"], model=d["model"],
                user_message=d["user_message"], reply=d["reply"],
                system_prompt="", bridge_matched=d.get("bridge_matched"),
                tokens=d.get("tokens") or {}, error=d.get("error"),
            ))
    scores = [score(c, by_id[c.sample_id]) for c in completions]
    with open(out / "scores.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for s in scores:
            w.writerow(to_row(s))
    with open(out / "summary.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SUMMARY_COLUMNS)
        w.writeheader()
        w.writerows(summarise(scores))

    # THE MANIFEST MUST MOVE TOO. A rescore changes what the numbers mean; if
    # prompt_set_hash still described the scoring data the run was ORIGINALLY
    # scored against, compare.py would gate on a claim that is no longer true —
    # either refusing a legitimate comparison, or passing one it should refuse.
    mpath = out / "manifest.json"
    if mpath.exists():
        m = json.loads(mpath.read_text(encoding="utf-8"))
        before = m.get("prompt_set_hash")
        now = prompt_set_hash()
        if before != now:
            m["rescored_from_prompt_set_hash"] = before
            m["prompt_set_hash"] = now
        m["rescored_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        m["rescored_at_git_sha"] = _git_sha()
        with open(mpath, "w", encoding="utf-8", newline=chr(10)) as fh:
            json.dump(m, fh, indent=2, ensure_ascii=False)
            fh.write(chr(10))
        if before != now:
            print(f"  manifest prompt_set_hash {before} -> {now}")

    print(f"rescored {len(scores)} completions in {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m evals.run")
    p.add_argument("--arm", default="baseline", choices=list(arm_b.ARMS),
                   help="baseline = run-1 prompt, unchanged. tightened = arm B, "
                        "the founder-approved directive appended last.")
    p.add_argument("--note", default="", help="one line into the manifest")
    p.add_argument("--out", default=None, help="output dir (default: dated folder)")
    p.add_argument("--persona", action="append", default=None,
                   help="restrict to a persona slug; repeatable")
    p.add_argument("--limit", type=int, default=None, help="first N samples only")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--dry-run", action="store_true",
                   help="assemble every prompt, send nothing, spend nothing; "
                        "writes manifest.json with dry_run: true")
    p.add_argument("--require-bridge", choices=["true", "false"], default=None,
                   help="exit 2 BEFORE sending anything if "
                        "PHENOMENOLOGY_BRIDGE_ENABLED does not match")
    p.add_argument("--rescore", default=None, metavar="DIR",
                   help="re-score a stored run from its completions.jsonl")
    args = p.parse_args()

    if args.rescore:
        return _rescore(args.rescore)
    if args.arm not in arm_b.ARMS:
        print(f"REFUSING: --arm {args.arm!r} is not one of {arm_b.ARMS}. "
              f"Nothing has been sent.", file=sys.stderr)
        return 2
    gate = _check_bridge(args.require_bridge)
    if gate:
        return gate
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
