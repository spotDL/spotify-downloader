"""The injectable time seam for the community layer (CONTRACT).

Every expiry and rotation decision in Plan 6 — JWT ``iat``/``exp``, refresh-token
rotation and expiry, PAT expiry, and rate-limit windows — reads *now* through a
:class:`Clock` rather than calling :func:`datetime.now` directly. Production wires
the :class:`SystemClock`; tests wire a ``FakeClock`` (see ``tests/conftest.py``)
so any of those windows can be made to elapse deterministically without sleeping
or monkeypatching the standard library.

Per the no-module-level-singletons rule, the concrete clock is built in the
FastAPI lifespan and injected into services — this module defines only the
protocol and the real implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """A source of the current time.

    Implementations MUST return a timezone-aware UTC :class:`datetime` so that
    every downstream comparison (``expires_at <= now``) is unambiguous.
    """

    def now(self) -> datetime:
        """Return the current instant as a tz-aware UTC ``datetime``."""
        ...


class SystemClock:
    """The production :class:`Clock`: the real wall clock, in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
