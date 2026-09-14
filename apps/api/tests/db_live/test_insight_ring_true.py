"""insights.ring_true accepts only the shipped vocabulary, and NULL survives the spine.

Migration 063. Two things need a real Postgres and can be proven nowhere else:

1. A CHECK constraint is enforced by the server and by nothing else. A mocked
   session accepts any string, so the only place the vocabulary is actually a
   vocabulary is here. This mirrors test_letter_failed_status.py, including its
   second assertion — a SQLAlchemy CheckConstraint in __table_args__ is DDL
   metadata that the ORM does not evaluate on insert, so with 063 applied and the
   model left unchanged the insert would still succeed and the drift would go
   unnoticed.

2. IS DISTINCT FROM vs != is three-valued logic, which only Postgres performs.
   The unit test in tests/workers/ pins the compiled SQL; this one runs it against
   rows and proves what the spine actually returns. If the predicate were ever
   "simplified" to `!=`, test_an_unanswered_insight_stays_in_the_spine is what
   would catch the letters quietly losing almost every insight they anchor on.

Run: cd apps/api && pytest tests/db_live/test_insight_ring_true.py -v
"""
import re
import uuid

import pytest
from sqlalchemy import select, text

from models import Insight

CONSTRAINT = "ck_insights_ring_true"

# The vocabulary, written out rather than derived from either side — an assertion
# that computed its expectation from the thing under test could not fail. This is
# the third, independent statement of the rule (migration, model, here).
EXPECTED_VERDICTS = {"yes", "partly", "no"}


def _literals(sql_text: str) -> set[str]:
    return set(re.findall(r"'([^']*)'", sql_text))


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _make_insight(db, user_id: str, ring_true=None) -> str:
    iid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO insights (id, user_id, content, insight_type, ring_true) "
            "VALUES (:id, :uid, 'You keep returning to the same decision.', "
            "        'pattern', :rt)"
        ),
        {"id": iid, "uid": user_id, "rt": ring_true},
    )
    return iid


# ── 1. The vocabulary is real ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", sorted(EXPECTED_VERDICTS))
async def test_each_shipped_verdict_writes(db, verdict):
    user_id = await _make_user(db)
    iid = await _make_insight(db, user_id, verdict)
    await db.flush()

    row = (await db.execute(
        text("SELECT ring_true FROM insights WHERE id = :id"), {"id": iid},
    )).scalar_one()
    assert row == verdict


@pytest.mark.asyncio
async def test_null_is_allowed_and_is_the_default(db):
    """NULL means "not answered" and is the only honest state for every row that
    predates 063. A default would have invented an opinion for them."""
    user_id = await _make_user(db)
    iid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO insights (id, user_id, content) "
            "VALUES (:id, :uid, 'A claim about you.')"
        ),
        {"id": iid, "uid": user_id},
    )
    await db.flush()

    row = (await db.execute(
        text("SELECT ring_true FROM insights WHERE id = :id"), {"id": iid},
    )).scalar_one()
    assert row is None


@pytest.mark.asyncio
async def test_an_off_vocabulary_verdict_is_refused_by_postgres(db):
    """THE ASSERTION NO MOCK CAN MAKE. self_comparisons.ring_true has no CHECK and
    accepts any ten characters; this is what stops insights going the same way."""
    user_id = await _make_user(db)
    with pytest.raises(Exception) as excinfo:
        await _make_insight(db, user_id, "maybe")
        await db.flush()
    assert CONSTRAINT in str(excinfo.value)


# ── 2. The model says what the DB says ───────────────────────────────────────

@pytest.mark.asyncio
async def test_the_live_constraint_matches_the_model_declaration(db):
    """Sets of literals, not raw strings: Postgres rewrites CHECK text when it
    stores it, so the two sides never match textually and asserting on the text
    would pin Postgres's rendering rather than the product's rule."""
    live = (await db.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = :name"
        ),
        {"name": CONSTRAINT},
    )).scalar_one_or_none()
    assert live is not None, f"{CONSTRAINT} is missing from the live schema"
    assert _literals(live) == EXPECTED_VERDICTS

    declared = next(
        c for c in Insight.__table__.constraints if c.name == CONSTRAINT
    )
    assert _literals(str(declared.sqltext)) == EXPECTED_VERDICTS


# ── 3. The three-valued logic the spine depends on ───────────────────────────

