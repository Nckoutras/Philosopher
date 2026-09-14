"""Γ-2 — a 'no' is excluded from the letter spine, at BOTH sites.

WHY TWO NEAR-IDENTICAL TESTS. The weekly and monthly spines are separate blocks
in arq_worker.py that have always carried the same predicate written out twice.
That is the classic fix-one-miss-one shape, and the miss would be invisible: both
letters still generate, both still read plausibly, and the only symptom is that
one of them keeps re-anchoring on a claim the reader said was not true of them.
So there is one test per call site, deliberately, rather than one test of the
shared helper standing in for both.

THE NULL TRAP, which is the real subject of this file. `ring_true != 'no'`
evaluates to NULL for every unanswered insight, and SQL drops NULL rows from a
WHERE — so the obvious spelling would silently exclude every insight nobody has
voted on, which is nearly all of them. The letters would keep generating from a
spine quietly reduced to answered rows. `IS DISTINCT FROM` treats NULL as a value
and keeps them. test_unanswered_insights_are_kept is the assertion that would go
red if someone "simplified" it back.

Run: cd apps/api && pytest tests/workers/test_letter_spine_verdict.py -v
"""
import sys
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import ast
import inspect
import pathlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models import Insight
from workers.arq_worker import _insight_spine_conditions

USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
START = datetime(2026, 9, 7, tzinfo=timezone.utc)
END = START + timedelta(days=7)


def _compiled():
    stmt = select(Insight).where(*_insight_spine_conditions(USER_ID, START, END))
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


# ── The predicate ────────────────────────────────────────────────────────────

def test_a_no_is_excluded():
    sql = _compiled()
    assert "ring_true" in sql, f"the spine no longer filters on a verdict:\n{sql}"
    assert "'no'" in sql


def test_unanswered_insights_are_kept():
    """IS DISTINCT FROM, never !=.

    This is the one assertion standing between the letter and a spine containing
    only the handful of insights a reader has voted on. Asserted on the compiled
    SQL because the difference is invisible in Python and only appears in the
    three-valued logic Postgres applies.
    """
    sql = _compiled()
    assert "IS DISTINCT FROM" in sql, (
        "the verdict filter must use IS DISTINCT FROM: `ring_true != 'no'` is NULL "
        "for every unanswered insight, and a WHERE drops NULL rows — which would "
        f"silently empty the spine of everything nobody has voted on.\n{sql}"
    )
    assert "ring_true !=" not in sql


def test_the_pre_existing_filters_are_untouched():
    """Γ-2 adds a condition; it must not quietly drop one. A spine that stopped
    filtering is_dismissed would re-anchor on discarded insights."""
    sql = _compiled()
    assert "is_dismissed" in sql
    assert "user_id" in sql
    assert "created_at" in sql


# ── One test per call site ───────────────────────────────────────────────────

def _calls_in(fn_name: str) -> set[str]:
    """Every function called inside the named top-level worker function."""
    src = pathlib.Path(inspect.getfile(_insight_spine_conditions)).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            return {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
    raise AssertionError(f"{fn_name} not found in arq_worker.py")


@pytest.mark.parametrize("task", [
    "generate_weekly_letter_task",
    "generate_monthly_letter_task",
])
def test_each_letter_task_uses_the_shared_spine_predicate(task):
    """Parametrised rather than merged into one assertion so a failure names WHICH
    letter lost the filter. If one of these ever goes red alone, that is the
    fix-one-miss-one this file exists for, caught on the side that was missed."""
    assert "_insight_spine_conditions" in _calls_in(task), (
        f"{task} no longer builds its spine from the shared predicate — its filter "
        f"has been inlined and can now drift from the other letter's"
    )


@pytest.mark.parametrize("task", [
    "generate_weekly_letter_task",
    "generate_monthly_letter_task",
])
def test_no_letter_task_inlines_its_own_spine_filter(task):
    """The other direction: a helper that is called but bypassed by a second,
    hand-written query would pass the test above while behaving as before."""
    src = pathlib.Path(inspect.getfile(_insight_spine_conditions)).read_text(encoding="utf-8")
    tree = ast.parse(src)
    node = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == task
    )
    body = ast.get_source_segment(src, node) or ""
    assert "Insight.is_dismissed" not in body, (
        f"{task} filters Insight.is_dismissed inline; that predicate belongs to "
        f"_insight_spine_conditions so both letters keep the same definition"
    )
