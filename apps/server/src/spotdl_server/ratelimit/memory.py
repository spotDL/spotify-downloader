"""The default in-process fixed-window rate limiter.

A single dict maps ``key -> (window_start_epoch, count)``. Each :meth:`hit` reads
*now* through the injected :class:`~spotdl_server.auth.clock.Clock`, so tests
drive window resets with ``FakeClock.advance`` — no ``sleep``, no wall-clock
flakiness. This is the sole backend the offline test suite exercises; Redis is an
optional extra selected only when ``settings.redis_url`` is set.

Fixed-window semantics: the first hit in a window stamps ``window_start`` at the
current instant; subsequent hits within ``window_s`` increment the count; a hit
at or after ``window_start + window_s`` starts a fresh window. A request is
allowed while its post-increment count is ``<= limit``.
"""

from __future__ import annotations

import math

from spotdl_server.auth.clock import Clock
from spotdl_server.ratelimit.base import RateLimitResult


class InMemoryRateLimiter:
    """A per-key fixed-window counter held in a plain dict.

    Single-process only (no cross-worker coordination) — the right default for
    self-host and a single hosted worker; multi-worker hosted deployments set
    ``redis_url`` to share counters. ``aclose`` is a no-op (nothing to release).
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._buckets: dict[str, tuple[float, int]] = {}

    async def hit(self, key: str, *, limit: int, window_s: int) -> RateLimitResult:
        now = self._clock.now().timestamp()
        entry = self._buckets.get(key)
        if entry is None or now >= entry[0] + window_s:
            window_start, count = now, 1
        else:
            window_start, count = entry[0], entry[1] + 1
        self._buckets[key] = (window_start, count)

        allowed = count <= limit
        remaining = max(0, limit - count)
        retry_after = None if allowed else max(0, math.ceil(window_start + window_s - now))
        return RateLimitResult(
            allowed=allowed, limit=limit, remaining=remaining, retry_after=retry_after
        )

    async def aclose(self) -> None:
        """No resources to release — present for the :class:`RateLimiter` protocol."""
