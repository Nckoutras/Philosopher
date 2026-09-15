"""Γ-4a — the prior-letters QUERY, against real Postgres.

WHY THIS NEEDS A LIVE DATABASE. The claim under test is that the weekly letter's
continuity fetch is no longer scoped to one voice — and the whole of that claim
lives in a WHERE clause. A mocked AsyncSession returns whatever the test author
invented, so "letters from three voices came back" would be a statement about the
fixture and not about the query. The result set IS the behaviour
(tests/db_live/conftest.py, and the same reasoning as
test_memory_recall_and_cascades).

IT EXECUTES _prior_letters_stmt, IT DOES NOT REBUILD IT. The statement was
extracted from the task body for exactly this reason, following the
_insight_spine_conditions precedent: a test that hand-assembled an equivalent
SELECT would pin its own copy, and would stay green while the shipped query drifted
underneath it. Everything below runs the object the letter generator runs.

THE RENDERER IS ELSEWHERE — tests/workers/test_letter_continuity.py. Attribution,
the bare/to= split, oldest-first ordering and the missing-name rule are pure
string work over rows and need no server.

Skips when DATABASE_URL_TEST is unset (every local run without Docker); CI's
db-tests job runs it.

Run: cd apps/api && DATABASE_URL_TEST=... python -m pytest tests/db_live/test_letter_continuity.py -v
"""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from workers.arq_worker import PRIOR_LETTERS_MAX_CARRIED, _prior_letters_stmt

pytestmark = pytest.mark.asyncio

# The letter being generated. Everything seeded below is dated relative to this,
# so "strictly before this window" is a property of the data rather than of the
# clock the suite happens to run on.
NOW = datetime(2026, 9, 27, 18, 0, tzinfo=timezone.utc)


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _persona_ids(db, how_many: int) -> list[tuple[str, str]]:
    """(id, name) for personas the MIGRATION CHAIN inserts, discovered at runtime.

    Not hardcoded slugs, and this is the trap test_resume_thread.py documents:
    only 006 and 027 INSERT persona rows. socrates and marcus_aurelius appear in
    migrations solely inside UPDATE statements, so they do not exist here — the
    rest of the roster comes from db/seed.py, which this conftest never runs.

    str() on the id is load-bearing: asyncpg returns a UUID column as uuid.UUID
    while the ORM maps these with as_uuid=False, so an uncoerced comparison reads
    False on identical values.
    """
    rows = (await db.execute(
        text("SELECT id, name FROM personas ORDER BY slug")
    )).all()
    assert len(rows) >= how_many, (
        f"this test needs {how_many} personas from the migration chain; "
        f"it provided {len(rows)}"
    )
    return [(str(r[0]), r[1]) for r in rows[:how_many]]


async def _letter(db, user_id, *, weeks_ago, voice_id, status="generated",
                  kind="weekly", title="A letter"):
    """One weekly_letters row, every NOT NULL column set from the migration.

    TD-76: period_start/period_end are bound as datetime OBJECTS, never ISO
    strings — asyncpg rejects a string for timestamptz, and the failure reads as
    a driver error rather than as the fixture defect it is.
    """
    lid = str(uuid.uuid4())
    start = NOW - timedelta(weeks=weeks_ago)
    await db.execute(
        text(
            "INSERT INTO weekly_letters "
            "  (id, user_id, voice_persona_id, period_start, period_end, status, kind, payload) "
            "VALUES (:id, :uid, :pid, :ps, :pe, :st, :kd, CAST(:pl AS jsonb))"
        ),
        {
            "id": lid, "uid": user_id, "pid": voice_id,
            "ps": start, "pe": start + timedelta(days=6),
            "st": status, "kd": kind,
            "pl": json.dumps({"title": title, "pull_quote": "A line."}),
        },
    )
    return lid


async def _carried(db, user_id):
    """The rows the letter generator would carry, via the shipped statement."""
    return (await db.execute(_prior_letters_stmt(user_id, NOW))).all()


# ── The ruling's core claim ──────────────────────────────────────────────────

async def test_the_fetch_crosses_voices(db):
    """THE POINT OF Γ-4a, asserted against the server.

    Three letters in three different voices, none of them the voice now writing.
    Before this change the equivalent query returned ZERO rows for a reader who
    had rotated away — the letter began again from nothing every week and no code
    path could tell. All three must come back, each with its persona's name.
    """
    uid = await _make_user(db)
    personas = await _persona_ids(db, 3)
    for i, (pid, _) in enumerate(personas):
        await _letter(db, uid, weeks_ago=i + 1, voice_id=pid, title=f"L{i}")

    rows = await _carried(db, uid)

    assert len(rows) == 3
    assert {name for _, name in rows} == {name for _, name in personas}


async def test_a_reader_who_switched_voice_still_has_a_correspondence(db):
    """The regression this PR exists to fix, stated as its own case.

    Every prior letter is in one voice; the letter now being written is in
    another. The old voice-scoped query returned nothing here. This is the
    difference between "six weeks of thread" and "hello, stranger".
    """
    uid = await _make_user(db)
    (old_id, old_name), (_new_id, _) = await _persona_ids(db, 2)
    for i in range(3):
        await _letter(db, uid, weeks_ago=i + 1, voice_id=old_id)

    rows = await _carried(db, uid)

    assert len(rows) == 3
    assert all(name == old_name for _, name in rows)


