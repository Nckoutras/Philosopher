from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import config
from models import Subscription


async def get_user_tier(db: AsyncSession, user_id: UUID) -> Literal["free", "pro", "premium"]:
    if config.BETA_GRANT_PRO_TO_ALL:
        return "pro"

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == str(user_id))
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return "free"
    if sub.status not in ("active", "trialing"):
        return "free"
    if sub.current_period_end is None:
        return "free"
    if sub.current_period_end <= datetime.now(timezone.utc):
        return "free"
    if sub.plan not in ("pro", "premium"):
        return "free"
    return sub.plan
