"""``CollectionViewModel`` — album/artist/playlist dispatch + enqueue."""

from __future__ import annotations

from uuid import uuid4

import pytest
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.collection import CollectionViewModel

from .fakes import (
    FakeSpotdlClient,
    make_album,
    make_artist,
    make_batch,
    make_playlist,
    make_session,
    make_source,
    make_sources,
    make_track,
)


async def test_load_album_dispatch() -> None:
    client = FakeSpotdlClient()
    album_id = uuid4()
    client.albums[str(album_id)] = make_album(
        id=album_id, name="Discovery", tracks=[make_track(name="a"), make_track(name="b")]
    )
    result = await CollectionViewModel(client, make_session()).load("album", album_id)

    assert result.state is LoadState.READY
    detail = result.data
    assert detail is not None
    assert detail.kind == "album"
    assert detail.header.title == "Discovery"
    assert [row.title for row in detail.tracks] == ["a", "b"]
    assert client.called("album")


async def test_load_artist_dispatch() -> None:
    client = FakeSpotdlClient()
    artist_id = uuid4()
    client.artists[str(artist_id)] = make_artist(id=artist_id, name="Daft Punk")
    result = await CollectionViewModel(client, make_session()).load("artist", artist_id)

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.kind == "artist"
    assert client.called("artist")


async def test_load_playlist_dispatch() -> None:
    client = FakeSpotdlClient()
    playlist_id = uuid4()
    client.playlists[str(playlist_id)] = make_playlist(id=playlist_id, name="Mix")
    result = await CollectionViewModel(client, make_session()).load("playlist", playlist_id)

    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.kind == "playlist"
    assert client.called("playlist")


async def test_load_unknown_type_fails_without_call() -> None:
    client = FakeSpotdlClient()
    result = await CollectionViewModel(client, make_session()).load("track", uuid4())
    assert result.state is LoadState.ERROR
    assert not (client.called("album") or client.called("artist") or client.called("playlist"))


async def test_enqueue_all_submits_collection_id() -> None:
    client = FakeSpotdlClient()
    album_id = uuid4()
    client.albums[str(album_id)] = make_album(id=album_id)
    batch_id = uuid4()
    client.submit_download_result = make_batch(batch_id=batch_id)
    vm = CollectionViewModel(client, make_session())
    await vm.load("album", album_id)

    result = await vm.enqueue_all()
    assert result.state is LoadState.READY
    assert result.data is not None
    assert result.data.batch_id == batch_id
    submit = next(c for c in client.calls if c[0] == "submit_download")
    assert submit[1][0].query == str(album_id)


async def test_enqueue_track_submits_track_id() -> None:
    client = FakeSpotdlClient()
    client.submit_download_result = make_batch()
    track_id = uuid4()
    vm = CollectionViewModel(client, make_session())

    result = await vm.enqueue_track(track_id)
    assert result.state is LoadState.READY
    submit = next(c for c in client.calls if c[0] == "submit_download")
    assert submit[1][0].query == str(track_id)


async def test_load_sources_maps_provider_rows() -> None:
    client = FakeSpotdlClient()
    artist_id = uuid4()
    client.sources_by_entity[str(artist_id)] = make_sources(
        entity_id=artist_id,
        entity_type="artist",
        sources=[
            make_source(provider="spotify", name="Daft Punk", followers=1_500_000, popularity=88),
            make_source(provider="deezer", name="Daft Punk", followers=900_000),
        ],
    )
    result = await CollectionViewModel(client, make_session()).load_sources("artist", artist_id)

    assert result.state is LoadState.READY
    rows = result.data
    assert rows is not None
    assert [row.provider for row in rows] == ["spotify", "deezer"]
    # followers formatted compactly; popularity present only where the source carries it
    assert dict(rows[0].metrics) == {"followers": "1.5M", "popularity": "88"}
    assert dict(rows[1].metrics) == {"followers": "900K"}
    assert client.called("sources")


async def test_load_sources_error_is_surfaced() -> None:
    client = FakeSpotdlClient()
    client.errors["sources"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    result = await CollectionViewModel(client, make_session()).load_sources("album", uuid4())
    assert result.state is LoadState.ERROR


@pytest.mark.parametrize("method", ["enqueue_all", "enqueue_track"])
async def test_enqueue_blocked_when_cannot_download(method: str) -> None:
    client = FakeSpotdlClient()
    album_id = uuid4()
    client.albums[str(album_id)] = make_album(id=album_id)
    vm = CollectionViewModel(client, make_session(can_download=False))
    await vm.load("album", album_id)

    result = await (vm.enqueue_all() if method == "enqueue_all" else vm.enqueue_track(uuid4()))
    assert result.state is LoadState.ERROR
    assert not client.called("submit_download")
