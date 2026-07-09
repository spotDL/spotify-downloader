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


def test_reconfigure_does_not_duplicate_handlers() -> None:
    stream = io.StringIO()
    configure_logging(Settings(), stream=stream)
    configure_logging(Settings(), stream=stream)

    structlog.get_logger("spotdl_server.test").info("once")
    assert len(_lines(stream)) == 1
