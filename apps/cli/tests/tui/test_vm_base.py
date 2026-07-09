"""``describe_api_error`` (CONTRACT G) + ``Loadable``/``guard`` (CONTRACT A)."""

from __future__ import annotations

import httpx
import pytest
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError, ExitCode, describe_api_error, format_api_error
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, LoadState, guard


@pytest.mark.parametrize("code", list(ErrorCode))
def test_describe_covers_every_code(code: ErrorCode) -> None:
    """Every ``ErrorCode`` has a real CONTRACT E row (never the unknown fallback)."""
    rendering = describe_api_error(ApiError(code, message="ctx", detail={"retry_after": 5}))
    assert isinstance(rendering.exit_code, ExitCode)
    assert not rendering.message.startswith("server error (")
    # describe is the shared half; the tuple wrapper agrees with it.
    assert format_api_error(ApiError(code, message="ctx")) == (
        describe_api_error(ApiError(code, message="ctx")).message,
        rendering.exit_code,
    )


def test_describe_matches_contract_message() -> None:
    rendering = describe_api_error(ApiError(ErrorCode.RATE_LIMITED, detail={"retry_after": 30}))
    assert rendering.message == "rate limited by the server; retry after 30s"
    assert rendering.exit_code == ExitCode.TRANSPORT


async def test_guard_maps_api_error_to_failed() -> None:
    async def boom() -> int:
        raise ApiError(ErrorCode.NOT_FOUND, message="gone")

    result = await guard(boom())
    assert result.state is LoadState.ERROR
    assert result.data is None
    assert isinstance(result.error, ErrorDisplay)
    assert result.error.code == "not_found"
    assert result.error.severity == "error"
    assert result.error.message == "not found: gone"


async def test_guard_returns_ready_on_success() -> None:
    async def ok() -> str:
        return "value"

    result = await guard(ok())
    assert result == Loadable.ready("value")
    assert result.state is LoadState.READY


@pytest.mark.parametrize(
    ("code", "severity"),
    [
        (ErrorCode.RATE_LIMITED, "warning"),
        (ErrorCode.PROVIDER_UNAVAILABLE, "warning"),
        (ErrorCode.NOT_FOUND, "error"),
        (ErrorCode.FORBIDDEN, "error"),
    ],
)
async def test_guard_severity_mapping(code: ErrorCode, severity: str) -> None:
    async def boom() -> int:
        raise ApiError(code, message="x", detail={"retry_after": 1, "provider": "p"})

    result = await guard(boom())
    assert result.error is not None
    assert result.error.severity == severity


async def test_guard_maps_transport_error_to_connection_display() -> None:
    async def boom() -> int:
        raise httpx.ConnectError("connection refused")

    result = await guard(boom())
    assert result.state is LoadState.ERROR
    assert result.error is not None
    assert result.error.code is None
    assert "couldn't reach the server" in result.error.message


async def test_guard_maps_oserror_to_connection_display() -> None:
    async def boom() -> int:
        raise OSError("network down")

    result = await guard(boom())
    assert result.error is not None
    assert result.error.code is None


async def test_guard_reraises_programming_errors() -> None:
    async def boom() -> int:
        raise ValueError("bug")

    with pytest.raises(ValueError, match="bug"):
        await guard(boom())
