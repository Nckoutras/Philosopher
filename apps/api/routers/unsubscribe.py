"""Public (no-auth) unsubscribe endpoint for the weekly-letter email.

The link is signed with an HMAC token (services.unsubscribe_token), so no login
is required and no information leaks: an invalid/forged token returns a generic
400 regardless of whether the user exists.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models import User
from services.unsubscribe_token import verify_token

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])

_CONFIRM_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unsubscribed</title></head>
<body style="font-family:Georgia,serif;background:#FAF4E6;color:#1F1B14;margin:0;padding:48px 24px;text-align:center">
<p style="font-size:18px;line-height:1.5;max-width:440px;margin:0 auto">You've been unsubscribed from weekly readings.</p>
</body></html>"""


@router.get("/weekly", response_class=HTMLResponse)
async def unsubscribe_weekly(
    u: str,
    t: str,
    db: AsyncSession = Depends(get_db),
):
    # Verify the signature first — never reveal whether the user exists.
    if not verify_token(u, t):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")

    result = await db.execute(select(User).where(User.id == u))
    user = result.scalar_one_or_none()
    if user is None:
        # Valid signature but no such user: generic 400, no info leak.
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")

    # Idempotent: setting an already-true flag is harmless.
    user.weekly_email_opt_out = True
    return HTMLResponse(content=_CONFIRM_HTML)
