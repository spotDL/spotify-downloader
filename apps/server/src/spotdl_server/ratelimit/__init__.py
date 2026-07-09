"""Rate-limiting leaf utility (spec §6.4 / Plan 6, Task 11).

A leaf package below ``services`` in the import graph: it imports neither FastAPI
nor SQLAlchemy nor ``services``, so both ``services`` and the ``api`` glue may
depend on it without a layering violation (``ratelimit.redis`` importing ``redis``
is the one allowed external edge). It holds the limiter interface + backends and
the pure tier classifier; the middleware that applies it is HTTP glue in ``api``.

:func:`build_rate_limiter` is the single selection seam, called once in the
FastAPI lifespan: a :class:`RedisRateLimiter` when ``redis_url`` is set and the
``redis`` extra is installed, otherwise the in-process :class:`InMemoryRateLimiter`.
"""

from __future__ import annotations

from spotdl_server.auth.clock import Clock
from spotdl_server.ratelimit.base import RateLimiter, RateLimitResult
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.ratelimit.tiers import (
    AUTH_PATHS,
    TIERS,
    Tier,
    classify,
    client_ip,
)


def build_rate_limiter(redis_url: str | None, clock: Clock) -> RateLimiter:
    """Select the rate-limit backend (spec §6.4). Called once in the lifespan.

    Redis is used only when ``redis_url`` is set AND the ``redis`` package is
    importable; both misses fall back to the in-memory backend so a self-host
    server (or a hosted one without the extra) always gets a working limiter.
    """
    if redis_url:
        from spotdl_server.ratelimit.redis import build_redis_rate_limiter

        limiter = build_redis_rate_limiter(redis_url, clock)
        if limiter is not None:
            return limiter
    return InMemoryRateLimiter(clock)


__all__ = [
    "AUTH_PATHS",
    "InMemoryRateLimiter",
    "RateLimiter",
    "RateLimitResult",
    "TIERS",
    "Tier",
    "build_rate_limiter",
    "classify",
    "client_ip",
]
