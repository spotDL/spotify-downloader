"""``ConnectionViewModel`` — probe outcomes + target rewriting (Plan 9 redesign §3).

Offline, over the fake client + fake ``ConfigStore``: a reachable ``/config`` becomes
a populated :class:`ProbeResult`, an ``ApiError``/transport failure becomes an
unreachable result (never a raise), and each ``switch_*`` persists the new
``api_url``/``offline`` and hands back the primitives the app rebuilds from.
"""

from __future__ import annotations

import pytest
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.config import DEFAULT_API_URL, CliConfig
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.connection import ConnectionViewModel, validate_self_hosted

from .conftest import FakeConfigStore
from .fakes import FakeSpotdlClient, make_config, make_features

_ORIGIN = "https://api.example.test"


def _vm(client: FakeSpotdlClient, store: FakeConfigStore) -> ConnectionViewModel:
    return ConnectionViewModel(
        client, store, server_origin=_ORIGIN, transport_label="remote · api.example.test"
    )


async def test_probe_reachable_reports_mode_and_features() -> None:
    client = FakeSpotdlClient(
        config=make_config(mode="community", features=make_features(voting=False))
    )
    result = await _vm(client, FakeConfigStore()).probe()
    assert result.reachable is True
    assert result.mode == "community"
    assert result.voting is False
    assert result.latency_ms is not None and result.latency_ms >= 0


async def test_probe_api_error_is_unreachable_not_a_raise() -> None:
    client = FakeSpotdlClient()
    client.errors["config"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    result = await _vm(client, FakeConfigStore()).probe()
    assert result.reachable is False
    assert result.reason  # a human reason is carried for the connect screen


async def test_probe_transport_failure_is_unreachable() -> None:
    class _Dead(FakeSpotdlClient):
        async def config(self):  # type: ignore[override]
            raise ConnectionError("connection refused")

    result = await _vm(_Dead(), FakeConfigStore()).probe()
    assert result.reachable is False
    assert "connection refused" in (result.reason or "")


async def test_switch_community_resets_to_default_online() -> None:
    store = FakeConfigStore(CliConfig(api_url="https://self.example", offline=True))
    api_url, offline = _vm(FakeSpotdlClient(), store).switch_community()
    assert (api_url, offline) == (DEFAULT_API_URL, False)
    assert store.saves[-1].api_url == DEFAULT_API_URL
    assert store.saves[-1].offline is False


async def test_switch_self_hosted_persists_normalised_url() -> None:
    store = FakeConfigStore()
    api_url, offline = _vm(FakeSpotdlClient(), store).switch_self_hosted("https://host.example/  ")
    assert (api_url, offline) == ("https://host.example", False)
    assert store.saves[-1].api_url == "https://host.example"


async def test_switch_self_hosted_rejects_bad_url() -> None:
    store = FakeConfigStore()
    with pytest.raises(ValueError):
        _vm(FakeSpotdlClient(), store).switch_self_hosted("not-a-url")
    assert not store.saves  # nothing persisted on rejection


async def test_go_offline_keeps_url_and_sets_offline() -> None:
    store = FakeConfigStore(CliConfig(api_url="https://host.example", offline=False))
    api_url, offline = _vm(FakeSpotdlClient(), store).go_offline()
    assert (api_url, offline) == ("https://host.example", True)
    assert store.saves[-1].offline is True


def test_validate_self_hosted() -> None:
    assert validate_self_hosted("https://ok.example") is None
    assert validate_self_hosted("http://ok.example:8000") is None
    assert validate_self_hosted("") == "enter a server URL"
    assert validate_self_hosted("ftp://x") == "URL must start with http:// or https://"
    assert validate_self_hosted("https://") == "URL is missing a host"
