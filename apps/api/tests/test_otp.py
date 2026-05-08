"""
Tests for services.otp_service.

Pattern: AsyncMock for db, monkeypatch for send_email.
No real database, no real email send, no Redis.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from services import otp_service
from services.otp_service import (
    _generate_code,
    _generate_salt,
    _hash_code,
    create_and_send_otp,
    verify_otp,
    OtpInvalid,
    OtpExpired,
    OtpLocked,
    OTP_LENGTH,
    OTP_MAX_ATTEMPTS,
)
from models import OtpCode


# ── Helper function tests (sync) ─────────────────────────────────────────────

def test_generate_code_format():
    """Code is exactly OTP_LENGTH digits, zero-padded if needed."""
    for _ in range(50):
        code = _generate_code()
        assert len(code) == OTP_LENGTH
        assert code.isdigit()


def test_generate_salt_format():
    """Salt is 32 hex characters."""
    salt = _generate_salt()
    assert len(salt) == 32
    int(salt, 16)  # raises if not valid hex


def test_hash_code_deterministic():
    assert _hash_code("123456", "abc") == _hash_code("123456", "abc")


def test_hash_code_changes_with_salt():
    assert _hash_code("123456", "saltA") != _hash_code("123456", "saltB")


def test_hash_code_changes_with_code():
    assert _hash_code("111111", "salt") != _hash_code("222222", "salt")


# ── create_and_send_otp ──────────────────────────────────────────────────────

async def test_create_and_send_otp_persists_and_emails(monkeypatch):
    db = AsyncMock()
    db.add = MagicMock()  # SQLAlchemy db.add() is sync

    sent_emails = []

    def fake_send(to, subject, html):
        sent_emails.append({"to": to, "subject": subject, "html": html})

    monkeypatch.setattr(otp_service, "send_email", fake_send)

    await create_and_send_otp(db, "user@example.com")

    db.add.assert_called_once()
    db.commit.assert_awaited_once()

    record = db.add.call_args[0][0]
    assert isinstance(record, OtpCode)
    assert record.email == "user@example.com"
    assert len(record.code_hash) == 64  # SHA256 hex digest length
    assert len(record.salt) == 32
    assert record.expires_at > datetime.now(timezone.utc)

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "user@example.com"
    assert sent_emails[0]["subject"] == "Your verification code"
    # Template placeholder must be substituted
    assert "{{code}}" not in sent_emails[0]["html"]


# ── verify_otp ───────────────────────────────────────────────────────────────

def _mock_db_with_record(record):
    """Build an AsyncMock db whose execute() returns the given record."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=record)
    db.execute.return_value = result
    return db


def _make_record(code: str, **overrides) -> OtpCode:
    salt = "a" * 32
    defaults = {
        "email": "user@example.com",
        "code_hash": _hash_code(code, salt),
        "salt": salt,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0,
        "used_at": None,
    }
    defaults.update(overrides)
    return OtpCode(**defaults)


async def test_verify_otp_success():
    record = _make_record("123456")
    db = _mock_db_with_record(record)

    returned = await verify_otp(db, "user@example.com", "123456")

    assert returned is record
    assert record.used_at is not None
    db.commit.assert_awaited()


async def test_verify_otp_no_record_raises_invalid():
    db = _mock_db_with_record(None)

    with pytest.raises(OtpInvalid):
        await verify_otp(db, "user@example.com", "123456")

    db.commit.assert_not_awaited()


async def test_verify_otp_wrong_code_increments_attempts_then_invalid():
    record = _make_record("111111", attempts=2)
    db = _mock_db_with_record(record)

    with pytest.raises(OtpInvalid):
        await verify_otp(db, "user@example.com", "999999")

    assert record.attempts == 3
    assert record.used_at is None
    db.commit.assert_awaited()


async def test_verify_otp_expired_raises_expired():
    record = _make_record(
        "123456",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db = _mock_db_with_record(record)

    with pytest.raises(OtpExpired):
        await verify_otp(db, "user@example.com", "123456")

    assert record.used_at is None


async def test_verify_otp_locked_raises_locked():
    record = _make_record("123456", attempts=OTP_MAX_ATTEMPTS)
    db = _mock_db_with_record(record)

    with pytest.raises(OtpLocked):
        await verify_otp(db, "user@example.com", "999999")

    assert record.used_at is None
