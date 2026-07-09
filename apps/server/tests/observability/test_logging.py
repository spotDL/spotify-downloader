"""CONTRACT A1 — structlog JSON logging.

``configure_logging`` routes both structlog-native and stdlib records through a
single JSON renderer that emits one line per record carrying the CONTRACT A1
fields (``ts, level, event, logger, mode``), and secret values never leak into
the rendered line.
"""

from __future__ import annotations

import io
import json
import logging

import pytest
import structlog
from spotdl_server.observability.logging import configure_logging
from spotdl_server.settings import DeploymentMode, Settings


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_structlog_record_is_one_json_line_with_contract_fields() -> None:
    stream = io.StringIO()
    configure_logging(Settings(mode=DeploymentMode.SELFHOST), stream=stream)

    structlog.get_logger("spotdl_server.test").info("resolved", extra_field=7)

    records = _lines(stream)
    assert len(records) == 1
    record = records[0]
    for field in ("ts", "level", "event", "logger", "mode"):
        assert field in record, f"missing {field}: {record}"
    assert record["event"] == "resolved"
    assert record["level"] == "info"
    assert record["logger"] == "spotdl_server.test"
    assert record["mode"] == "selfhost"
    assert record["extra_field"] == 7


def test_stdlib_records_are_routed_through_the_same_json_renderer() -> None:
    stream = io.StringIO()
    configure_logging(Settings(mode=DeploymentMode.HOSTED), stream=stream)

    logging.getLogger("uvicorn.error").warning("boot")

    records = _lines(stream)
    assert len(records) == 1
    assert records[0]["event"] == "boot"
    assert records[0]["level"] == "warning"
    assert records[0]["logger"] == "uvicorn.error"
    assert records[0]["mode"] == "hosted"


def test_secret_values_never_appear_in_output() -> None:
    stream = io.StringIO()
    settings = Settings(mode=DeploymentMode.HOSTED, auth_secret_key="super-secret-value")
    configure_logging(settings, stream=stream)

    structlog.get_logger("spotdl_server.test").info(
        "startup", auth_secret_key=settings.auth_secret_key, settings=settings
    )

    raw = stream.getvalue()
    assert "super-secret-value" not in raw
    # The masked SecretStr placeholder is what should be rendered instead.
    assert "**********" in raw


def test_no_access_log_suppression_is_respected() -> None:
    # `uvicorn --no-access-log` clears the access logger's handlers and stops its
    # propagation before our factory runs; configure_logging must not revive it
    # (which would defeat the flag and double every request log, since our
    # middleware already emits the authoritative spotdl_server.access line).
    access = logging.getLogger("uvicorn.access")
    saved_propagate, saved_handlers = access.propagate, list(access.handlers)
    access.handlers = []
    access.propagate = False
    try:
        stream = io.StringIO()
        configure_logging(Settings(), stream=stream)

        assert access.propagate is False  # operator's suppression left intact

        # Our middleware's access line is authoritative and still emits...
        structlog.get_logger("spotdl_server.access").info(
            "request",
            request_id="r1",
            method="GET",
            path="/api/v1/health",
            status_code=200,
            duration_ms=1.0,
        )
        # ...while uvicorn's own access record stays suppressed (no double line).
        logging.getLogger("uvicorn.access").info("native uvicorn access line")

        records = _lines(stream)
        access_lines = [r for r in records if r.get("logger") == "spotdl_server.access"]
        uvicorn_lines = [r for r in records if r.get("logger") == "uvicorn.access"]
        assert len(access_lines) == 1, records
        assert uvicorn_lines == [], records
    finally:
        access.propagate, access.handlers = saved_propagate, saved_handlers


def test_embedded_mode_defaults_to_warning_console_not_json() -> None:
    # CONTRACT A1: embedded (CLI) mode wants quiet, human-readable output — a
    # WARNING default and the structlog ConsoleRenderer, not INFO JSON noise.
    stream = io.StringIO()
    configure_logging(Settings(mode=DeploymentMode.EMBEDDED), stream=stream)

    log = structlog.get_logger("spotdl_server.test")
    log.info("info noise")  # dropped by the WARNING default
    log.warning("kept warning")

    out = stream.getvalue()
    assert "info noise" not in out
    assert "kept warning" in out
    # Human console output, not JSON.
    first = next(line for line in out.splitlines() if line.strip())
    with pytest.raises(json.JSONDecodeError):
        json.loads(first)


def test_embedded_mode_honours_explicit_log_level_as_json() -> None:
    # An explicit log_level opts back into the JSON pipeline at that level, even
    # in embedded mode (the quiet default only applies when it was left unset).
    stream = io.StringIO()
    configure_logging(Settings(mode=DeploymentMode.EMBEDDED, log_level="INFO"), stream=stream)

    structlog.get_logger("spotdl_server.test").info("shown", k=1)

    records = _lines(stream)
    assert len(records) == 1
    assert records[0]["event"] == "shown"
    assert records[0]["k"] == 1


def test_reconfigure_does_not_duplicate_handlers() -> None:
    stream = io.StringIO()
    configure_logging(Settings(), stream=stream)
    configure_logging(Settings(), stream=stream)

    structlog.get_logger("spotdl_server.test").info("once")
    assert len(_lines(stream)) == 1
