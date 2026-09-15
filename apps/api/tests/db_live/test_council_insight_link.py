"""council_cases.insight_id — the third instance of one pattern (065, Γ-7-lite).

WHY THIS NEEDS A LIVE DATABASE. Everything asserted here is DDL: a column's type
and nullability, a foreign key's ON DELETE action, and a PARTIAL unique index.
The ORM does not enforce any of it on insert — `__table_args__` is metadata — so
a model that declared the index and a migration that forgot it would agree with
each other and disagree with production. That is the ck_weekly_letters_status
precedent, and the same reasoning applies to an index.

THE PATTERN IS ASSERTED AS A PATTERN, which is the part worth reading. Three
rituals can be opened from an insight card; mirrors (031) and counterviews (032)
each recorded which one, and the Council did not. Rather than pin the new index
alone, the test below pins all THREE against one another — because the defect
this closes was not a broken index, it was an inconsistent family, and the way
that recurs is a fourth surface copying two of the three.

Neither sibling index was pinned by any test before this file. Both are now.

Skips when DATABASE_URL_TEST is unset, like every file in this directory.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_council_insight_link.py -v
"""
import uuid

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

# (table, index name). One row per ritual that can be opened from an insight card.
INSIGHT_LINKED = [
    ("mirrors", "uq_mirrors_insight"),
    ("counterviews", "uq_counterviews_insight"),
    ("council_cases", "uq_council_cases_insight"),
]


async def _column(db, table, column):
    return (await db.execute(
        text(
            "SELECT data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )).first()


async def test_the_column_exists_and_is_a_nullable_uuid(db):
    """Nullable is load-bearing, not incidental: direct, chat and mirror councils
    have no insight, and so does every row written before 065."""
    row = await _column(db, "council_cases", "insight_id")

    assert row is not None, "065 did not add council_cases.insight_id"
    assert row.data_type == "uuid"
    assert row.is_nullable == "YES"


@pytest.mark.parametrize("table", ["mirrors", "counterviews", "council_cases"])
async def test_all_three_declare_the_column_the_same_way(db, table):
    """The family, compared. A fourth surface added later should be able to read
    one rule off these three rather than pick a sibling and hope."""
    row = await _column(db, table, "insight_id")

    assert row is not None, f"{table}.insight_id is missing"
    assert (row.data_type, row.is_nullable) == ("uuid", "YES")


@pytest.mark.parametrize("table,index", INSIGHT_LINKED)
async def test_the_partial_unique_index_exists_on_all_three(db, table, index):
    """UNIQUE and PARTIAL, both halves asserted from the index definition.

    Unique without the WHERE clause would be a bug rather than a stricter rule:
    council_cases.insight_id is NULL on most rows, and in Postgres NULLs do not
    collide in a unique index — but the partial predicate is what states the
    intent ("at most one per insight, and rows without one are not constrained")
    instead of relying on that behaviour by accident.
    """
    indexdef = (await db.execute(
        text("SELECT indexdef FROM pg_indexes WHERE tablename = :t AND indexname = :i"),
        {"t": table, "i": index},
    )).scalar_one_or_none()

    assert indexdef is not None, f"{index} is missing from {table}"
    assert "UNIQUE INDEX" in indexdef
    assert "insight_id" in indexdef
    assert "WHERE (insight_id IS NOT NULL)" in indexdef, (
        f"{index} is unique but not partial: {indexdef}"
    )


@pytest.mark.parametrize("table,index", INSIGHT_LINKED)
async def test_the_foreign_key_sets_null_on_delete_on_all_three(db, table, index):
    """SET NULL, never CASCADE. The ritual is the person's own artefact and
    outlives the card that prompted it — deleting an insight must not delete a
    council they convened because of it."""
    action = (await db.execute(
        text(
            "SELECT rc.delete_rule "
            "FROM information_schema.referential_constraints rc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = rc.constraint_name "
            "WHERE kcu.table_name = :t AND kcu.column_name = 'insight_id'"
        ),
        {"t": table},
    )).scalar_one_or_none()

    assert action == "SET NULL", f"{table}.insight_id deletes with {action!r}"


# ── Behaviour, not just shape ────────────────────────────────────────────────

async def _user(db):
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :e)"),
        {"id": uid, "e": f"{uid}@example.test"},
    )
    return uid


async def _insight(db, user_id):
    iid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO insights (id, user_id, content, insight_type) "
            "VALUES (:id, :u, :c, 'dilemma')"
        ),
        {"id": iid, "u": user_id, "c": "Whether to take the job."},
    )
    return iid


