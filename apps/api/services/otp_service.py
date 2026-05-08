"""
OTP business logic.

Generation, hashing, persistence, and verification.
Endpoints (routers/auth.py) call into this module — no HTTP concerns here.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import OtpCode
from services.email_service import send_email

# ── Constants ─────────────────────────────────────────────────────────────────

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "otp_email.html"

# ── Exceptions ────────────────────────────────────────────────────────────────

class OtpError(Exception):
    """Base for OTP verification errors."""


class OtpInvalid(OtpError):
    """Code does not match, or no recent record exists for this email."""


class OtpExpired(OtpError):
    """Most recent record exists but has expired (>10 minutes old)."""


class OtpLocked(OtpError):
    """Most recent record has hit max attempts and is locked."""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _generate_code() -> str:
    """Generate a 6-digit numeric code via stdlib secrets (CSPRNG)."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def _generate_salt() -> str:
    """Generate a 32-char hex salt."""
    return secrets.token_hex(16)


def _hash_code(code: str, salt: str) -> str:
    """SHA256 hex digest of 'salt:code'."""
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


# ── Public API ────────────────────────────────────────────────────────────────

async def create_and_send_otp(db: AsyncSession, email: str) -> None:
    """
    Generate a code, persist it (hashed), and email it to the user.

    Caller (endpoint) is responsible for rate limiting BEFORE calling this.
    Raises whatever the email provider raises if send fails.
    """
    code = _generate_code()
    salt = _generate_salt()
    code_hash = _hash_code(code, salt)

    record = OtpCode(
        email=email,
        code_hash=code_hash,
        salt=salt,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(record)
    await db.commit()

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    html = template.replace("{{code}}", code)
    send_email(to=email, subject="Your verification code", html=html)


async def verify_otp(db: AsyncSession, email: str, code: str) -> OtpCode:
    """
    Verify `code` against the most recent unused OTP for `email`.

    On success: marks record used_at, commits, returns the record.
    On failure: raises OtpInvalid / OtpExpired / OtpLocked.

    On wrong-code attempts (record exists but code mismatch), increments
    attempts counter before raising OtpInvalid.
    """
    result = await db.execute(
        select(OtpCode)
        .where(OtpCode.email == email)
        .where(OtpCode.used_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if record is None:
        raise OtpInvalid()

    if record.attempts >= OTP_MAX_ATTEMPTS:
        raise OtpLocked()

    now = datetime.now(timezone.utc)
    if record.expires_at < now:
        raise OtpExpired()

    expected = _hash_code(code, record.salt)
    if expected != record.code_hash:
        record.attempts += 1
        await db.commit()
        raise OtpInvalid()

    record.used_at = now
    await db.commit()
    return record
