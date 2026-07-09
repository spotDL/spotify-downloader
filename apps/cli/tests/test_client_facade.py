"""``SpotdlClient`` over a ``RemoteTransport`` — typed ``*View`` results + errors.

Uses respx to stub the HTTP surface (no network). Confirms the façade maps the
generated success models to hand-written Views, and a non-2xx ``ErrorEnvelope``
into a typed :class:`ApiError` carrying the code + HTTP status.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest
import respx
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.client import RemoteTransport, SpotdlClient
from spotdl_cli.errors import ApiError
from spotdl_cli.views import ConfigView, EntityView, TrackView

BASE = "https://api.test"
TRACK_ID = UUID("11111111-1111-1111-1111-111111111111")

TRACK_JSON = {
    "artists": ["Daft Punk"],
    "duration_ms": 224_000,
    "id": "sp:1",
    "name": "One More Time",
}
CONFIG_JSON = {
    "features": {"auth": False, "downloads": True, "library": True, "voting": False},
    "matcher_version": "1.2.3",
    "mode": "embedded",
    "oauth_providers": [],
}


@pytest.fixture
async def client() -> AsyncIterator[SpotdlClient]:
    transport = RemoteTransport(BASE)
    try:
        yield SpotdlClient(resolution=transport, downloads=transport)
    finally:
        await transport.aclose()


async def test_config_returns_typed_view(client: SpotdlClient) -> None:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/config").mock(return_value=httpx.Response(200, json=CONFIG_JSON))
        view = await client.config()

    assert isinstance(view, ConfigView)
    assert view.mode == "embedded"
    assert view.matcher_version == "1.2.3"
    assert view.features.downloads is True
    assert view.features.auth is False


async def test_resolve_returns_tagged_entity(client: SpotdlClient) -> None:
    body = {"degraded_sources": ["genius"], "entity": {"type": "track", "track": TRACK_JSON}}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.post("/api/v1/resolve").mock(return_value=httpx.Response(200, json=body))
        view = await client.resolve("One More Time")

    assert isinstance(view, EntityView)
    assert view.type == "track"
    assert view.degraded_sources == ["genius"]
    assert view.track is not None
    assert view.track.name == "One More Time"
    assert view.track.artists == ["Daft Punk"]


async def test_search_returns_track_views(client: SpotdlClient) -> None:
    body = {"degraded_sources": [], "results": [TRACK_JSON]}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        route = router.get("/api/v1/search").mock(return_value=httpx.Response(200, json=body))
        results = await client.search("daft punk", limit=5)

    assert route.called
    assert route.calls.last.request.url.params["limit"] == "5"
    assert [type(r) for r in results] == [TrackView]
    assert results[0].name == "One More Time"


async def test_404_envelope_becomes_api_error(client: SpotdlClient) -> None:
    envelope = {"code": "not_found", "message": "no such track"}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get(f"/api/v1/tracks/{TRACK_ID}").mock(
            return_value=httpx.Response(404, json=envelope)
        )
        with pytest.raises(ApiError) as excinfo:
            await client.track(TRACK_ID)

    err = excinfo.value
    assert err.code is ErrorCode.NOT_FOUND
    assert err.status == 404
    assert err.message == "no such track"


async def test_token_is_sent_per_request_not_persisted(client: SpotdlClient) -> None:
    """An authenticated call carries the Bearer header, but never persists it.

    The transport's shared httpx client serves both authenticated and anonymous
    calls; mutating its default headers would leak the token onto every later
    request. So the header must ride the authenticated request only, and the
    shared client's defaults must stay clean.
    """
    user = {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "a@b.c",
        "is_admin": False,
        "created_at": "2020-01-01T00:00:00+00:00",
    }
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        me = router.get("/api/v1/auth/me").mock(return_value=httpx.Response(200, json=user))
        cfg = router.get("/api/v1/config").mock(return_value=httpx.Response(200, json=CONFIG_JSON))

        await client.me(token="secret-pat")
        assert me.calls.last.request.headers["Authorization"] == "Bearer secret-pat"

        # A later anonymous call on the same transport must not inherit the token.
        await client.config()
        assert "Authorization" not in cfg.calls.last.request.headers

    # The shared client's default headers were never mutated.
    assert "Authorization" not in client._resolution.http_client().headers


async def test_config_error_body_without_documented_schema(client: SpotdlClient) -> None:
    """GET /config only documents 200; an error body is still surfaced as ApiError."""
    envelope = {"code": "internal_error", "message": "boom"}
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("/api/v1/config").mock(return_value=httpx.Response(500, json=envelope))
        with pytest.raises(ApiError) as excinfo:
            await client.config()

    assert excinfo.value.code is ErrorCode.INTERNAL_ERROR
    assert excinfo.value.status == 500
