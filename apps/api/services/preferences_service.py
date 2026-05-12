"""
User preferences business logic.

Upserts user_preferences rows (one per user) and reads them back.
Endpoints (routers/preferences.py) call into this module — no HTTP
concerns here.
"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from models import UserPreference


async def upsert_preferences(
    user_id: str,
    themes: list[str],
    other_text: str | None,
    need_most: str,
    db: AsyncSession,
) -> UserPreference:
    """
    Insert or update the user's preferences row.

    Uses Postgres INSERT ... ON CONFLICT (user_id) DO UPDATE so the operation
    is atomic in a single statement. Returns the resulting row.
    """
    stmt = (
        pg_insert(UserPreference)
        .values(
            user_id=user_id,
            themes=themes,
            other_text=other_text,
            need_most=need_most,
        )
        .on_conflict_do_update(
            index_elements=[UserPreference.user_id],
            set_={
                "themes": themes,
                "other_text": other_text,
                "need_most": need_most,
                "updated_at": func.now(),
            },
        )
        .returning(UserPreference)
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_user_preferences(
    user_id: str,
    db: AsyncSession,
) -> UserPreference | None:
    """Return the user's preferences row, or None if not set yet."""
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()
