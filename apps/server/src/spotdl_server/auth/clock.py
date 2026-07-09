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


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` as a tz-aware UTC datetime.

    Timestamps written as tz-aware UTC round-trip through SQLite as *naive*
    datetimes (SQLite has no native ``timestamptz``; the offset is dropped and the
    value re-read without a ``tzinfo``), while Postgres returns them tz-aware. So
    a stored ``expires_at`` compared against :meth:`Clock.now` may be naive on
    SQLite — this attaches UTC to a naive value (it is known to be UTC) and
    normalizes an aware value to UTC, making ``expires_at <= now`` unambiguous on
    both dialects.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
