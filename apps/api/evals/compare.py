"""Diff two runs.

    cd apps/api && python -m evals.compare results/<A> results/<B>

IT REFUSES BEFORE IT DIFFS. Two runs are only comparable when they measured the
same thing, and every way that can fail is silent — the sample_ids line up
perfectly whether or not the prompt set, the bridge flag or the model changed
underneath. So the manifests are checked first and a mismatch is an error with
the offending keys named, not a warning above a table someone will read anyway.

WHAT MUST MATCH, and why each one:

    prompt_set_hash   different prompt text is a different measurement
    models            Haiku and Sonnet are not each other; cross-model rows
                      would look like an effect
    phenomenology_bridge_enabled
                      the bridge changes the system prompt on 9 of 10 problems,
                      so a run with it off is a different corpus entirely
    deep_problem_ids  the mode split decides which band a sample is scored
                      against
    personas          a persona added between runs shifts every aggregate

WHAT IS ALLOWED TO DIFFER, and is printed rather than enforced:

    git_sha           the A/B arm IS a code change; requiring equality would
                      make the tool useless for the thing it was built for
    arm, note, generated_at_utc, cost

A DIRTY TREE IS REPORTED, LOUDLY. `git_dirty: true` in either manifest means the
run's git_sha does not describe what actually ran, so the comparison has no
provenance even if every gate above passes.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

MUST_MATCH = (
    "prompt_set_hash",
    "models",
    "phenomenology_bridge_enabled",
    "deep_problem_ids",
    "personas",
)

# Rates: lower is better for all of them, so a negative delta is an improvement.
RATE_COLUMNS = (
    "fm_over_rate", "std_over_rate",
    "persona_lexicon_rate", "universal_lexicon_rate",
    "anti_flex_rate", "modern_leak_rate", "would_correct_rate",
    # B2. NOTE the direction: for these four, "lower is better" is TRUE for
    # ends_q_rate and no_opening_rate and FALSE for the two stance rates, which
    # the arrows below do not know. Read the sign, not the word.
    "ends_q_rate", "no_opening_rate", "stance_observation_rate", "stance_any_rate",
)
KEY = ("persona_slug", "mode", "plan", "model")


def _load(d: Path) -> tuple[dict, dict]:
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    rows = {}
    with open(d / "summary.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows[tuple(r[k] for k in KEY)] = r
    return manifest, rows


def _gate(a: dict, b: dict, da: Path, db: Path) -> list[str]:
    problems = []
    for key in MUST_MATCH:
        if a.get(key) != b.get(key):
            problems.append(
                f"  {key}:\n    {da.name}: {a.get(key)!r}\n    {db.name}: {b.get(key)!r}"
            )
    return problems


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m evals.compare")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--force", action="store_true",
                   help="diff anyway after a gate failure; the header says so")
    args = p.parse_args()

    da, db = Path(args.a), Path(args.b)
    ma, ra = _load(da)
    mb, rb = _load(db)

    problems = _gate(ma, mb, da, db)
    if problems and not args.force:
        print("REFUSING: these two runs did not measure the same thing.\n")
        print("\n".join(problems))
        print("\nFix the run, or pass --force if you know why they differ.")
        return 2

    print(f"A  {da.name}   arm={ma['arm']!r}  git={ma['git_sha'][:8]}"
          f"{'  DIRTY' if ma.get('git_dirty') else ''}")
    print(f"B  {db.name}   arm={mb['arm']!r}  git={mb['git_sha'][:8]}"
          f"{'  DIRTY' if mb.get('git_dirty') else ''}")
    if ma.get("git_dirty") or mb.get("git_dirty"):
        print("\n!! a run was made from a dirty tree: its git_sha does not "
              "describe what ran, and this comparison has no provenance.")
    if problems:
        print("\n!! FORCED past a gate failure:\n" + "\n".join(problems))
    print()

    only_a = sorted(set(ra) - set(rb))
    only_b = sorted(set(rb) - set(ra))
    for label, rows in (("A only", only_a), ("B only", only_b)):
        if rows:
            print(f"!! {label}: {len(rows)} summary rows — "
                  f"aggregates below are not over the same population")
            for r in rows[:5]:
                print(f"     {'/'.join(r)}")

    shared = sorted(set(ra) & set(rb))
    width = max((len("/".join(k)) for k in shared), default=10)

    for col in RATE_COLUMNS:
        moved = []
        for k in shared:
            va, vb = float(ra[k][col]), float(rb[k][col])
            if va != vb:
                moved.append((k, va, vb))
        print(f"\n{col}   ({len(moved)} of {len(shared)} rows moved)")
        if not moved:
            print("  unchanged")
            continue
        for k, va, vb in sorted(moved, key=lambda t: t[2] - t[1]):
            d = vb - va
            arrow = "improved" if d < 0 else "worse"
            print(f"  {'/'.join(k):<{width}}  {va:>7.3f} -> {vb:>7.3f}   "
                  f"{d:+.3f}  {arrow}")

    # Totals, weighted by n, so the headline is not an average of averages.
    print("\nweighted totals")
    for col in RATE_COLUMNS:
        na = sum(int(ra[k]["n"]) for k in shared)
        nb = sum(int(rb[k]["n"]) for k in shared)
        if not na or not nb:
            continue
        ta = sum(float(ra[k][col]) * int(ra[k]["n"]) for k in shared) / na
        tb = sum(float(rb[k][col]) * int(rb[k]["n"]) for k in shared) / nb
        print(f"  {col:<24} {ta:>7.3f} -> {tb:>7.3f}   {tb - ta:+.3f}")

    print("\nRates only. No pass/fail — see manifest.caveats.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
