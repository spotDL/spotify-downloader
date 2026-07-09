"""``SearchViewModel`` — row mapping, warning errors, resolve → ``EntityRef``."""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.search import SearchViewModel
from spotdl_cli.views import AlbumRefView, EntityView

from .fakes import FakeSpotdlClient, make_track


async def test_search_maps_track_rows() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.search_results = [
        make_track(
            id=track_id,
            name="One More Time",
            artists=["Daft Punk", "Romanthony"],
            duration_ms=185_000,
            explicit=True,
            album=AlbumRefView(id=str(uuid4()), name="Discovery"),
        )
    ]
    result = await SearchViewModel(client).search("daft", limit=5)

    assert result.state is LoadState.READY
    assert result.data is not None
    (row,) = result.data
    assert row.id == track_id
    assert row.title == "One More Time"
    assert row.artists == "Daft Punk, Romanthony"
    assert row.album == "Discovery"
    assert row.duration == "3:05"
    assert row.explicit is True
    # the search limit is forwarded to the client
    assert client.calls[-1] == ("search", ("daft",), {"limit": 5})


async def test_search_rate_limited_is_warning() -> None:
    client = FakeSpotdlClient()
    client.errors["search"] = ApiError(ErrorCode.RATE_LIMITED, detail={"retry_after": 5})
    result = await SearchViewModel(client).search("x")

    assert result.state is LoadState.ERROR
    assert result.error is not None
    assert result.error.severity == "warning"
    assert result.error.code == "rate_limited"


async def test_open_resolves_to_entity_ref() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.resolve_result = EntityView(
        type="track", track=make_track(id=track_id, name="Around the World")
    )
    result = await SearchViewModel(client).open("https://open.spotify.com/track/x")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.entity_type == "track"
    assert result.data.id == track_id
    assert result.data.title == "Around the World"


async def test_open_unresolvable_entity_fails() -> None:
    client = FakeSpotdlClient()
    client.resolve_result = EntityView(type="track")  # no populated payload
    result = await SearchViewModel(client).open("mystery")

    assert result.state is LoadState.ERROR
    assert result.error is not None
    assert result.error.code is None


async def test_open_propagates_api_error() -> None:
    client = FakeSpotdlClient()
    client.errors["resolve"] = ApiError(ErrorCode.UNSUPPORTED_URL, message="nope")
    result = await SearchViewModel(client).open("bad")

    assert result.state is LoadState.ERROR
    assert result.error is not None
    assert result.error.code == "unsupported_url"
