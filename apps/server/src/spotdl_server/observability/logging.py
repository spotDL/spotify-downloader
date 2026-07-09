"""CONTRACT A1 — structlog JSON logging.

``configure_logging`` installs a single stdout handler whose formatter renders
every record — structlog-native *and* foreign stdlib records (uvicorn,
sqlalchemy) — as one JSON line carrying ``ts, level, event, logger, mode``.
Routing stdlib logging through the same ``ProcessorFormatter`` means there is
exactly one log format for the whole process.

Secrets never leak: the JSON renderer serialises unknown objects via ``str``, so
a ``pydantic.SecretStr`` renders as its masked placeholder rather than its value.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import TYPE_CHECKING, Any, TextIO

import structlog

if TYPE_CHECKING:
    from spotdl_server.settings import Settings

# Marks the handler this module installs so re-configuring replaces only our own
# handler and never touches, e.g., pytest's caplog handler on the root logger.
_HANDLER_TAG = "_spotdl_observability"

EventDict = MutableMapping[str, Any]


def _static_field(key: str, value: str) -> Any:
    """A processor that stamps a constant ``key=value`` onto every record."""

    def processor(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
        event_dict[key] = value
        return event_dict

    return processor


def configure_logging(settings: Settings, *, stream: TextIO | None = None) -> None:
    """Configure structlog + stdlib logging to emit CONTRACT A1 JSON lines.

    ``stream`` overrides the destination (defaults to ``sys.stdout``); tests pass
    a ``StringIO`` to capture and parse the emitted lines.
    """
    mode_field = _static_field("mode", settings.mode.value)
    timestamper = structlog.processors.TimeStamper(fmt="iso", key="ts")

    # Shared across native and foreign records so both carry the same fields.
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        mode_field,
        timestamper,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Do NOT cache: a cached bound logger ignores later ``configure_logging``
        # calls, which would pin the first-seen output stream/handler. Recreating
        # per call keeps reconfiguration honest (and matters in the test suite,
        # where each app/logging setup rebinds the destination).
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # ``default=str`` masks SecretStr (and any non-JSON object) instead of
            # raising, so secrets are rendered as their placeholder, never leaked.
            structlog.processors.JSONRenderer(default=str),
        ],
    )

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    handler.set_name(_HANDLER_TAG)

    root = logging.getLogger()
    for existing in list(root.handlers):
        if existing.get_name() == _HANDLER_TAG:
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Undo any prior ``disable_existing_loggers=True`` (Alembic's ``fileConfig``
    # on migrate, or a stray ``dictConfig``): a disabled logger silently drops
    # every record, which would black-hole our JSON access log and any library
    # logs. Re-enabling here makes ``configure_logging`` authoritative whenever it
    # is called, regardless of what touched ``logging`` before it.
    for logger in root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.disabled = False

    # Framework loggers ship their own handlers/formatters; strip them so records
    # flow through the single root JSON handler (no double lines, one format) and
    # propagate to the root level.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    # SQLAlchemy echoes every statement at INFO when its logger is enabled for
    # INFO; since the root is INFO, pin these to WARNING so a debug-friendly root
    # level does not silently turn on full SQL echo.
    for name in ("sqlalchemy", "sqlalchemy.engine"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)
        logger.propagate = True
