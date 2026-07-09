"""Optional Redis fixed-window rate limiter (behind the ``redis`` extra).

Selected only when ``settings.redis_url`` is set AND the ``redis`` package is
importable (multi-worker hosted deployments that need shared counters); otherwise
the lifespan builds the in-memory backend. The default offline test suite never
exercises this module — a ``network``/``redis``-marked CI test may.

Atomicity: ``INCR`` then ``PEXPIRE`` (only when the counter was just created) plus
the ``PTTL`` read run in a single server-side Lua script, so the window's counter
and its TTL can never diverge under concurrency. ``retry_after`` comes from the
remaining TTL, not the injected clock (Redis owns window expiry here); the
``Clock`` is accepted for interface symmetry with the in-memory backend.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from spotdl_server.auth.clock import Clock
from spotdl_server.ratelimit.base import RateLimitResult

if TYPE_CHECKING:
    from redis.asyncio import Redis

# Atomic fixed-window step: increment, set the TTL once on window creation, and
# return both the count and the millisecond TTL in one round-trip.
_HIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return {current, redis.call('PTTL', KEYS[1])}
"""


class RedisRateLimiter:
    """A fixed-window limiter backed by a shared Redis instance."""

    def __init__(self, client: Redis, clock: Clock) -> None:
        self._client = client
        self._clock = clock  # reserved for interface symmetry; Redis owns expiry

    async def hit(self, key: str, *, limit: int, window_s: int) -> RateLimitResult:
        count, pttl_ms = await self._client.eval(_HIT_SCRIPT, 1, key, str(window_s * 1000))
        count = int(count)
        allowed = count <= limit
        remaining = max(0, limit - count)
        if allowed:
            retry_after = None
        elif pttl_ms is not None and int(pttl_ms) > 0:
            retry_after = max(0, math.ceil(int(pttl_ms) / 1000))
        else:  # TTL missing (key raced to expiry) — fall back to the full window
            retry_after = window_s
        return RateLimitResult(
            allowed=allowed, limit=limit, remaining=remaining, retry_after=retry_after
        )

    async def aclose(self) -> None:
        """Release the Redis connection pool on shutdown."""
        await self._client.aclose()


def build_redis_rate_limiter(redis_url: str, clock: Clock) -> RedisRateLimiter | None:
    """Build a :class:`RedisRateLimiter` from ``redis_url``, or ``None`` if unavailable.

    Returns ``None`` when the ``redis`` package is not installed so the caller
    (the lifespan) falls back to the in-memory backend rather than crashing.
    """
    try:
        from redis.asyncio import Redis
    except ImportError:  # pragma: no cover - exercised only without the redis extra
        return None
    client: Any = Redis.from_url(redis_url)
    return RedisRateLimiter(client, clock)
