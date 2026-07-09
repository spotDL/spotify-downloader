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

from spotdl_server.settings import DeploymentMode

if TYPE_CHECKING:
    from spotdl_server.settings import Settings

# Marks the handler this module installs so re-configuring replaces only our own
# handler and never touches, e.g., pytest's caplog handler on the root logger.
_HANDLER_TAG = "_spotdl_observability"

# The operator's access-log toggle. ``uvicorn --no-access-log`` clears this
# logger's handlers and sets ``propagate=False``; our middleware already emits the
# authoritative ``spotdl_server.access`` line, so we must NEVER re-enable or
# force-propagate this logger — doing so defeats ``--no-access-log`` and doubles
# every request log. It is deliberately excluded from both loops below.
_UVICORN_ACCESS = "uvicorn.access"

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
    # CONTRACT A1 embedded default: the embedded server backs the CLI, where INFO
    # JSON lines are noise on the user's terminal. Unless ``log_level`` was set
    # explicitly, embedded mode logs at WARNING through the human-readable
    # ConsoleRenderer; every other mode (and any explicit level) keeps the JSON
    # pipeline at the configured level.
    embedded_quiet = (
        settings.mode is DeploymentMode.EMBEDDED and "log_level" not in settings.model_fields_set
    )
    effective_level = "WARNING" if embedded_quiet else settings.log_level.upper()
    renderer: Any = (
        structlog.dev.ConsoleRenderer(colors=False)
        if embedded_quiet
        else structlog.processors.JSONRenderer(default=str)
    )

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
            # JSONRenderer's ``default=str`` masks SecretStr (and any non-JSON
            # object) instead of raising, so secrets render as their placeholder,
            # never leaked. ConsoleRenderer (embedded) likewise repr/str-s values,
            # so SecretStr stays masked there too.
            renderer,
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
    root.setLevel(effective_level)

    # Undo any prior ``disable_existing_loggers=True`` (Alembic's ``fileConfig``
    # on migrate, or a stray ``dictConfig``): a disabled logger silently drops
    # every record, which would black-hole our JSON access log and any library
    # logs. Re-enabling here makes ``configure_logging`` authoritative whenever it
    # is called, regardless of what touched ``logging`` before it.
    # ``uvicorn.access`` is excluded: re-enabling it would revive an access log an
    # operator suppressed with ``--no-access-log`` (see ``_UVICORN_ACCESS``).
    for logger in root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger) and logger.name != _UVICORN_ACCESS:
            logger.disabled = False

    # Framework loggers ship their own handlers/formatters; strip them so records
    # flow through the single root JSON handler (no double lines, one format) and
    # propagate to the root level. ``uvicorn.access`` is deliberately absent — we
    # leave it in whatever state uvicorn set so ``--no-access-log`` is honoured and
    # our middleware's ``spotdl_server.access`` line is the sole access log.
    for name in ("uvicorn", "uvicorn.error"):
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
