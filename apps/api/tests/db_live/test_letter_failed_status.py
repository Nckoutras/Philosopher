"""weekly_letters.status accepts 'failed', and the model says what the DB says.

Migration 058. Both letter generators write status='failed' when the model's
reply and its one retry are both unparseable JSON (arq_worker.py:1712 weekly,
:2096 monthly). The CHECK created by 022 permitted only
('generated', 'empty', 'suppressed'), so that INSERT raised CheckViolation, the
logger.error on the next line never ran, and the failure surfaced as a generic
task error. The comment above that write says "silence is what cost us four days
last time"; it had been silent since it shipped.

WHY THIS NEEDS A LIVE DATABASE, AND WHY IT NEEDS **TWO** ASSERTIONS.

A CHECK constraint is enforced by Postgres and by nothing else, so the insert can
only be proven against a real server — a mocked session accepts anything. Every
layer that could have caught this defect was mocked, which is exactly how it
survived: tests/routers/test_weekly_letters.py:204 has pinned
"status != 'failed'" in the list endpoint's COMPILED SQL all along, against a
value the schema made impossible, and passed the whole time because it never
executed that SQL.

But the insert alone proves only the MIGRATION. A SQLAlchemy CheckConstraint in
__table_args__ is DDL metadata — the ORM does not evaluate it on insert — so with
058 applied and models/__init__.py left unchanged, the insert would still succeed
and the model/migration disagreement would go unnoticed. The second test compares
the live constraint against the model's declaration so that drift fails here.

Sets of literals, not raw strings: Postgres rewrites CHECK text when it stores it
(`(status)::text = ANY ((ARRAY['generated'::character varying, ...])::text[])`),
so the two sides never match textually and asserting on the text would pin
Postgres's rendering rather than the product's rule.
"""
import re
import uuid

import pytest
from sqlalchemy import text

from models import WeeklyLetter

CONSTRAINT = "ck_weekly_letters_status"

# The vocabulary after 058. Written out rather than derived from either side —
# an assertion that computed its own expectation from the thing under test could
# not fail. This is the third, independent statement of the rule.
EXPECTED_STATUSES = {"generated", "empty", "suppressed", "failed"}


def _literals(sql_text: str) -> set[str]:
    """Every single-quoted literal in a CHECK expression, however it is rendered."""
    return set(re.findall(r"'([^']*)'", sql_text))


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


# ── 1. The insert the product has been attempting all along ─────────────────

@pytest.mark.asyncio
async def test_a_letter_row_can_be_written_with_status_failed(db):
    """THE ASSERTION NO MOCK CAN MAKE. Before 058 this commit raised
    CheckViolation; the generators have been attempting it on every double parse
    failure since the letter engine shipped."""
    user_id = await _make_user(db)
    letter_id = str(uuid.uuid4())

    await db.execute(
        text(
            "INSERT INTO weekly_letters "
            "  (id, user_id, period_start, period_end, status, kind) "
            "VALUES (:id, :uid, now() - interval '7 days', now(), 'failed', 'weekly')"
        ),
        {"id": letter_id, "uid": user_id},
    )
    await db.flush()

    row = (await db.execute(
        text("SELECT status FROM weekly_letters WHERE id = :id"), {"id": letter_id},
    )).scalar_one()
    assert row == "failed"


@pytest.mark.asyncio
async def test_the_other_three_statuses_still_write(db):
    """Widening must not have narrowed anything. All four are legal after 058."""
    user_id = await _make_user(db)
    for i, status in enumerate(sorted(EXPECTED_STATUSES)):
        await db.execute(
            text(
                "INSERT INTO weekly_letters "
                "  (id, user_id, period_start, period_end, status, kind) "
                f"VALUES (:id, :uid, now() - interval '{7 + i} days', now(), :st, 'weekly')"
            ),
            {"id": str(uuid.uuid4()), "uid": user_id, "st": status},
        )
    await db.flush()

    got = (await db.execute(
        text("SELECT count(DISTINCT status) FROM weekly_letters WHERE user_id = :uid"),
        {"uid": user_id},
    )).scalar_one()
    assert got == len(EXPECTED_STATUSES)


@pytest.mark.asyncio
async def test_an_unknown_status_is_still_rejected(db):
    """The constraint still constrains. Without this, "widen the CHECK" and "drop
    the CHECK" would look identical to this file.

    Note tests/routers/test_weekly_letters.py:52 sets a letter's status to
    "delivered" on a MagicMock — harmless there because nothing validates a mock,
    and rejected here, which is the difference this file exists to show."""
    user_id = await _make_user(db)

    with pytest.raises(Exception) as excinfo:
        await db.execute(
            text(
                "INSERT INTO weekly_letters "
                "  (id, user_id, period_start, period_end, status, kind) "
                "VALUES (:id, :uid, now() - interval '7 days', now(), 'delivered', 'weekly')"
            ),
            {"id": str(uuid.uuid4()), "uid": user_id},
        )
        await db.flush()

    assert CONSTRAINT in str(excinfo.value)


# ── 2. The model agrees with the database (AMENDMENT 1) ─────────────────────

@pytest.mark.asyncio
async def test_the_model_constraint_matches_the_live_constraint(db):
    """MODEL/MIGRATION DRIFT GUARD.

    The insert tests above prove the MIGRATION and nothing else: a CheckConstraint
    in __table_args__ is DDL metadata, not an ORM-enforced rule, so 058 applied
    against an unchanged models/__init__.py would leave every test above green
    while the two halves disagreed. That disagreement is precisely the defect
    class 058 fixes, one layer up — so it gets its own assertion.

    Compared as SETS OF LITERALS. Postgres rewrites CHECK text on storage, into
    something like:
        CHECK (((status)::text = ANY ((ARRAY['generated'::character varying, ...])::text[])))
    while the model declares:
        status IN ('generated', 'empty', 'suppressed', 'failed')
    Those never match textually. The rule they encode is the set of permitted
    values, and that is what is compared.
    """
    live_def = (await db.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = :name AND conrelid = 'weekly_letters'::regclass"
        ),
        {"name": CONSTRAINT},
    )).scalar_one()

    model_constraint = next(
        c for c in WeeklyLetter.__table__.constraints
        if getattr(c, "name", None) == CONSTRAINT
    )
    model_def = str(model_constraint.sqltext)

    live_values = _literals(live_def)
    model_values = _literals(model_def)

    assert live_values == EXPECTED_STATUSES, f"live constraint: {live_def}"
    assert model_values == EXPECTED_STATUSES, f"model constraint: {model_def}"
    assert live_values == model_values
