"""The runbook's SQL runs against the real schema — read out of the markdown.

WHY THIS FILE EXISTS. `docs/RUNBOOK_LOOP_METRICS.md` carries the queries that
answer two Blueprint §16 gates. A query in a document is exactly the kind of
claim this project's failure log is about: it is written once against the schema
of the day, copied forward through rotations, and nothing ever re-checks it. A
column rename three months from now leaves the runbook confidently wrong, and
the way anyone finds out is by pasting it into psql during the one hour it
matters.

SO THE TEST READS THE DOCUMENT, it does not restate the SQL. Restating it here
would pin a copy — green forever while the copy in the runbook rotted, which is
the failure mode rather than a partial fix. The strings executed below are the
strings a reader will paste.

WHAT THE QUERIES' LOGIC WAS CHECKED AGAINST, since this file does not check it.
On 2026-09-15 both queries were run on a scratch PostgreSQL 16.4 cluster with a
discriminating fixture, to verify they mean what the runbook says they mean:

  activation   6 users -> cohort_size 4, activated 1, pct 25.0
               excluded: an admin; a user 1h old (window not yet finished);
               a user whose activity fell OUTSIDE 72h; a user whose third
               conversation was soft-deleted; a user with only one thread.
  memory trust insight 4/1 25.0 | mirror 2/1 50.0 | self_comparison 3/2 66.7
               | ALL SURFACES 9/4 44.4, with the ROLLUP row sorted last and a
               NULL ring_true excluded from its surface's denominator.

The two SAMENESS queries (D2, added 2026-09-16) were not rehearsed on a fixture.
They were run once against PRODUCTION, and their output is the runbook's stated
baseline — §7b and §7c carry the numbers. That is a stronger check than a fixture
for what these two need to be right about (they name real columns and return the
shape the runbook prints) and a weaker one for their arithmetic, which nothing
verifies. Their interpretation is the founder's, as the activation query's is.

  sameness A   control 2745 pairs mean 0.0096 | gap 1-2 332 @ 0.0606 (6.3x)
               | gap 3-10 861 @ 0.0459 (4.8x) | gap 11+ 661 @ 0.0429 (4.5x)
  sameness B   turn 1-2 50.0% end-question | 3-5 31.7 | 6-10 31.0 | 11-20 26.4
               | 21+ 12.7, mean words 37.7 -> 32.4 across the same bands

Reproduce it rather than trust this paragraph if a clause is ever in doubt. It is
recorded here because it is evidence that expires: the next schema change makes
it a claim about the past, which is what the CLAUDE.md failure log is about.

WHAT IS AND IS NOT ASSERTED. These run against an EMPTY database, so they assert
that each query is valid SQL over the migration-built schema — every table,
column and function it names exists, and the shape it returns is the shape the
runbook describes. They do NOT assert that the numbers are right; that needs a
fixture encoding the gate's own definition, which would be this test asserting
its own interpretation of §16 rather than the schema. The activation query's one
interpretive choice is stated in the runbook and is the founder's to change.

An empty result is the CORRECT outcome for the activation query here: with no
users, the cohort is empty and the percentage is NULL rather than 0. That
distinction is the query working — `nullif` exists to make "nobody yet"
different from "nobody activated".

The two EXECUTING tests skip when DATABASE_URL_TEST is unset, like every file in
this directory. The rest read the document only and take no `db` fixture, so
they run everywhere — a runbook edit that drops a load-bearing clause fails on
the laptop it was made on rather than waiting for CI.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_runbook_queries.py -v
"""
import pathlib
import re
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

RUNBOOK = (
    pathlib.Path(__file__).resolve().parents[4] / "docs" / "RUNBOOK_LOOP_METRICS.md"
)


def _sql_blocks() -> list[str]:
    """Every ```sql fenced block in the runbook, in document order."""
    assert RUNBOOK.is_file(), f"runbook not found at {RUNBOOK}"
    return [
        b.strip()
        for b in re.findall(r"```sql\n(.*?)```", RUNBOOK.read_text(encoding="utf-8"), re.S)
    ]


def test_the_runbook_still_has_the_five_queries_this_file_checks():
    """A guard on the guard. If someone removes or renames a block, the
    parametrised test below would quietly check fewer queries and stay green —
    the same 'absence looks like success' shape as the 2026-09-01 no-run trap.
    """
    blocks = _sql_blocks()
    assert len(blocks) == 5, (
        f"expected 5 SQL blocks in {RUNBOOK.name}, found {len(blocks)}. If a query "
        f"was added, extend this file; if one was removed, say so here."
    )
    assert "Activation" in blocks[0]
    assert "Memory trust" in blocks[1]
    assert "Sameness A" in blocks[2]
    assert "Sameness B" in blocks[3]
    assert "Council v2 trigger" in blocks[4]


