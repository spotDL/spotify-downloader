"""Pilot tests for the album/artist/playlist ``CollectionScreen`` (Plan 9 Task 7).

Everything runs headless through ``App.run_test()`` over :class:`FakeSpotdlClient`.
The screen's contract: load a collection through ``CollectionViewModel``, render an
:class:`EntityCard` + a track ``DataTable`` (CONTRACT C); ``e`` enqueues the whole
collection with a ``queued N`` toast; ``d`` enqueues the focused track; ``Enter``
drills into that track's screen; and the enqueue bindings vanish when the session
can't download (CONTRACT F).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.messages import NavigateTo
from spotdl_cli.tui.screens.collection import AlbumScreen, ArtistScreen, PlaylistScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.viewmodels.factory import ViewModelFactory
from spotdl_cli.viewmodels.types import EntityRef
from textual.widgets import DataTable

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import (
    FakeSpotdlClient,
    make_album,
    make_artist,
    make_batch,
    make_config,
    make_features,
    make_job,
    make_playlist,
    make_track,
)

_ORIGIN = "https://api.example.test"
_TRANSPORT = "remote · api.example.test"


def _factory(client: FakeSpotdlClient) -> ViewModelFactory:
    return ViewModelFactory(
        client,
        FakeCredentialStore(),
        FakeConfigStore(),
        server_origin=_ORIGIN,
        transport_label=_TRANSPORT,
    )


def _album_client(*, downloads: bool = True) -> tuple[FakeSpotdlClient, UUID, list[UUID]]:
    config = make_config(features=make_features(downloads=downloads))
    client = FakeSpotdlClient(config=config, download_config=config)
    track_ids = [uuid4(), uuid4(), uuid4()]
    tracks = [make_track(id=tid, name=f"Track {i}") for i, tid in enumerate(track_ids, 1)]
    for track in tracks:
        client.tracks[str(track.id)] = track
    album_id = uuid4()
    client.albums[str(album_id)] = make_album(id=album_id, name="Discovery", tracks=tracks)
    return client, album_id, track_ids


async def _open_album(app: SpotdlApp, album_id: UUID, pilot: object) -> None:
    app.post_message(NavigateTo(EntityRef(entity_type="album", id=album_id, title="Discovery")))
    await pilot.pause()  # type: ignore[attr-defined]
    await pilot.pause()  # type: ignore[attr-defined]


async def test_album_renders_entity_card_and_track_table() -> None:
    client, album_id, track_ids = _album_client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_album(app, album_id, pilot)
        assert isinstance(app.screen, AlbumScreen)
        card = app.screen.query_one(EntityCard)
        assert "Discovery" in card.summary
        table = app.screen.query_one(DataTable)
        assert table.row_count == len(track_ids)


async def test_e_enqueues_all_and_toasts_count() -> None:
    client, album_id, track_ids = _album_client()
    jobs = [make_job() for _ in track_ids]
    client.submit_download_result = make_batch(jobs=jobs)
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_album(app, album_id, pilot)
        await pilot.press("e")
        await pilot.pause()
        assert client.called("submit_download")
        submitted = next(call for call in client.calls if call[0] == "submit_download")
        assert str(album_id) in str(submitted[1][0])  # enqueue_all submits the collection id
        toasts = [n.message for n in app._notifications]
        assert f"queued {len(jobs)}" in toasts


async def test_d_enqueues_focused_track() -> None:
    client, album_id, track_ids = _album_client()
    client.submit_download_result = make_batch(jobs=[make_job()])
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_album(app, album_id, pilot)
        table = app.screen.query_one(DataTable)
        table.move_cursor(row=1)
        await pilot.press("d")
        await pilot.pause()
        submitted = next(call for call in client.calls if call[0] == "submit_download")
        assert str(track_ids[1]) in str(submitted[1][0])  # the focused track, not the album
        assert "queued 1" in [n.message for n in app._notifications]


async def test_enter_drills_into_track_screen() -> None:
    client, album_id, track_ids = _album_client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_album(app, album_id, pilot)
        table = app.screen.query_one(DataTable)
        table.move_cursor(row=0)
        await pilot.press("enter")
        await pilot.pause()
        # Drilling in pushes the real TrackScreen (registered by Task 6).
        from spotdl_cli.tui.screens.track import TrackScreen

        assert isinstance(app.screen, TrackScreen)
        assert len(app.screen_stack) == 3  # section + album + track


async def test_enqueue_bindings_absent_when_downloads_disabled() -> None:
    client, album_id, _ = _album_client(downloads=False)
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _open_album(app, album_id, pilot)
        assert app.screen.check_action("enqueue_all", ()) is None
        assert app.screen.check_action("enqueue_track", ()) is None
        await pilot.press("e")
        await pilot.pause()
        assert not client.called("submit_download")


async def test_artist_and_playlist_reuse_the_base() -> None:
    config = make_config(features=make_features(downloads=True))
    client = FakeSpotdlClient(config=config, download_config=config)
    artist_id, playlist_id = uuid4(), uuid4()
    client.artists[str(artist_id)] = make_artist(id=artist_id, name="Daft Punk")
    client.playlists[str(playlist_id)] = make_playlist(id=playlist_id, name="Mix")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.post_message(
            NavigateTo(EntityRef(entity_type="artist", id=artist_id, title="Daft Punk"))
        )
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, ArtistScreen)
        assert "Daft Punk" in app.screen.query_one(EntityCard).summary
        app.post_message(NavigateTo(EntityRef(entity_type="playlist", id=playlist_id, title="Mix")))
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, PlaylistScreen)
        assert "Mix" in app.screen.query_one(EntityCard).summary
