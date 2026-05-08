"""
Redis-backed rate limiting.

Atomic counter per key with TTL on first hit.
Caller constructs the full key (e.g. "otp_request:user@example.com").
"""
from typing import Optional
import redis.asyncio as redis
from config import config

_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _pool


async def check_and_increment(
    key: str,
    max_count: int,
    window_seconds: int,
) -> bool:
    """
    Increment the counter at `key`. Set TTL on first hit.

    Returns True if the request is within the limit (count <= max_count).
    Returns False if the limit has been exceeded.
    """
    r = await get_redis()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window_seconds)
    return count <= max_count
