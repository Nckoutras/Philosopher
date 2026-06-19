"""HMAC token for the public weekly-letter unsubscribe link.

Stateless: the token is HMAC-SHA256(user_id) keyed by the existing server
secret (JWT_SECRET). No new secret, no DB storage. Used by the worker to build
the link and by the unsubscribe router to verify it.
"""
import hashlib
import hmac

from config import config


def make_token(user_id: str) -> str:
    """Deterministic unsubscribe token for a user id."""
    return hmac.new(
        config.JWT_SECRET.encode("utf-8"),
        str(user_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_token(user_id: str, token: str) -> bool:
    """Constant-time comparison; False on any missing/garbage input."""
    if not user_id or not token:
        return False
    return hmac.compare_digest(make_token(user_id), token)