async def _case(db, user_id, *, insight_id=None, source="direct"):
    cid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO council_cases (id, user_id, source, insight_id, status, session_count) "
            "VALUES (:id, :u, :s, :i, 'open', 1)"
        ),
        {"id": cid, "u": user_id, "s": source, "i": insight_id},
    )
    return cid


async def test_a_direct_council_stores_null(db):
    """The common case, and the reason the column is nullable."""
    uid = await _user(db)
    cid = await _case(db, uid)

    stored = (await db.execute(
        text("SELECT insight_id FROM council_cases WHERE id = :id"), {"id": cid},
    )).scalar_one()

    assert stored is None


async def test_many_councils_may_have_no_insight(db):
    """The partial predicate, exercised. Without WHERE ... IS NOT NULL this would
    still pass in Postgres — NULLs do not collide — which is exactly why the index
    definition is asserted above as well as the behaviour here."""
    uid = await _user(db)
    for _ in range(3):
        await _case(db, uid)

    count = (await db.execute(
        text("SELECT count(*) FROM council_cases WHERE user_id = :u"), {"u": uid},
    )).scalar_one()

    assert count == 3


async def test_one_council_per_insight(db):
    """The race guard. There is no app-level dedup on this path, so the index is
    the only thing standing between a double tap and two councils claiming the
    same card.

    ASSERTED BY CONSTRAINT NAME, which is the convention test_job_run.py and
    test_trajectory_snapshots.py already use for exactly this shape, and it is the
    right one for a reason worth writing down. The first version of this test
    asserted `isinstance(exc.value.orig, asyncpg.UniqueViolationError)` and failed
    in CI while the constraint worked perfectly: `.orig` is NOT asyncpg's
    exception. SQLAlchemy's asyncpg dialect wraps it in its own DBAPI shim, so the
    real chain is

        sqlalchemy.exc.IntegrityError
          .orig           -> sqlalchemy.dialects.postgresql.asyncpg.IntegrityError
          .orig.__cause__ -> asyncpg.exceptions.UniqueViolationError

    Pinning `.orig.__cause__` would work today and would pin SQLAlchemy's internal
    wrapping — the same brittleness one level along. The constraint NAME is the
    thing this test is actually about, it survives a driver change, and it names
    WHICH index fired rather than merely that something collided.

    IntegrityError rather than bare Exception, though: it is verified, and it
    distinguishes a constraint violation from a connection error that would
    otherwise satisfy the same assertion.
    """
    from sqlalchemy.exc import IntegrityError

    uid = await _user(db)
    iid = await _insight(db, uid)
    await _case(db, uid, insight_id=iid, source="nudge")

    with pytest.raises(IntegrityError) as exc:
        await _case(db, uid, insight_id=iid, source="nudge")

    assert "uq_council_cases_insight" in str(exc.value), (
        f"a constraint fired, but not the one under test: {exc.value}"
    )


async def test_deleting_the_insight_keeps_the_council(db):
    """SET NULL in practice. The council survives; only the link goes."""
    uid = await _user(db)
    iid = await _insight(db, uid)
    cid = await _case(db, uid, insight_id=iid, source="nudge")

    await db.execute(text("DELETE FROM insights WHERE id = :id"), {"id": iid})

    row = (await db.execute(
        text("SELECT insight_id FROM council_cases WHERE id = :id"), {"id": cid},
    )).first()

    assert row is not None, "the council was deleted with its insight"
    assert row.insight_id is None
