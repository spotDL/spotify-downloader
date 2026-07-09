"""CONTRACT A4 — optional Sentry error reporting.

``sentry-sdk`` is an optional extra: it is imported lazily *inside*
``init_sentry`` and only when a DSN is configured, so a default install never
imports it and importing this module stays cheap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spotdl_server.settings import Settings


def init_sentry(settings: Settings) -> bool:
    """Initialise Sentry when a DSN is set; a no-op otherwise.

    Returns ``True`` when Sentry was initialised, ``False`` when no DSN is
    configured. Raises a clear error if a DSN is set but the ``sentry`` extra is
    not installed.
    """
    if settings.sentry_dsn is None:
        return False

    try:
        import sentry_sdk  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on extra
        raise RuntimeError(
            "SPOTDL_SENTRY_DSN is set but sentry-sdk is not installed "
            "(install the 'sentry' extra: pip install 'spotdl-server[sentry]')"
        ) from exc

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.mode.value,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )
    return True
