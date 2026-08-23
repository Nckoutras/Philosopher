#!/usr/bin/env python3
"""Run the backend suite and fail only on failures NOT in the committed baseline.

The suite has a set of known-failing tests (TD-45, broken mock harnesses). A CI
job that is red from day one teaches everyone to ignore CI, so this compares the
failing set against apps/api/tests/ci_baseline_failures.txt and fails only on
ids that are not listed.

Comparison is BY TEST ID, never by count. 28 failures could be 1 baseline test
fixed plus 1 new regression; a count check would call that green and would be
worse than no check at all.

A baseline test that starts passing is NOT a failure — it prints a notice
asking for the baseline to be pruned, and exits 0.

Stdlib only, by design: no dependency of this script may break CI itself.

Usage:
    python .github/scripts/check_pytest_baseline.py
    python .github/scripts/check_pytest_baseline.py --report existing-output.txt
"""
import argparse
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_API_DIR = REPO_ROOT / "apps" / "api"
DEFAULT_BASELINE = DEFAULT_API_DIR / "tests" / "ci_baseline_failures.txt"

# `FAILED path::test - message` and `ERROR path::test - message`. The message
# suffix is optional and is discarded: it carries assertion text that changes
# between runs, while the id is stable.
_RESULT_LINE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+?)(?:\s+-\s.*)?$")


def parse_failures(text):
    """Extract the set of failed/errored test ids from pytest output."""
    found = set()
    for line in text.splitlines():
        m = _RESULT_LINE.match(line.strip())
        if m:
            found.add(m.group(1))
    return found


def load_baseline(path):
    """Read the baseline, ignoring comments and blank lines."""
    if not path.exists():
        sys.stderr.write(f"baseline file not found: {path}\n")
        raise SystemExit(2)
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line)
    return ids


def run_pytest(api_dir):
    """Run the suite and return its combined output.

    -rfE prints the FAILED/ERROR summary lines this script parses; --tb=no keeps
    tracebacks out so a traceback line can never be mistaken for a summary line.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-rfE"],
        cwd=str(api_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=pathlib.Path, default=DEFAULT_BASELINE)
    ap.add_argument("--api-dir", type=pathlib.Path, default=DEFAULT_API_DIR)
    ap.add_argument(
        "--report",
        type=pathlib.Path,
        help="Parse this pytest output file instead of running the suite.",
    )
    args = ap.parse_args()

    baseline = load_baseline(args.baseline)

    if args.report:
        output = args.report.read_text(encoding="utf-8", errors="replace")
    else:
        output = run_pytest(args.api_dir)
        print(output)

    failing = parse_failures(output)

    # A run that collected nothing is not a pass. Without this, a collection
    # error or a bad path would produce zero failures and a green check.
    if not failing and "passed" not in output:
        print("::error::pytest produced no recognisable result summary - treating as failure")
        return 1

    new_failures = sorted(failing - baseline)
    now_passing = sorted(baseline - failing)

    print("")
    print("=" * 68)
    print(f"baseline entries : {len(baseline)}")
    print(f"failing this run : {len(failing)}")
    print(f"new failures     : {len(new_failures)}")
    print(f"fixed (prunable) : {len(now_passing)}")
    print("=" * 68)

    if now_passing:
        print("")
        print("These baseline tests now PASS. Prune them from")
        print(f"{args.baseline.relative_to(REPO_ROOT).as_posix()} so the baseline keeps shrinking:")
        for t in now_passing:
            print(f"  - {t}")
            print(f"::notice::baseline test now passing, prune it: {t}")

    if new_failures:
        print("")
        print("NEW FAILURES - not in the baseline:")
        for t in new_failures:
            print(f"  - {t}")
            print(f"::error::new test failure not in baseline: {t}")
        print("")
        print("If this is a genuine pre-existing failure rather than a regression")
        print("you introduced, say so explicitly in the PR - do not silently add it")
        print("to the baseline.")
        return 1

    print("")
    print("OK - no new failures against the baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
