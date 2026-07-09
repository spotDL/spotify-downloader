"""CONTRACT C — connectivity policy, ``--offline``, embedded fallback, warning copy.

Uses respx to stub the remote ``GET /api/v1/health`` probe (no network). Fake
embedded/remote transports stand in for the sibling ``EmbeddedTransport`` so the
selection policy — and ``SpotdlClient.from_config``'s use of it — is exercised in
isolation. The warning/error copy strings are a CONTRACT and pinned verbatim here.
"""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
import respx
from httpx_ws import AsyncWebSocketSession
from rich.console import Console
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.client import DEFAULT_API_URL, RemoteTransport, SpotdlClient
from spotdl_cli.errors import ApiError, ExitCode
from spotdl_cli.fallback import (
    FALLBACK_WARNING,
    OFFLINE_AUTH_ERROR,
    UNREACHABLE_AUTH_ERROR,
    RemoteRequiredError,
    probe_remote,
    select_resolution_transport,
)

BASE = "https://api.test"


# --- fakes -------------------------------------------------------------------


class FakeTransport:
    """A minimal :class:`Transport` stand-in (no real client)."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.closed = False

    @property
    def http_base(self) -> str:
        return f"http://{self.label}"

    @property
    def ws_base(self) -> str:
        return f"ws://{self.label}"

    def http_client(self) -> httpx.AsyncClient:  # pragma: no cover - unused by policy
        raise AssertionError("fake embedded transport has no http_client in these tests")

    @asynccontextmanager
    async def ws_connect(
        self, path: str
    ) -> AsyncIterator[AsyncWebSocketSession]:  # pragma: no cover
        raise AssertionError("unused")
        yield  # type: ignore[unreachable]

    async def aclose(self) -> None:
        self.closed = True


def _capture_console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, width=10_000, highlight=False, soft_wrap=True), buf


# --- DEFAULT_API_URL (CONTRACT B) --------------------------------------------


def test_default_api_url_is_the_pinned_community_server() -> None:
    # Binding (Plan 8 Task 5 handoff): api.spotdl.dev. NEVER a localhost stub.
    assert DEFAULT_API_URL == "https://api.spotdl.dev"
    assert "localhost" not in DEFAULT_API_URL
    assert "127.0.0.1" not in DEFAULT_API_URL


# --- probe_remote ------------------------------------------------------------


async def test_probe_returns_none_when_reachable() -> None:
    transport = RemoteTransport(BASE)
    try:
        with respx.mock(base_url=BASE, assert_all_called=True) as router:
            router.get("/api/v1/health").mock(
                return_value=httpx.Response(200, json={"status": "ok"})
            )
            reason = await probe_remote(transport.http_client())
        assert reason is None
    finally:
        await transport.aclose()


async def test_probe_treats_non_401_4xx_as_reachable() -> None:
    transport = RemoteTransport(BASE)
    try:
        with respx.mock(base_url=BASE, assert_all_called=True) as router:
            router.get("/api/v1/health").mock(return_value=httpx.Response(404))
            reason = await probe_remote(transport.http_client())
        assert reason is None
    finally:
        await transport.aclose()


async def test_probe_reports_5xx_as_unreachable() -> None:
    transport = RemoteTransport(BASE)
    try:
        with respx.mock(base_url=BASE, assert_all_called=True) as router:
            router.get("/api/v1/health").mock(return_value=httpx.Response(503))
            reason = await probe_remote(transport.http_client())
        assert reason is not None
        assert "503" in reason
    finally:
        await transport.aclose()


async def test_probe_reports_connection_error_reason() -> None:
    transport = RemoteTransport(BASE)
    try:
        with respx.mock(base_url=BASE, assert_all_called=True) as router:
            router.get("/api/v1/health").mock(
                side_effect=httpx.ConnectError("name resolution failed")
            )
            reason = await probe_remote(transport.http_client())
        assert reason == "name resolution failed"
    finally:
        await transport.aclose()


# --- select_resolution_transport (the CONTRACT C policy) ---------------------


async def test_reachable_remote_is_used_without_warning() -> None:
    remote = RemoteTransport(BASE)
    embedded = FakeTransport("embedded")
    console, buf = _capture_console()
    with respx.mock(base_url=BASE, assert_all_called=True) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(200))
        chosen = await select_resolution_transport(
            offline=False,
            api_url=BASE,
            require_remote=False,
            make_remote=lambda: remote,
            make_embedded=lambda: embedded,
            console=console,
        )
    assert chosen is remote
    assert buf.getvalue() == ""
    assert embedded.closed is False
    await remote.aclose()


async def test_unreachable_remote_falls_back_to_embedded_with_exact_warning() -> None:
    remote = RemoteTransport(BASE)
    embedded = FakeTransport("embedded")
    console, buf = _capture_console()
    with respx.mock(base_url=BASE, assert_all_called=True) as router:
        router.get("/api/v1/health").mock(side_effect=httpx.ConnectError("connection refused"))
        chosen = await select_resolution_transport(
            offline=False,
            api_url=BASE,
            require_remote=False,
            make_remote=lambda: remote,
            make_embedded=lambda: embedded,
            console=console,
        )
    assert chosen is embedded
    expected = FALLBACK_WARNING.format(api_url=BASE, reason="connection refused")
    assert buf.getvalue().strip() == expected
    # The rejected remote transport is closed before falling back.
    assert remote.http_client().is_closed


async def test_5xx_probe_falls_back_to_embedded() -> None:
    remote = RemoteTransport(BASE)
    embedded = FakeTransport("embedded")
    console, buf = _capture_console()
    with respx.mock(base_url=BASE, assert_all_called=True) as router:
        router.get("/api/v1/health").mock(return_value=httpx.Response(502))
        chosen = await select_resolution_transport(
            offline=False,
            api_url=BASE,
            require_remote=False,
            make_remote=lambda: remote,
            make_embedded=lambda: embedded,
            console=console,
        )
    assert chosen is embedded
    assert "using the offline embedded server" in buf.getvalue()


async def test_offline_uses_embedded_with_no_probe_and_no_warning() -> None:
    embedded = FakeTransport("embedded")
    make_remote = Mock(side_effect=AssertionError("offline must not build a remote transport"))
    console, buf = _capture_console()
    chosen = await select_resolution_transport(
        offline=True,
        api_url=BASE,
        require_remote=False,
        make_remote=make_remote,
        make_embedded=lambda: embedded,
        console=console,
    )
    assert chosen is embedded
    assert buf.getvalue() == ""
    make_remote.assert_not_called()


# --- require_remote (CONTRACT C rule 5) --------------------------------------


async def test_require_remote_with_offline_raises_usage_error() -> None:
    make_remote = Mock(side_effect=AssertionError("must not probe"))
    make_embedded = Mock(side_effect=AssertionError("auth never falls back to embedded"))
    with pytest.raises(RemoteRequiredError) as excinfo:
        await select_resolution_transport(
            offline=True,
            api_url=BASE,
            require_remote=True,
            make_remote=make_remote,
            make_embedded=make_embedded,
        )
    assert excinfo.value.message == OFFLINE_AUTH_ERROR
    assert excinfo.value.exit_code is ExitCode.USAGE
    make_embedded.assert_not_called()


async def test_require_remote_when_unreachable_raises_transport_error() -> None:
    remote = RemoteTransport(BASE)
    make_embedded = Mock(side_effect=AssertionError("auth never falls back to embedded"))
    with respx.mock(base_url=BASE, assert_all_called=True) as router:
        router.get("/api/v1/health").mock(side_effect=httpx.ConnectError("no route to host"))
        with pytest.raises(RemoteRequiredError) as excinfo:
            await select_resolution_transport(
                offline=False,
                api_url=BASE,
                require_remote=True,
                make_remote=lambda: remote,
                make_embedded=make_embedded,
            )
    assert excinfo.value.message == UNREACHABLE_AUTH_ERROR.format(
        api_url=BASE, reason="no route to host"
    )
    assert excinfo.value.exit_code is ExitCode.TRANSPORT
    make_embedded.assert_not_called()
    assert remote.http_client().is_closed


# --- 401 on an authed call is an ApiError, NOT a fallback --------------------


async def test_401_on_authed_call_raises_api_error_no_fallback() -> None:
    transport = RemoteTransport(BASE, token="spdl_pat_x")
    client = SpotdlClient(resolution=transport, downloads=transport)
    envelope = {"code": "authentication_required", "message": "log in"}
    try:
        with respx.mock(base_url=BASE, assert_all_called=True) as router:
            router.get("/api/v1/auth/me").mock(return_value=httpx.Response(401, json=envelope))
            with pytest.raises(ApiError) as excinfo:
                await client.me(token="spdl_pat_x")
        assert excinfo.value.code is ErrorCode.AUTHENTICATION_REQUIRED
        assert excinfo.value.status == 401
    finally:
        await transport.aclose()


# --- PAT header injection (HTTP + WS handshake) ------------------------------


def test_remote_transport_injects_bearer_pat_on_http_client() -> None:
    transport = RemoteTransport(BASE, token="spdl_pat_abc")
    assert transport.http_client().headers["Authorization"] == "Bearer spdl_pat_abc"


def test_remote_transport_no_auth_header_without_token() -> None:
    transport = RemoteTransport(BASE)
    assert "Authorization" not in transport.http_client().headers


async def test_ws_connect_uses_wss_and_authed_client(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = RemoteTransport(BASE, token="spdl_pat_ws")
    captured: dict[str, Any] = {}
    sentinel = object()

    @asynccontextmanager
    async def fake_aconnect_ws(
        url: str, client: httpx.AsyncClient, **kwargs: Any
    ) -> AsyncIterator[Any]:
        captured["url"] = url
        captured["client"] = client
        yield sentinel

    monkeypatch.setattr("spotdl_cli.transport.aconnect_ws", fake_aconnect_ws)
    async with transport.ws_connect("/ws/progress") as session:
        assert session is sentinel
    assert captured["url"] == "wss://api.test/ws/progress"
    # The PAT rides the WS handshake via the transport's httpx client headers.
    assert captured["client"] is transport.http_client()
    assert captured["client"].headers["Authorization"] == "Bearer spdl_pat_ws"
    await transport.aclose()


# --- from_config wiring (delegates to the policy) ----------------------------


@respx.mock(base_url=BASE, assert_all_called=True)
async def test_from_config_falls_back_to_embedded_when_unreachable(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("/api/v1/health").mock(side_effect=httpx.ConnectError("down"))
    embedded = FakeTransport("embedded")
    cfg = _FakeConfig(api_url=BASE, offline=False)
    async with SpotdlClient.from_config(
        cfg, _embedded_factory=lambda enable_downloads: embedded
    ) as client:
        assert client._resolution is embedded  # resolution fell back to embedded
        assert client._downloads is embedded  # downloads are ALWAYS embedded
    assert embedded.closed is True


@respx.mock(base_url=BASE, assert_all_called=True)
async def test_from_config_uses_remote_when_reachable(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("/api/v1/health").mock(return_value=httpx.Response(200))
    embedded = FakeTransport("embedded")
    cfg = _FakeConfig(api_url=BASE, offline=False)
    async with SpotdlClient.from_config(
        cfg, _embedded_factory=lambda enable_downloads: embedded
    ) as client:
        assert isinstance(client._resolution, RemoteTransport)
        assert client._resolution.http_base == BASE
        assert client._downloads is embedded  # downloads still embedded
    assert embedded.closed is True


async def test_from_config_offline_skips_probe() -> None:
    embedded = FakeTransport("embedded")
    cfg = _FakeConfig(api_url=BASE, offline=True)
    # No respx mock installed: any network probe would raise, proving none happens.
    async with SpotdlClient.from_config(
        cfg, _embedded_factory=lambda enable_downloads: embedded
    ) as client:
        assert client._resolution is embedded
    assert embedded.closed is True


class _FakeConfig:
    """Duck-typed stand-in for the sibling ``CliConfig`` (Task 3)."""

    def __init__(self, *, api_url: str, offline: bool) -> None:
        self.api_url = api_url
        self.offline = offline