# ── Cap and ordering ─────────────────────────────────────────────────────────

async def test_the_cap_holds_at_six(db):
    """Nine eligible letters, six carried — and the six are the NEWEST six.

    Both halves matter. A cap that kept the oldest six would also return six and
    would be silently, completely wrong about what the correspondence is.
    """
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    for i in range(1, 10):
        await _letter(db, uid, weeks_ago=i, voice_id=pid, title=f"W{i:02d}")

    rows = await _carried(db, uid)

    assert len(rows) == PRIOR_LETTERS_MAX_CARRIED == 6
    titles = [letter.payload["title"] for letter, _ in rows]
    assert titles == ["W01", "W02", "W03", "W04", "W05", "W06"]


async def test_rows_come_back_newest_first(db):
    """The renderer reverses this, so the query's direction is load-bearing at a
    distance: get it wrong and the prompt reads the correspondence backwards with
    no error anywhere."""
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    for i in (1, 2, 3):
        await _letter(db, uid, weeks_ago=i, voice_id=pid, title=f"W{i}")

    rows = await _carried(db, uid)

    assert [letter.payload["title"] for letter, _ in rows] == ["W1", "W2", "W3"]


# ── The four surviving filters ───────────────────────────────────────────────

async def test_another_readers_letters_are_never_carried(db):
    """user_id. The one filter whose failure would be a privacy incident rather
    than a quality one — another person's letter in this person's prompt."""
    uid, other = await _make_user(db), await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    await _letter(db, other, weeks_ago=1, voice_id=pid, title="NOT HERS")
    await _letter(db, uid, weeks_ago=1, voice_id=pid, title="hers")

    titles = [letter.payload["title"] for letter, _ in await _carried(db, uid)]

    assert titles == ["hers"]


@pytest.mark.parametrize("status", ["empty", "suppressed", "failed"])
async def test_only_generated_letters_are_carried(db, status):
    """A quiet week, a safety-gated week and a lost letter all have no payload to
    render — carrying them would emit a header of two empty strings."""
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    await _letter(db, uid, weeks_ago=1, voice_id=pid, status=status)

    assert await _carried(db, uid) == []


async def test_season_letters_never_leak_into_weekly_continuity(db):
    """kind is CADENCE, not ownership (A14): a season write-back answers a
    month's reckoning and does not belong in a letter about seven days."""
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    await _letter(db, uid, weeks_ago=1, voice_id=pid, kind="monthly", title="season")
    await _letter(db, uid, weeks_ago=2, voice_id=pid, kind="weekly", title="week")

    titles = [letter.payload["title"] for letter, _ in await _carried(db, uid)]

    assert titles == ["week"]


async def test_the_letter_being_written_cannot_quote_itself(db):
    """period_start STRICTLY before the window. A catch-up or a re-run generates
    for a period that already has a row; without the strict comparison the letter
    would carry itself forward as its own prior."""
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    await _letter(db, uid, weeks_ago=0, voice_id=pid, title="ITSELF")
    await _letter(db, uid, weeks_ago=1, voice_id=pid, title="last week")

    titles = [letter.payload["title"] for letter, _ in await _carried(db, uid)]

    assert titles == ["last week"]


# ── The outer join ───────────────────────────────────────────────────────────

async def test_a_letter_with_no_voice_is_still_returned_with_a_null_name(db):
    """OUTER join, not inner, and the distinction is the whole of Decision 2.

    voice_persona_id is nullable. An inner join would drop such a letter from the
    correspondence entirely — silently shortening the thread, which is the defect
    this change exists to fix. It comes back with name=None, and the renderer
    turns that into a bare header.
    """
    uid = await _make_user(db)
    await _letter(db, uid, weeks_ago=1, voice_id=None, title="orphaned")

    rows = await _carried(db, uid)

    assert len(rows) == 1
    letter, name = rows[0]
    assert name is None
    assert letter.payload["title"] == "orphaned"


# ── The A12 backstop still has something to do ───────────────────────────────

async def test_a_write_back_on_an_old_letter_falls_outside_the_cap(db):
    """WHY THE A12 FETCH SURVIVES Γ-4a rather than being deleted as redundant.

    Nothing gates a write-back by letter age: WriteBackPanel renders on every
    letter detail page and PATCH /weekly-letters/{id}/write-back checks ownership
    and plan only. So a reader can answer a three-month-old letter today. That
    row's write_back_at is recent, but the letter itself sits outside the newest
    six — proven here — so only the recency-scoped A12 query reaches it.

    If this test ever fails because the old letter IS carried, the A12 fetch has
    become genuinely redundant and should be removed in a deliberate PR, not left
    running. That is the review this assertion is really pinning.
    """
    uid = await _make_user(db)
    (pid, _), = await _persona_ids(db, 1)
    old = await _letter(db, uid, weeks_ago=12, voice_id=pid, title="OLD")
    await db.execute(
        text("UPDATE weekly_letters SET write_back_text = :t, write_back_at = :a "
             "WHERE id = :id"),
        {"t": "I came back to this.", "a": NOW - timedelta(days=2), "id": old},
    )
    for i in range(1, 8):
        await _letter(db, uid, weeks_ago=i, voice_id=pid, title=f"W{i}")

    carried_ids = {str(letter.id) for letter, _ in await _carried(db, uid)}

    assert old not in carried_ids
