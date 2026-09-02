from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db, AsyncSessionLocal
from models import User, Subscription
from config import config


bearer_scheme = HTTPBearer()


def create_token(user_id: str, email: str, token_version: int) -> str:
    """Mint a session token. `token_version` is the user's CURRENT users.token_version
    (A16): both validators reject a token whose "ver" differs from the column, so a
    mint must always read the live value rather than carry one forward."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "ver": token_version, "exp": expire},
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # A16 — revocation. No extra query: the row is already loaded. A missing "ver"
    # is a pre-A16 token and reads as 0, matching the column default, so those stay
    # valid until this user's first revocation.
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(status_code=401, detail="Token revoked")
    return user


async def get_current_user_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, str]:
    from services.tier_service import get_user_tier
    tier = await get_user_tier(db, user.id)
    return user, tier


async def get_user_plan_streaming(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> tuple[User, str]:
    """No-pin auth for SSE streaming endpoints (§5 pool-leak fix).

    Unlike get_current_user_plan — which depends on get_db, a yield-dependency
    whose session is released only AFTER the StreamingResponse body is fully
    sent, pinning a pooled session for the entire multi-second token stream —
    this opens and CLOSES its own short-lived session before the stream begins.
    The returned User is detached but its loaded scalar attributes (id,
    full_name, is_admin) stay readable. Scoped to streaming routes only; do NOT
    use elsewhere.
    """
    from services.tier_service import get_user_tier

    payload = decode_token(credentials.credentials)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # A16 — revocation, same check and same position as get_current_user. It
        # lives INSIDE this block deliberately: the session closes below and the
        # returned User is detached, so the comparison must happen while the row
        # is still attached. Forgetting this validator would leave every SSE
        # endpoint accepting revoked tokens.
        if payload.get("ver", 0) != user.token_version:
            raise HTTPException(status_code=401, detail="Token revoked")
        tier = await get_user_tier(db, user.id)
    return user, tier


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
