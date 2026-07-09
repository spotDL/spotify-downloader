"""``Loadable`` state envelope, ``ErrorDisplay``, and the ``guard`` funnel (CONTRACT A).

Every remote call a view-model makes is awaited through :func:`guard`, which turns
an :class:`~spotdl_cli.errors.ApiError` (or a connection failure) into a
``Loadable.failed(ErrorDisplay)`` — a view-model **never raises to the screen**. The
error copy comes from Plan 8's single CONTRACT E table via
:func:`~spotdl_cli.errors.describe_api_error` (CONTRACT G), so the TUI toast and the
CLI handler can never drift.
"""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from spotdl_cli.errors import ApiError, describe_api_error

T = TypeVar("T")

Severity = Literal["error", "warning"]

# CONTRACT G: transient/degraded conditions render as a warning toast; everything
# else is an error. Compared against ``ApiError.code.value`` — the string values of
# the server's ``ErrorCode`` (named as literals here because the framework-free
# view-model layer must not import the generated ``ErrorCode`` enum, CONTRACT I).
_WARNING_CODES: frozenset[str] = frozenset({"provider_unavailable", "rate_limited"})

# Root package names of the transport stack. A raised exception from one of these
# is a connection/protocol failure (the view-model layer must not import them, so
# it recognises them structurally by module rather than by type — CONTRACT I).
_TRANSPORT_MODULES: frozenset[str] = frozenset({"httpx", "httpx_ws", "httpcore"})


class LoadState(StrEnum):
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ErrorDisplay:
    """A screen-ready error: human ``message`` + optional ``code`` + ``severity``."""

    message: str
    code: str | None
    severity: Severity


@dataclass(frozen=True, slots=True)
class Loadable(Generic[T]):
    """An immutable snapshot of an async load: state + optional data/error."""

    state: LoadState
    data: T | None = None
    error: ErrorDisplay | None = None

    @classmethod
    def idle(cls) -> Loadable[T]:
        return cls(LoadState.IDLE)

    @classmethod
    def loading(cls) -> Loadable[T]:
        return cls(LoadState.LOADING)

    @classmethod
    def ready(cls, data: T) -> Loadable[T]:
        return cls(LoadState.READY, data=data)

    @classmethod
    def failed(cls, err: ErrorDisplay) -> Loadable[T]:
        return cls(LoadState.ERROR, error=err)


def describe_error(err: ApiError) -> ErrorDisplay:
    """Map an :class:`ApiError` to an :class:`ErrorDisplay` (CONTRACT G severity)."""
    rendering = describe_api_error(err)
    severity: Severity = "warning" if err.code.value in _WARNING_CODES else "error"
    return ErrorDisplay(message=rendering.message, code=err.code.value, severity=severity)


def _is_transport_error(exc: BaseException) -> bool:
    """True when ``exc`` originates in the transport stack (a connection failure)."""
    root = type(exc).__module__.split(".", 1)[0]
    return root in _TRANSPORT_MODULES or isinstance(exc, OSError)


def _connection_display(exc: BaseException) -> ErrorDisplay:
    reason = str(exc).strip() or type(exc).__name__
    return ErrorDisplay(message=f"couldn't reach the server: {reason}", code=None, severity="error")


def as_connection_error(exc: BaseException) -> ErrorDisplay | None:
    """Return a connection ``ErrorDisplay`` if ``exc`` is a transport failure, else ``None``.

    Used by the queue's WS ``stream`` (which drives a raw ``async with``/``async for``
    rather than a single coroutine) to recognise a reconnectable transport error
    without importing the transport stack (CONTRACT I).
    """
    return _connection_display(exc) if _is_transport_error(exc) else None


async def guard(coro: Awaitable[T]) -> Loadable[T]:
    """Await ``coro``; map ``ApiError``/connection errors to ``Loadable.failed``.

    The one place every view-model funnels a remote call through (rule A.2): a
    typed server error becomes its CONTRACT E copy, a transport failure becomes a
    generic connection notice, and a genuine programming error is re-raised.
    """
    try:
        return Loadable.ready(await coro)
    except ApiError as exc:
        return Loadable.failed(describe_error(exc))
    except Exception as exc:  # noqa: BLE001 — narrowed to transport failures below
        if _is_transport_error(exc):
            return Loadable.failed(_connection_display(exc))
        raise