@pytest.mark.parametrize(
    "index,label",
    [
        (0, "activation"),
        (1, "memory_trust"),
        (2, "sameness_lexical"),
        (3, "sameness_structural"),
        (4, "council_trigger"),
    ],
)
async def test_the_runbook_query_is_valid_against_the_live_schema(db, index, label):
    """Execute it. Every table and column it names must exist.

    :cohort_start is the activation query's only bind parameter; it is supplied
    here so the query runs unmodified. A reader pastes a real date in its place.

    A TZ-AWARE DATETIME, NEVER THE STRING (TD-76, third occurrence). The first
    version of this file bound '2026-01-01' and asyncpg answered "expected
    datetime.date or datetime.datetime instance, got 'str'" — it does not coerce
    for a timestamptz parameter, and the string that reads fine in psql is a
    LITERAL there rather than a bound parameter. Aware, not naive: a naive value
    is read in the server's timezone, which would shift the cohort floor by the
    server's offset and move the gate without failing.
    """
    sql = _sql_blocks()[index]
    params = (
        {"cohort_start": datetime(2026, 1, 1, tzinfo=timezone.utc)}
        if ":cohort_start" in sql else {}
    )

    result = await db.execute(text(sql), params)
    rows = result.all()

    # SHAPE, NOT VALUES — and in both cases the shape against an empty database is
    # ONE ROW, which is the part the first version of this file got wrong.
    #
    # An aggregate with no GROUP BY returns a row over zero input rows, and so
    # does GROUP BY ROLLUP: the grand-total row exists whether or not anything
    # was grouped into it. "No verdicts" is therefore a row saying 0, not an
    # absent row, and asserting [] here asserted that the query had no grand
    # total — which would have been a defect in the query, not in the database.
    if label == "activation":
        assert len(rows) == 1
        assert result.keys() == ["cohort_size", "activated", "pct"]
        assert rows[0].cohort_size == 0
        assert rows[0].activated == 0
        # NULL, not 0: "nobody has signed up yet" is a different fact from
        # "nobody activated", and nullif is what keeps them apart.
        assert rows[0].pct is None
    elif label == "sameness_lexical":
        # ZERO ROWS here, and that is the correct shape rather than an oversight.
        # Unlike the two above, this query has a plain GROUP BY and no ROLLUP, so
        # over an empty table there is nothing to group and no grand total is
        # defined. "No pairs" is an empty result, not a row of zeroes.
        assert result.keys() == ["kind", "band", "pairs", "mean_jaccard", "p90_jaccard"]
        assert rows == []
    elif label == "council_trigger":
        # ONE ROW over an empty table: the outer aggregate has no GROUP BY, so
        # "no councils yet" is a row of zeroes. The trigger column must be there
        # by name — the threshold (>= 10, founder ruling 2026-09-24) reads it.
        assert result.keys() == [
            "users", "users_with_more_than_one", "users_with_more_than_one_non_admin",
            "cases", "cases_reused",
        ]
        assert len(rows) == 1
        assert tuple(rows[0]) == (0, 0, 0, 0, 0)
    elif label == "sameness_structural":
        assert result.keys() == [
            "band", "replies", "pct_end_question", "mean_words", "sd_words",
        ]
        assert rows == []
    else:
        assert result.keys() == ["surface", "verdicts", "wrong", "pct_wrong"]
        assert len(rows) == 1, "ROLLUP returns its grand-total row even over zero input"
        total = rows[0]
        # COALESCE labels the ROLLUP row; a real surface is never NULL, because
        # all three union branches are literals.
        assert total.surface == "ALL SURFACES"
        assert (total.verdicts, total.wrong) == (0, 0)
        # And the percentage stays NULL. Coalescing it to 0 would report a
        # PASSING memory-trust gate against an empty table, which is the one
        # wrong answer this column can give.
        assert total.pct_wrong is None


async def test_the_activation_query_reads_user_messages_not_message_count():
    """The runbook explains WHY it counts message rows, and this pins the choice.

    conversations.message_count increments by TWO per exchange and the opening
    invocation lands in it too, so "at least 2 user messages" is not
    `message_count >= 4` in every case. An edit that swapped the row count for
    the column would look tidier, change the threshold silently, and move the
    gate.
    """
    sql = _sql_blocks()[0]
    assert "role = 'user'" in sql
    assert "message_count" not in sql


