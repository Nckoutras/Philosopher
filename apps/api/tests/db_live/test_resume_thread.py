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
import pytest_asyncio
from sqlalchemy import text

from personas import get_persona, is_persona_accessible
from services.conversation_service import RESUME_WINDOW_DAYS, conversation_service


@pytest_asyncio.fixture
async def two_personas(db):
    """(slug, other_slug) for two personas that exist in BOTH the table and the
    registry, discovered at runtime.

    WHY NOT HARDCODED slugS — this is what made the first version of this file
    fail nine times with one error. The migration chain INSERTs only six
    personas (006, 027). `socrates` and `marcus_aurelius` appear in migrations
    ONLY inside UPDATE statements (005 and 026 repoint portrait_url), so they
    never exist here: the rest of the roster comes from db/seed.py, which the
    db_live conftest does not run. A `scalar_one()` on a slug that is seeded by
    app code rather than by a migration is a NoResultFound waiting to happen.

    Both halves are required. The DB row satisfies the FK; the registry entry is
    what create_or_resume looks up before it queries anything, and a slug in one
    but not the other fails in a different place for a different reason.
    """
    rows = (await db.execute(text("SELECT id, slug FROM personas ORDER BY slug"))).all()
    usable = [
        (str(r[0]), r[1])
        for r in rows
        if get_persona(r[1]) is not None
        and is_persona_accessible(get_persona(r[1]), "pro")
    ]
    assert len(usable) >= 2, (
        "this file needs two personas present in both the table and the registry; "
        f"the migration chain provided {[r[1] for r in rows]}"
    )
    return usable[0][1], usable[1][1]


async def _make_user(db) -> str:
    uid = str(uuid.uuid4())
    await db.execute(
        text("INSERT INTO users (id, email) VALUES (:id, :email)"),
        {"id": uid, "email": f"{uid}@example.test"},
    )
    return uid


async def _persona_id(db, slug: str) -> str:
    """scalar_one is correct HERE because two_personas has already proved the row
    exists — the assertion lives in the fixture rather than in every caller."""
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


async def _resume(db, user_id, slug):
    return await conversation_service.create_or_resume(
        db=db, user_id=user_id, persona_slug=slug, user_plan="pro",
    )


@pytest.mark.asyncio
async def test_it_resumes_a_recent_thread_that_was_spoken_in(db, two_personas):
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, slug,
        message_count=4,
        last_message_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is True
    assert conv.id == cid


@pytest.mark.asyncio
async def test_it_picks_the_thread_last_SPOKEN_in_not_the_newest(db, two_personas):
    """The ordering assertion. `older` was created first but answered yesterday;
    `newer` was created later and abandoned at its opening. created_at ordering
    would return `newer` — and would look fine, because it still resumes."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    now = datetime.now(timezone.utc)

    older_but_active = await _make_conv(
        db, user_id, slug, message_count=6,
        created_at=now - timedelta(days=9),
        last_message_at=now - timedelta(hours=20),
    )
    newer_but_stale = await _make_conv(
        db, user_id, slug, message_count=2,
        created_at=now - timedelta(days=2),
        last_message_at=now - timedelta(days=2),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is True
    assert conv.id == older_but_active, (
        f"expected the thread last spoken in ({older_but_active}), got {conv.id} "
        f"({'the newest by created_at' if conv.id == newer_but_stale else 'neither'})"
    )


@pytest.mark.asyncio
async def test_a_thread_older_than_the_window_is_not_resumed(db, two_personas):
    """15 days. A month-old thread is a different conversation; resuming it reads
    as the room having lost track of time rather than having kept up."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, slug, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(days=RESUME_WINDOW_DAYS + 1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is False
    assert conv.message_count == 0, "a miss must produce a genuinely fresh thread"


@pytest.mark.asyncio
async def test_a_thread_just_inside_the_window_is_resumed(db, two_personas):
    """The other side of the same boundary — a window that never matched would
    pass the test above for the wrong reason."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, slug, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(days=RESUME_WINDOW_DAYS - 1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is True
    assert conv.id == cid


@pytest.mark.asyncio
async def test_a_deleted_thread_is_not_resumed(db, two_personas):
    """deleted_at is the soft delete the Library relies on. Resuming one would
    resurrect a thread the person removed — the worst possible failure here."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, slug, message_count=5,
        last_message_at=datetime.now(timezone.utc) - timedelta(hours=2),
        deleted_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is False


@pytest.mark.asyncio
async def test_an_untouched_shell_is_not_resumed(db, two_personas):
    """message_count == 0 is the EXISTING dedup's business, not resume's. A shell
    has nothing to continue, and treating it as a resume would fire
    conversation_resumed for a thread that never started."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    await _make_conv(db, user_id, slug, message_count=0, last_message_at=None)
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is False


@pytest.mark.asyncio
async def test_another_personas_thread_is_untouched(db, two_personas):
    """Opening one persona must never hand back another's thread, however recent.
    The join is on slug; this is what proves it is actually applied."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    await _make_conv(
        db, user_id, other_slug, message_count=8,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    await db.flush()

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is False
    assert conv.persona_id == await _persona_id(db, slug)


@pytest.mark.asyncio
async def test_another_users_thread_is_untouched(db, two_personas):
    """The user_id predicate, asserted rather than assumed — this endpoint hands
    back a whole conversation, so a missing owner filter would be a disclosure
    bug, not a routing one."""
    slug, other_slug = two_personas
    mine = await _make_user(db)
    theirs = await _make_user(db)
    await _make_conv(
        db, theirs, slug, message_count=9,
        last_message_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    await db.flush()

    conv, resumed = await _resume(db, mine, slug)
    assert resumed is False
    assert conv.user_id == mine


@pytest.mark.asyncio
async def test_a_resumed_thread_keeps_its_id_and_therefore_its_history(db, two_personas):
    """The whole mechanism in one assertion: resuming returns the SAME
    conversation_id, which is why the send path's history query loads the full
    thread with no cross-conversation injection anywhere."""
    slug, other_slug = two_personas
    user_id = await _make_user(db)
    cid = await _make_conv(
        db, user_id, slug, message_count=3,
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

    conv, resumed = await _resume(db, user_id, slug)
    assert resumed is True
    count = (await db.execute(
        text("SELECT count(*) FROM messages WHERE conversation_id = :cid"), {"cid": conv.id},
    )).scalar_one()
    assert count == 1, "the resumed thread must still own its messages"
