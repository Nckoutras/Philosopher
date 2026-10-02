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
#
# The id is `path::name`, then an optional `[params]` that MAY CONTAIN SPACES:
# `test_x[I want to die]`. The pattern used to be `(\S+?)`, which cannot cross a
# space, so a failing parametrized test whose id had one matched nothing at all
# and was dropped from the failing set -- silently, and the run went green. On
# 2026-10-02, 1,106 of the 3,853 collected ids had a space, most of them the
# safety lexicon and tier tests. The bracket part is matched lazily, so it ends
# at the first `]` after which only an optional ` - message` remains.
_RESULT_LINE = re.compile(
    r"^(?:FAILED|ERROR)\s+([^\s\[]+(?:\[.*?\])?)(?:\s+-\s.*)?$"
)

# pytest's final summary: `3 failed, 120 passed, 1 error in 4.20s`, with or
# without the `=` rule around it.
_SUMMARY_LINE = re.compile(r"^=*\s*(?:\d+ \w+(?:, )?)+ in [\d.]+s\b")
_SUMMARY_COUNT = re.compile(r"(\d+) (failed|errors?)\b")


def parse_result_lines(text):
    """Every failed/errored test id in pytest's -rfE summary, one per line.

    A list, not a set: a test that fails in its call AND errors in teardown is
    reported twice and counted twice by pytest, and the count check below needs
    the same arithmetic.
    """
    found = []
    for line in text.splitlines():
        m = _RESULT_LINE.match(line.strip())
        if m:
            found.append(m.group(1))
    return found


def parse_failures(text):
    """Extract the set of failed/errored test ids from pytest output."""
    return set(parse_result_lines(text))


def parse_summary_count(text):
    """failed + errors from pytest's own final summary line; None if absent."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if _SUMMARY_LINE.match(line):
            return sum(int(n) for n, _ in _SUMMARY_COUNT.findall(line))
    return None


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

    lines = parse_result_lines(output)
    failing = set(lines)

    # A run that collected nothing is not a pass. Without this, a collection
    # error or a bad path would produce zero failures and a green check.
    reported = parse_summary_count(output)
    if reported is None:
        print("::error::pytest produced no recognisable result summary - treating as failure")
        return 1

    # pytest's own count is the check on this script's parsing. If they differ,
    # some FAILED/ERROR line was not understood, and the failure it describes
    # would otherwise be dropped without a trace -- which is how a space in a
    # parametrized id went unseen. A mismatch fails, whatever the baseline says.
    if reported != len(lines):
        print(f"::error::pytest reports {reported} failed+errors but {len(lines)} "
              "FAILED/ERROR lines were parsed - a result line was not understood")
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
