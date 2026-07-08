"""Tests for the shared async HTTP plumbing (``http.py``).

All tests use ``respx`` to mock httpx transport and never touch the network.
Retry-heavy tests inject a no-op ``_sleep`` and use a low ``retries`` so the
suite stays fast.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import ProviderId
from spotdl_core.providers import (
    DEFAULT_USER_AGENT,
    EntityNotFound,
    ProviderAuthError,
    ProviderUnavailable,
    RateLimited,
    create_client,
    request_json,
)

URL = "https://api.example.test/resource"


async def _no_sleep(_seconds: float) -> None:
    """Async sleep replacement that returns immediately."""


@respx.mock
async def test_request_json_returns_body_on_200() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"hello": "world"}))
    async with create_client() as client:
        body = await request_json(client, "GET", URL, provider=ProviderId.DEEZER)
    assert body == {"hello": "world"}


@respx.mock
async def test_404_raises_entity_not_found() -> None:
    respx.get(URL).mock(return_value=httpx.Response(404, json={"error": "nope"}))
    async with create_client() as client:
        with pytest.raises(EntityNotFound) as excinfo:
            await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)
    assert excinfo.value.provider is ProviderId.SPOTIFY


@respx.mock
async def test_401_raises_provider_auth_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(401))
    async with create_client() as client:
        with pytest.raises(ProviderAuthError) as excinfo:
            await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)
    assert excinfo.value.provider is ProviderId.SPOTIFY


@respx.mock
async def test_403_raises_provider_auth_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(403))
    async with create_client() as client:
        with pytest.raises(ProviderAuthError):
            await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)


@respx.mock
async def test_429_then_200_succeeds() -> None:
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with create_client() as client:
        body = await request_json(client, "GET", URL, provider=ProviderId.DEEZER, _sleep=_no_sleep)
    assert body == {"ok": True}
    assert route.call_count == 2


@respx.mock
async def test_persistent_429_raises_rate_limited_with_retry_after() -> None:
    respx.get(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "2"}))
    async with create_client() as client:
        with pytest.raises(RateLimited) as excinfo:
            await request_json(
                client, "GET", URL, provider=ProviderId.DEEZER, retries=2, _sleep=_no_sleep
            )
    assert excinfo.value.provider is ProviderId.DEEZER
    assert excinfo.value.retry_after == 2.0


@respx.mock
async def test_persistent_500_raises_provider_unavailable() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(500))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable) as excinfo:
            await request_json(
                client, "GET", URL, provider=ProviderId.ITUNES, retries=2, _sleep=_no_sleep
            )
    assert excinfo.value.provider is ProviderId.ITUNES
    assert route.call_count == 2


@respx.mock
async def test_connect_error_raises_provider_unavailable() -> None:
    route = respx.get(URL).mock(side_effect=httpx.ConnectError("boom"))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable) as excinfo:
            await request_json(
                client, "GET", URL, provider=ProviderId.MUSICBRAINZ, retries=2, _sleep=_no_sleep
            )
    assert excinfo.value.provider is ProviderId.MUSICBRAINZ
    assert route.call_count == 2


@respx.mock
async def test_non_json_200_raises_provider_unavailable() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, text="<html>not json</html>"))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)


@respx.mock
async def test_expect_ok_body_can_raise_entity_not_found() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"error": {"code": 800}}))

    def _check(body: Any) -> None:
        if isinstance(body, dict) and "error" in body:
            raise EntityNotFound(provider=ProviderId.DEEZER)

    async with create_client() as client:
        with pytest.raises(EntityNotFound) as excinfo:
            await request_json(
                client, "GET", URL, provider=ProviderId.DEEZER, expect_ok_body=_check
            )
    assert excinfo.value.provider is ProviderId.DEEZER


@respx.mock
async def test_expect_ok_body_passes_through_on_valid_body() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"id": 42}))

    def _check(body: Any) -> None:
        if isinstance(body, dict) and "error" in body:
            raise EntityNotFound(provider=ProviderId.DEEZER)

    async with create_client() as client:
        body = await request_json(
            client, "GET", URL, provider=ProviderId.DEEZER, expect_ok_body=_check
        )
    assert body == {"id": 42}


@respx.mock
async def test_create_client_sets_user_agent() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={}))
    async with create_client() as client:
        await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)
    assert route.calls.last.request.headers["user-agent"] == DEFAULT_USER_AGENT


@respx.mock
async def test_create_client_custom_user_agent_and_headers() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json={}))
    async with create_client(user_agent="custom/1.0", headers={"X-Api-Key": "secret"}) as client:
        await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)
    request = route.calls.last.request
    assert request.headers["user-agent"] == "custom/1.0"
    assert request.headers["x-api-key"] == "secret"


@respx.mock
async def test_worst_case_attempt_count_equals_retries() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(503))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await request_json(
                client, "GET", URL, provider=ProviderId.PIPED, retries=3, _sleep=_no_sleep
            )
    assert route.call_count == 3


@respx.mock
async def test_unhandled_4xx_raises_provider_unavailable() -> None:
    respx.get(URL).mock(return_value=httpx.Response(400, json={"bad": "request"}))
    async with create_client() as client:
        with pytest.raises(ProviderUnavailable):
            await request_json(client, "GET", URL, provider=ProviderId.SPOTIFY)
