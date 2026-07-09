"""Deterministic unit tests for :class:`InMemoryRateLimiter` (the default backend).

The whole suite is offline: the limiter reads *now* through the injected
:class:`FakeClock`, so a fixed-window's reset is driven by ``clock.advance`` — no
``sleep`` and no wall-clock flakiness. These pin the fixed-window semantics the
middleware relies on: decreasing ``remaining`` under the limit, a blocked result
with a positive ``retry_after`` at ``limit + 1``, a window reset after the window
elapses, and per-key isolation.
"""

from __future__ import annotations

from spotdl_server.ratelimit.memory import InMemoryRateLimiter

from apps.server.tests.conftest import FakeClock


async def test_under_limit_allows_with_decreasing_remaining() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    first = await limiter.hit("k", limit=3, window_s=60)
    second = await limiter.hit("k", limit=3, window_s=60)
    third = await limiter.hit("k", limit=3, window_s=60)

    assert (first.allowed, first.remaining, first.retry_after) == (True, 2, None)
    assert (second.allowed, second.remaining, second.retry_after) == (True, 1, None)
    assert (third.allowed, third.remaining, third.retry_after) == (True, 0, None)
    assert first.limit == 3


async def test_over_limit_blocks_with_retry_after() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    for _ in range(2):
        assert (await limiter.hit("k", limit=2, window_s=60)).allowed

    blocked = await limiter.hit("k", limit=2, window_s=60)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after == 60  # full window remains — no time has passed


async def test_retry_after_counts_down_within_window() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    assert (await limiter.hit("k", limit=1, window_s=60)).allowed
    clock.advance(10)
    blocked = await limiter.hit("k", limit=1, window_s=60)

    assert blocked.allowed is False
    assert blocked.retry_after == 50  # ceil(60 - 10)


async def test_window_resets_after_elapsing() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    assert (await limiter.hit("k", limit=1, window_s=60)).allowed
    assert (await limiter.hit("k", limit=1, window_s=60)).allowed is False

    clock.advance(60)  # boundary reached -> the window resets

    fresh = await limiter.hit("k", limit=1, window_s=60)
    assert fresh.allowed is True
    assert fresh.remaining == 0


async def test_keys_are_independent() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(clock)

    assert (await limiter.hit("a", limit=1, window_s=60)).allowed
    assert (await limiter.hit("a", limit=1, window_s=60)).allowed is False

    # A different key has its own untouched budget.
    other = await limiter.hit("b", limit=1, window_s=60)
    assert other.allowed is True
    assert other.remaining == 0


async def test_aclose_is_a_noop() -> None:
    limiter = InMemoryRateLimiter(FakeClock())
    await limiter.aclose()  # must not raise
