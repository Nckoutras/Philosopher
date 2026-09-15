"""Γ-3 — which thread a bare persona open hands back, against real rows.

WHY THIS NEEDS A LIVE DATABASE. create_or_resume is a query with five predicates
and an ordering, and a mocked session returns whatever it is told — a test built
on one would assert its own fixture. Everything that could actually go wrong here
is SQL: the ordering, the window boundary, and NULL handling on last_message_at.

THE ORDERING IS THE SUBTLE ONE. `ORDER BY last_message_at DESC`, not created_at:
the thread someone last SPOKE in is the one they left open. A thread started
later but abandoned at its opening line must lose to an older one answered
yesterday — and created_at ordering would get that backwards, silently, while
still resuming *a* conversation and looking correct.

Run: cd apps/api && pytest tests/db_live/test_resume_thread.py -v
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from services.conversation_service import RESUME_WINDOW_DAYS, conversation_service

SLUG = "socrates"
OTHER_SLUG = "marcus_aurelius"


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _persona_id(db, slug: str) -> str:
    return (await db.execute(
        text("SELECT id FROM personas WHERE slug = :s"), {"s": slug},
    )).scalar_one()


async def _make_conv(db, user_id, slug, *, message_count, last_message_at,
                     created_at=None, deleted_at=None) -> str:
    """A conversation row. Every NOT NULL column is set from the migration, not
    from whatever the last error demanded (TD-76)."""
    cid = str(uuid.uuid4())
    pid = await _persona_id(db, slug)
    await db.execute(
        text(
            "INSERT INTO conversations "
            "  (id, user_id, persona_id, message_count, last_message_at, created_at, deleted_at) "
            "VALUES (:id, :uid, :pid, :mc, :lma, :ca, :da)"
        ),
        {
            "id": cid, "uid": user_id, "pid": pid, "mc": message_count,
            "lma": last_message_at,
            "ca": created_at or (datetime.now(timezone.utc) - timedelta(days=1)),
            "da": deleted_at,
        },
    )
    return cid


async def _resume(db, user_id):
    return await conversation_service.create_or_resume(
        db=db, user_id=user_id, persona_slug=SLUG, user_plan="pro",
    )


@pytest.mark.asyncio
async def test_it_resumes_a_recent_thread_that_was_spoken_in(db):
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, SLUG,
        message_count=4,
        last_message_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is True
    assert conv.id == cid


@pytest.mark.asyncio
async def test_it_picks_the_thread_last_SPOKEN_in_not_the_newest(db):
    """The ordering assertion. `older` was created first but answered yesterday;
    `newer` was created later and abandoned at its opening. created_at ordering
    would return `newer` — and would look fine, because it still resumes."""
    user_id = await _make_user(db)
    now = datetime.now(timezone.utc)

    older_but_active = await _make_conv(
        db, user_id, SLUG, message_count=6,
        created_at=now - timedelta(days=9),
        last_message_at=now - timedelta(hours=20),
    )
    newer_but_stale = await _make_conv(
        db, user_id, SLUG, message_count=2,
        created_at=now - timedelta(days=2),
        last_message_at=now - timedelta(days=2),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is True
    assert conv.id == older_but_active, (
        f"expected the thread last spoken in ({older_but_active}), got {conv.id} "
        f"({'the newest by created_at' if conv.id == newer_but_stale else 'neither'})"
    )


@pytest.mark.asyncio
async def test_a_thread_older_than_the_window_is_not_resumed(db):
    """15 days. A month-old thread is a different conversation; resuming it reads
    as the room having lost track of time rather than having kept up."""
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, SLUG, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(days=RESUME_WINDOW_DAYS + 1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is False
    assert conv.message_count == 0, "a miss must produce a genuinely fresh thread"


@pytest.mark.asyncio
async def test_a_thread_just_inside_the_window_is_resumed(db):
    """The other side of the same boundary — a window that never matched would
    pass the test above for the wrong reason."""
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, SLUG, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(days=RESUME_WINDOW_DAYS - 1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is True
    assert conv.id == cid


@pytest.mark.asyncio
async def test_a_deleted_thread_is_not_resumed(db):
    """deleted_at is the soft delete the Library relies on. Resuming one would
    resurrect a thread the person removed — the worst possible failure here."""
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, SLUG, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(hours=2),
        deleted_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is False


@pytest.mark.asyncio
async def test_an_untouched_shell_is_not_resumed(db):
    """message_count == 0 is the EXISTING dedup's business, not resume's. A shell
    has nothing to continue, and treating it as a resume would fire
    conversation_resumed for a thread that never started."""
    user_id = await _make_user(db)
    await _make_conv(db, user_id, SLUG, message_count=0, last_message_at=None)
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is False


@pytest.mark.asyncio
async def test_another_personas_thread_is_untouched(db):
    """Opening Socrates must never hand back the Marcus Aurelius thread, however
    recent. The join is on slug; this is what proves it is actually applied."""
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, OTHER_SLUG, message_count=8,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is False
    assert conv.persona_id == await _persona_id(db, SLUG)


@pytest.mark.asyncio
async def test_another_users_thread_is_untouched(db):
    """The user_id predicate, asserted rather than assumed — this endpoint hands
    back a whole conversation, so a missing owner filter would be a disclosure
    bug, not a routing one."""
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _make_conv(
        db, theirs, SLUG, message_count=9,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    await db.flush()

    conv, resumed = await _resume(db, mine)
    assert resumed is False
    assert conv.user_id == mine


@pytest.mark.asyncio
async def test_a_resumed_thread_keeps_its_id_and_therefore_its_history(db):
    """The whole mechanism in one assertion: resuming returns the SAME
    conversation_id, which is why the send path's history query loads the full
    thread with no cross-conversation injection anywhere."""
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, SLUG, message_count=3,
        last_message_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    await db.execute(
        text(
            "INSERT INTO messages (id, conversation_id, user_id, role, content) "
            "VALUES (:id, :cid, :uid, 'user', 'I am still turning this over.')"
        ),
        {"id": str(uuid.uuid4()), "cid": cid, "uid": user_id},
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id)
    assert resumed is True
    count = (await db.execute(
        text("SELECT count(*) FROM messages WHERE conversation_id = :cid"), {"cid": conv.id},
    )).scalar_one()
    assert count == 1, "the resumed thread must still own its messages"
