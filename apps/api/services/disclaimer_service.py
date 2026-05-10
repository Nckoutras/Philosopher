"""
Disclaimer business logic.

Fetches the current disclaimer version, checks user acceptance status,
and records acceptance. Endpoints (routers/disclaimer.py) call into
this module — no HTTP concerns here.
"""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import DisclaimerAcceptance, DisclaimerVersion

# ── Exceptions ────────────────────────────────────────────────────────────────

class DisclaimerError(Exception):
    """Base for disclaimer errors."""


class NoVersionAvailable(DisclaimerError):
    """No disclaimer_versions row exists in the database."""


# ── Public API ────────────────────────────────────────────────────────────────

async def get_current_version(db: AsyncSession) -> DisclaimerVersion:
    """Return the disclaimer version with the most recent effective_at."""
    result = await db.execute(
        select(DisclaimerVersion)
        .order_by(DisclaimerVersion.effective_at.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise NoVersionAvailable()
    return version


async def user_needs_acceptance(user_id: str, db: AsyncSession) -> bool:
    """
    Return True if the user has not accepted the current disclaimer version.

    Returns False if no disclaimer version exists (don't block login on
    misconfigured DB).
    """
    try:
        version = await get_current_version(db)
    except NoVersionAvailable:
        return False

    result = await db.execute(
        select(DisclaimerAcceptance)
        .where(DisclaimerAcceptance.user_id == user_id)
        .where(DisclaimerAcceptance.version_id == version.id)
    )
    return result.scalar_one_or_none() is None


async def accept(
    user_id: str,
    confirmed_age_18: bool,
    confirmed_non_therapy: bool,
    locale: str,
    ip_address: str | None,
    user_agent: str | None,
    db: AsyncSession,
) -> DisclaimerAcceptance:
    """
    Insert a disclaimer acceptance row for the current version.

    Idempotent — if the user has already accepted this version (UNIQUE
    constraint on user_id + version_id), returns the existing row as
    success rather than raising.
    """
    version = await get_current_version(db)

    try:
        record = DisclaimerAcceptance(
            user_id=user_id,
            version_id=version.id,
            locale=locale,
            confirmed_age_18=confirmed_age_18,
            confirmed_non_therapy=confirmed_non_therapy,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(record)
        await db.flush()
        await db.commit()
        return record
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(DisclaimerAcceptance)
            .where(DisclaimerAcceptance.user_id == user_id)
            .where(DisclaimerAcceptance.version_id == version.id)
        )
        return result.scalar_one()