@pytest.mark.asyncio
async def test_an_unanswered_insight_stays_in_the_spine(db):
    """The NULL trap, proven against rows rather than against compiled SQL.

    `ring_true != 'no'` is NULL for an unanswered insight and a WHERE drops it.
    Nearly every insight is unanswered, so that spelling would empty the letter's
    spine almost completely — while both letters kept generating and reading
    plausibly. This is the test that would go red.
    """
    from workers.arq_worker import _insight_spine_conditions

    user_id = await _make_user(db)
    unanswered = await _make_insight(db, user_id, None)
    affirmed = await _make_insight(db, user_id, "yes")
    partly = await _make_insight(db, user_id, "partly")
    rejected = await _make_insight(db, user_id, "no")
    await db.flush()

    rows = (await db.execute(
        select(Insight.id).where(
            Insight.user_id == user_id,
            Insight.ring_true.is_distinct_from("no"),
        )
    )).scalars().all()

    assert unanswered in rows, "an unanswered insight must stay in the spine"
    assert affirmed in rows
    assert partly in rows
    assert rejected not in rows, "a rejected claim must not be re-anchored next week"

    # And the shared predicate itself agrees, run end to end.
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    spine = (await db.execute(
        select(Insight.id).where(
            *_insight_spine_conditions(user_id, now - timedelta(days=1), now + timedelta(days=1))
        )
    )).scalars().all()
    assert rejected not in spine
    assert unanswered in spine


# ── 4. The third table finally enforces it too (064) ─────────────────────────

SC_CONSTRAINT = "ck_self_comparisons_ring_true"


async def _make_self_comparison(db, user_id: str, ring_true=None) -> str:
    sid = str(uuid.uuid4())
    await db.execute(
        text(
            # `prompt` is NOT NULL (021). Omitting it would make every assertion
            # below fail on a NOT NULL violation instead of on the constraint under
            # test — TD-76: a fixture that is present is not a fixture that is
            # correct. Columns checked against the migration, not against whatever
            # the last error happened to demand.
            "INSERT INTO self_comparisons (id, user_id, prompt, status, ring_true) "
            "VALUES (:id, :uid, 'Then and now.', 'ready', :rt)"
        ),
        {"id": sid, "uid": user_id, "rt": ring_true},
    )
    return sid


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", sorted(EXPECTED_VERDICTS))
async def test_self_comparisons_accepts_each_shipped_verdict(db, verdict):
    user_id = await _make_user(db)
    sid = await _make_self_comparison(db, user_id, verdict)
    await db.flush()

    row = (await db.execute(
        text("SELECT ring_true FROM self_comparisons WHERE id = :id"), {"id": sid},
    )).scalar_one()
    assert row == verdict


@pytest.mark.asyncio
async def test_self_comparisons_refuses_an_off_vocabulary_verdict(db):
    """THE GAP 064 CLOSES. This column was a bare VARCHAR(10) from 021 until now —
    the one surface of the three where a verdict outside the vocabulary could
    actually land. The founder counted the existing off-vocabulary rows before
    the constraint was written (zero), which is why 064 could validate rather
    than arrive NOT VALID."""
    user_id = await _make_user(db)
    with pytest.raises(Exception) as excinfo:
        await _make_self_comparison(db, user_id, "maybe")
        await db.flush()
    assert SC_CONSTRAINT in str(excinfo.value)


@pytest.mark.asyncio
async def test_self_comparisons_null_is_still_allowed(db):
    """Adding a CHECK must not have made the column required. NULL is 'not
    answered' here exactly as it is on insights and mirrors."""
    user_id = await _make_user(db)
    sid = await _make_self_comparison(db, user_id, None)
    await db.flush()

    row = (await db.execute(
        text("SELECT ring_true FROM self_comparisons WHERE id = :id"), {"id": sid},
    )).scalar_one()
    assert row is None


@pytest.mark.asyncio
async def test_all_three_tables_enforce_the_same_vocabulary(db):
    """The point of 063 + 064 in one sentence: one speech act, one contract.

    Compares the LIVE constraint on all three tables. Sets of literals rather than
    raw text, because Postgres rewrites CHECK expressions when it stores them and
    asserting on the text would pin its rendering rather than the product's rule.
    """
    from models import Mirror, SelfComparison

    expected = {
        "ck_mirrors_ring_true": Mirror,
        "ck_insights_ring_true": Insight,
        "ck_self_comparisons_ring_true": SelfComparison,
    }
    for name, model in expected.items():
        live = (await db.execute(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
            {"n": name},
        )).scalar_one_or_none()
        assert live is not None, f"{name} is missing from the live schema"
        assert _literals(live) == EXPECTED_VERDICTS, f"{name} enforces a different vocabulary"

        declared = next(c for c in model.__table__.constraints if c.name == name)
        assert _literals(str(declared.sqltext)) == EXPECTED_VERDICTS, (
            f"{model.__name__} declares a different vocabulary than the live {name}"
        )