async def test_the_activation_query_excludes_users_inside_their_own_window():
    """Without this clause every recent signup counts as a failure and the
    percentage falls as the product grows — a metric that gets worse when things
    get better is worse than no metric."""
    sql = _sql_blocks()[0]
    assert "now() - interval '72 hours'" in sql


async def test_the_memory_trust_query_covers_all_three_ring_true_surfaces():
    """Γ-5's finding, pinned where it would regress.

    Ring-true is one speech act on three surfaces. The gate was being read off
    insights alone; if a future edit drops a branch of this union the number goes
    UP and looks like an improvement.
    """
    sql = _sql_blocks()[1]
    for table in ("insights", "mirrors", "self_comparisons"):
        assert f"FROM {table}" in sql, f"{table} is missing from the memory-trust union"


async def test_the_memory_trust_percentage_is_not_coalesced_to_zero():
    """THE ONE WRONG ANSWER THIS COLUMN CAN GIVE.

    `pct_wrong` is NULL when nobody has answered. Wrapping it in COALESCE(...,0)
    is the obvious tidy-up — the grand-total row reads `NULL` against an empty
    table and looks unfinished — and it would report a PASSING memory-trust gate
    (<2% wrong) on a table with no verdicts in it at all.

    The surface LABEL is coalesced, deliberately, and that is a different thing:
    it names the ROLLUP row rather than inventing a measurement.
    """
    sql = _sql_blocks()[1]
    assert "nullif(count(*), 0)" in sql, "pct_wrong must stay NULL on a zero denominator"
    assert "COALESCE(v.surface" in sql, "the ROLLUP grand-total row should be labelled"
    # The only COALESCE in the query is the label one.
    assert sql.upper().count("COALESCE") == 1


async def test_the_activation_query_keeps_its_null_percentage_too():
    """Same rule, same reason, on the other gate: an empty cohort must report
    NULL rather than 0%, or a product with no users reads as a total activation
    failure instead of as a product with no users."""
    sql = _sql_blocks()[0]
    assert "nullif(count(*), 0)" in sql
    assert "COALESCE" not in sql.upper()


async def test_the_sameness_query_keeps_its_control_arm():
    """WITHOUT THE CONTROL THE NUMBER MEANS NOTHING, and it would still look fine.

    Two replies by the same persona always share vocabulary — that is the
    persona, not convergence. The control arm (same voice, DIFFERENT
    conversation) is the floor the within-conversation bands are read against;
    the runbook's baseline is stated as a ratio to it for exactly that reason.

    Delete the UNION ALL and the query still runs, still returns three tidy
    bands, and silently becomes a measurement of how a persona writes rather than
    of whether it repeats itself.
    """
    sql = _sql_blocks()[2]
    assert "UNION ALL" in sql, "the control arm is gone"
    assert "CONTROL: same voice, other conversation" in sql
    assert "b.conversation_id <> a.conversation_id" in sql, (
        "the control must compare ACROSS conversations, or it is not a control"
    )


@pytest.mark.parametrize("index", [2, 3])
async def test_the_sameness_queries_measure_the_persona_and_not_the_app(index):
    """Both sameness queries must exclude the two row kinds that are not a
    persona speaking.

    `persona_override = true` marks the app-voice safety reply — one fixed string
    (`prompt_builder.build_safety_response`). Left in, identical copies of it
    across conversations would register as extreme 'sameness' that no persona
    produced. `message_kind = 'conclusion'` rows are distilled summaries, never
    shown as turns, and are excluded from the LLM context for the same reason.
    """
    sql = _sql_blocks()[index]
    assert "persona_override = false" in sql
    assert "message_kind <> 'conclusion'" in sql


async def test_the_structural_query_still_measures_the_ending():
    """HARD RULE 4 (`prompts/system_base.jinja2`) specifies ~40% of replies ending
    in a question. This query is the only thing that checks the shipped mix
    against the spec, and the ending test is the half that does it."""
    sql = _sql_blocks()[3]
    assert "LIKE '%?'" in sql, "the question-ending measure is gone"
    assert "pct_end_question" in sql


async def test_the_council_trigger_reads_the_non_admin_column():
    """Staff traffic is not signal (founder ruling 2026-09-24): at the ruling, 2 of
    the 3 repeat council users were admin accounts, so an all-accounts threshold
    would have read 3 where the real number was 1. The non-admin column must
    exclude admins, and the runbook must name it as the trigger."""
    sql = _sql_blocks()[4]
    assert "AND NOT is_admin" in sql
    assert "users_with_more_than_one_non_admin >= 10" in sql
