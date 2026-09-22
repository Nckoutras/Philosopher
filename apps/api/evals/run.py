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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from personas import PERSONA_REGISTRY

from . import harness
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
    try:
        return bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        ).strip())
    except Exception:
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


def _write(out: Path, arm: str, samples, completions, scores: list[Scores], note: str):
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

    manifest = {
        "arm": arm,
        "note": note,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "git_dirty": _git_dirty(),
        "prompt_set_hash": prompt_set_hash(),
        "n_samples": len(samples),
        "n_completions": len(completions),
        "deep_problem_ids": sorted(DEEP_PROBLEM_IDS),
        "personas": sorted(PERSONA_REGISTRY),
        "models": sorted({c.model for c in completions}),
        "phenomenology_bridge_enabled": harness.PHENOMENOLOGY_BRIDGE_ENABLED,
        "postprocessing_enabled_env": os.getenv("POSTPROCESSING_ENABLED"),
        "errors": sum(1 for c in completions if c.error),
        "cost": _cost(completions),
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
    with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest, rows


def _select(samples: list[Sample], personas, limit) -> list[Sample]:
    if personas:
        wanted = set(personas)
        samples = [s for s in samples if s.persona_slug in wanted]
    if limit:
        samples = samples[:limit]
    return samples


async def _main_async(args) -> int:
    samples = _select(build_samples(), args.persona, args.limit)

    if args.dry_run:
        # Assemble every prompt and send nothing. Proves the harness runs and
        # prints the input profile, for free.
        total = 0
        for s in samples:
            system, bridge = harness.assemble_system(
                PERSONA_REGISTRY[s.persona_slug], s.user_message, deep=s.deep,
            )
            total += len(system)
        print(f"dry run: {len(samples)} samples, "
              f"{len(samples) * len(harness.ARMS_BY_PLAN)} completions would be sent")
        print(f"mean system prompt: {total // max(1, len(samples))} chars "
              f"(~{total // max(1, len(samples)) // 4} tokens, rough)")
        print(f"phenomenology_bridge_enabled={harness.PHENOMENOLOGY_BRIDGE_ENABLED}")
        print(f"prompt_set_hash={prompt_set_hash()}")
        return 0

    def progress(done, total, c):
        mark = "!" if c.error else "."
        sys.stderr.write(mark)
        if done % 50 == 0 or done == total:
            sys.stderr.write(f" {done}/{total}\n")
        sys.stderr.flush()

    completions = await harness.generate_all(
        samples, concurrency=args.concurrency, progress=progress,
    )
    by_id = {s.sample_id: s for s in samples}
    scores = [score(c, by_id[c.sample_id]) for c in completions]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
    out = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}_{args.arm}"
    manifest, rows = _write(out, args.arm, samples, completions, scores, args.note)

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
    print(f"rescored {len(scores)} completions in {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m evals.run")
    p.add_argument("--arm", default="baseline",
                   help="label for this arm, e.g. baseline / tightened")
    p.add_argument("--note", default="", help="one line into the manifest")
    p.add_argument("--out", default=None, help="output dir (default: dated folder)")
    p.add_argument("--persona", action="append", default=None,
                   help="restrict to a persona slug; repeatable")
    p.add_argument("--limit", type=int, default=None, help="first N samples only")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--dry-run", action="store_true",
                   help="assemble every prompt, send nothing, spend nothing")
    p.add_argument("--rescore", default=None, metavar="DIR",
                   help="re-score a stored run from its completions.jsonl")
    args = p.parse_args()

    if args.rescore:
        return _rescore(args.rescore)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
