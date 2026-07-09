"""The rate-limiter interface — ONE protocol, two backends (CONTRACT — spec §6.4).

Both the in-memory default (:mod:`~spotdl_server.ratelimit.memory`) and the
optional Redis backend (:mod:`~spotdl_server.ratelimit.redis`) implement this
protocol, and the middleware sees only :class:`RateLimiter`. The backend is
chosen once in the FastAPI lifespan (never a per-request conditional) and closed
via :meth:`~RateLimiter.aclose` on shutdown.

This module is a leaf utility: it imports neither FastAPI nor SQLAlchemy, so both
``services`` and the ``api`` glue may depend on it without a layering violation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RateLimitResult:
    """The outcome of a single :meth:`RateLimiter.hit`.

    ``remaining`` is the budget left in the current window after this hit (never
    negative); ``retry_after`` is the whole-seconds delay until the window resets
    and is ``None`` exactly when ``allowed`` is ``True``.
    """

    allowed: bool
    limit: int
    remaining: int
    retry_after: int | None  # seconds; None when allowed


@runtime_checkable
class RateLimiter(Protocol):
    """A fixed-window counter keyed by an opaque string.

    ``hit`` records one request against ``key`` and reports whether it is allowed
    under ``limit`` requests per ``window_s`` seconds. Implementations must be
    safe to call concurrently on the shared instance built in the lifespan.
    """

    async def hit(self, key: str, *, limit: int, window_s: int) -> RateLimitResult: ...

    async def aclose(self) -> None: ...
