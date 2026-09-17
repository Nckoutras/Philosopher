"""Layer C's SQL runs against the real schema — read out of the workflow file.

WHY THIS EXISTS, and it is the Gamma-5 lesson applied to the one query in this
feature that nothing else would ever execute. A query living in a YAML file is a
claim exactly like a query living in a runbook: written once against the schema
of the day, never re-run, and confidently wrong the moment a column is renamed.
The difference here is worse, not better. `docs/RUNBOOK_LOOP_METRICS.md` at
least gets pasted into psql by a human during the hour it matters. This one runs
unattended every thirty minutes, and the only reader of its failure is an email
saying the worker is down.

A BROKEN QUERY IN THIS WORKFLOW FAILS THE RUN, WHICH LOOKS EXACTLY LIKE A DEAD
WORKER. `psql` exits non-zero on a missing column under ON_ERROR_STOP=1, the
step fails, the founder gets the same red run and the same email they would get
from a genuine outage. So the one mistake this file prevents is the expensive
kind: an alert that cries wolf while looking indistinguishable from the wolf.

SO THE TEST READS THE WORKFLOW, it does not restate the SQL — the same rule
test_runbook_queries.py states for the runbook. A copy pinned here would stay
green forever while the shipped copy rotted, which is the failure mode rather
than a partial fix. The string executed below is the string the runner sends.

WHAT AN EMPTY DATABASE PROVES, AND WHAT IT DOES NOT. Every table and column the
query names must exist, and the aggregate must return ONE ROW over zero input
rows -- which is the Gamma-5 cardinality trap, and here it is load-bearing
rather than incidental: the workflow reads `last_seen` and `age_minutes` out of
that row unconditionally. A query that returned NO row on an empty table would
leave both variables empty, the numeric comparison would fail on an empty
string, and the step would go red for a reason having nothing to do with the
worker. The coalesce sentinels are what make the "never ran" branch reachable,
and this file asserts they actually come back.

It does NOT prove the workflow's threshold arithmetic. That is shell, it is
exercised against a stub psql, and it is not a claim about the schema.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_worker_liveness_query.py -v
"""
import pathlib
import re

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

WORKFLOW = (
    pathlib.Path(__file__).resolve().parents[4]
    / ".github" / "workflows" / "worker-liveness.yml"
)

# The SQL is the argument to psql's -c, and it contains no double quote of its
# own, so the shortest well-formed match is the whole statement.
SQL_IN_PSQL = re.compile(r'-c "(SELECT [^"]+)"')


def _workflow_sql() -> str:
    assert WORKFLOW.is_file(), f"workflow not found at {WORKFLOW}"
    found = SQL_IN_PSQL.findall(WORKFLOW.read_text(encoding="utf-8"))
    assert len(found) == 1, (
        f"expected exactly one psql -c SELECT in {WORKFLOW.name}, found "
        f"{len(found)}. If a second query was added, extend this file; if the "
        f"one query was removed or reshaped, say so here."
    )
    return found[0]


def test_the_workflow_still_carries_the_query_this_file_checks():
    """A guard on the guard. If the psql call is reshaped, the test below would
    quietly check nothing and stay green -- the same 'absence looks like
    success' shape as the 2026-09-01 no-run trap.
    """
    sql = _workflow_sql()
    assert "job_run" in sql
    assert "worker_heartbeat" in sql
    assert "succeeded" in sql


async def test_the_liveness_query_is_valid_against_the_live_schema(db):
    """Execute it. Every table and column it names must exist.

    No bind parameters: the workflow interpolates nothing into this string, and
    that is deliberate -- the threshold comparison happens in the shell, so the
    secret never meets string concatenation with a value.
    """
    result = await db.execute(text(_workflow_sql()))
    rows = result.all()

    # ONE ROW OVER ZERO INPUT ROWS. An aggregate with no GROUP BY always returns
    # a row; "no heartbeats yet" is a row saying so, not an empty result. The
    # workflow depends on this: it reads both values out of the row without
    # first checking that a row came back.
    assert len(rows) == 1
    assert len(rows[0]) == 2


async def test_an_empty_table_answers_with_the_sentinels_the_workflow_reads(db):
    """The "never ran" branch, proven reachable rather than assumed.

    This is the state a brand-new database is in, and it is also the state a
    worker that has never once reached the database leaves behind -- the gap
    Layer A's history floor deliberately cannot see. If the coalesce defaults
    ever changed, the workflow would compare an empty string with -gt and go red
    with a shell error instead of the sentence it was written to print.
    """
    last_seen, age_minutes = (await db.execute(text(_workflow_sql()))).one()

    assert last_seen == "never"
    # Returned as text by coalesce, and compared by the shell with -gt, so it
    # has to be an integer literal rather than NULL or an empty string.
    assert age_minutes == "-1"
    assert int(age_minutes) == -1
