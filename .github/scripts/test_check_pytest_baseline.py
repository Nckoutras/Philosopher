"""Tests for check_pytest_baseline.py.

Stdlib unittest, like the script itself, and run by backend-ci as its own step
BEFORE the gate. Not part of the apps/api pytest suite on purpose: a checker
whose own tests run inside the suite it gates would be grading its own failures.

    python -m unittest discover -s .github/scripts -p "test_*.py" -v
"""
import contextlib
import importlib.util
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "check_pytest_baseline", _HERE / "check_pytest_baseline.py"
)
cpb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpb)


class ParseResultLines(unittest.TestCase):
    def test_a_plain_id_with_a_message(self):
        out = "FAILED tests/test_a.py::test_x - AssertionError: 1 != 2"
        self.assertEqual(cpb.parse_result_lines(out), ["tests/test_a.py::test_x"])

    def test_a_parametrized_id_with_spaces_and_a_message(self):
        # The regression: this line used to match nothing and was dropped.
        out = "FAILED tests/test_s.py::test_band[I want to die-high] - assert 'low' == 'high'"
        self.assertEqual(
            cpb.parse_result_lines(out),
            ["tests/test_s.py::test_band[I want to die-high]"],
        )

    def test_a_parametrized_id_with_spaces_and_no_message(self):
        out = "FAILED tests/test_s.py::test_band[I want to die]"
        self.assertEqual(cpb.parse_result_lines(out), ["tests/test_s.py::test_band[I want to die]"])

    def test_a_param_that_contains_a_dash_separator_and_a_bracket(self):
        out = "FAILED tests/t.py::test_p[a - b] c] - ValueError: x"
        self.assertEqual(cpb.parse_result_lines(out), ["tests/t.py::test_p[a - b] c]"])

    def test_an_escaped_non_ascii_param(self):
        out = r"FAILED tests/t.py::test_el[θέλω να πεθάνω] - assert False"
        self.assertEqual(len(cpb.parse_result_lines(out)), 1)
        self.assertTrue(cpb.parse_result_lines(out)[0].endswith(r"ω]"))

    def test_a_collection_error_on_a_path(self):
        out = "ERROR tests/test_broken.py - ImportError: no module named x"
        self.assertEqual(cpb.parse_result_lines(out), ["tests/test_broken.py"])

    def test_a_call_failure_and_a_teardown_error_are_two_lines(self):
        out = "FAILED tests/t.py::test_x - a\nERROR tests/t.py::test_x - b"
        self.assertEqual(len(cpb.parse_result_lines(out)), 2)
        self.assertEqual(cpb.parse_failures(out), {"tests/t.py::test_x"})

    def test_other_lines_are_ignored(self):
        out = "tests/t.py::test_x PASSED\n.....F...\nsome FAILED text in the middle"
        self.assertEqual(cpb.parse_result_lines(out), [])


class ParseSummaryCount(unittest.TestCase):
    def test_failed_and_errors_are_summed(self):
        self.assertEqual(cpb.parse_summary_count("3 failed, 120 passed, 2 errors in 4.20s"), 5)

    def test_the_rule_form(self):
        self.assertEqual(
            cpb.parse_summary_count("========= 1 failed, 9 passed, 3 warnings in 0.51s =========="), 1
        )

    def test_a_green_run_is_zero(self):
        self.assertEqual(cpb.parse_summary_count("3853 passed, 12 skipped in 98.10s (0:01:38)"), 0)

    def test_xfailed_is_not_a_failure(self):
        self.assertEqual(cpb.parse_summary_count("10 passed, 2 xfailed, 1 xpassed in 1.00s"), 0)

    def test_the_last_summary_line_wins(self):
        out = "1 failed in 0.1s\n...\n2 failed, 1 error in 0.3s"
        self.assertEqual(cpb.parse_summary_count(out), 3)

    def test_no_summary_is_none(self):
        self.assertIsNone(cpb.parse_summary_count("no tests ran in 0.01s"))
        self.assertIsNone(cpb.parse_summary_count("ImportError while loading conftest"))


class MainExitCode(unittest.TestCase):
    """End to end through --report, against an empty baseline (as committed)."""

    def _run(self, report_text):
        with tempfile.TemporaryDirectory() as d:
            report = pathlib.Path(d) / "out.txt"
            baseline = pathlib.Path(d) / "baseline.txt"
            report.write_text(report_text, encoding="utf-8")
            baseline.write_text("# empty\n", encoding="utf-8")
            argv = ["check", "--report", str(report), "--baseline", str(baseline)]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                return cpb.main()

    def test_a_green_run_passes(self):
        self.assertEqual(self._run("3853 passed in 98.10s\n"), 0)

    def test_a_failure_with_a_spaced_id_fails_the_gate(self):
        # Before the fix this returned 0: the line was dropped and "passed" was present.
        out = (
            "FAILED tests/test_s.py::test_band[I want to die] - assert 'low' == 'high'\n"
            "1 failed, 3852 passed in 98.10s\n"
        )
        self.assertEqual(self._run(out), 1)

    def test_a_result_line_the_parser_misses_fails_the_gate(self):
        # pytest says 1, nothing parses: whatever that line was, it must not vanish.
        # This is the hole's general shape -- the spaced id was one instance of it.
        out = (
            "FAILED [some shape this parser has never seen]\n"
            "1 failed, 10 passed in 1.00s\n"
        )
        self.assertEqual(self._run(out), 1)

    def test_no_summary_fails_the_gate(self):
        self.assertEqual(self._run("ImportError while loading conftest\n"), 1)


if __name__ == "__main__":
    unittest.main()
