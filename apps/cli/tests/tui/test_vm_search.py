"""``SearchViewModel`` — row mapping, warning errors, resolve → ``EntityRef``."""

from __future__ import annotations

from uuid import uuid4

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.search import SearchViewModel
from spotdl_cli.views import AlbumRefView, EntityView

from .fakes import FakeSpotdlClient, make_album, make_artist, make_playlist, make_track


async def test_search_maps_all_universal_sections() -> None:
    """A universal search maps every group (tracks/albums/artists/playlists) → hits."""
    client = FakeSpotdlClient()
    album_id, artist_id, playlist_id = uuid4(), uuid4(), uuid4()
    client.search_results = [make_track(name="One More Time")]
    client.search_albums = [make_album(id=album_id, name="Discovery")]
    client.search_artists = [make_artist(id=artist_id, name="Daft Punk")]
    client.search_playlists = [make_playlist(id=playlist_id, name="Mix")]
    result = await SearchViewModel(client).search("daft")

    assert result.state is LoadState.READY
    data = result.data
    assert data is not None
    assert [row.title for row in data.rows] == ["One More Time"]
    ((album,), (artist,), (playlist,)) = (data.albums, data.artists, data.playlists)
    # A hit's id is the table row key (a str); resolve-on-open uses provider/provider_id.
    assert (album.entity_type, album.id, album.title) == ("album", str(album_id), "Discovery")
    assert (artist.entity_type, artist.id) == ("artist", str(artist_id))
    assert artist.detail == "1.5M followers"  # followers formatted K/M/B
    assert (playlist.entity_type, playlist.id, playlist.title) == (
        "playlist",
        str(playlist_id),
        "Mix",
    )
    assert data.total == 4


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
    assert result.data.degraded is False
    (row,) = result.data.rows
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
    assert result.data.degraded is False
    assert result.data.ref.entity_type == "track"
    assert result.data.ref.id == track_id
    assert result.data.ref.title == "Around the World"


async def test_search_flags_degraded_sources() -> None:
    client = FakeSpotdlClient()
    client.search_results = [make_track()]
    client.search_degraded = ["genius"]
    result = await SearchViewModel(client).search("daft")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.degraded is True


async def test_open_flags_degraded_sources() -> None:
    client = FakeSpotdlClient()
    client.resolve_result = EntityView(
        type="track", track=make_track(), degraded_sources=["musicbrainz"]
    )
    result = await SearchViewModel(client).open("https://open.spotify.com/track/x")

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.degraded is True


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
