"""Pilot tests for the home / search screen (Plan 9 Task 5).

Runs headless through ``App.run_test()`` with a :class:`ViewModelFactory` over
:class:`FakeSpotdlClient`. The screen's contract (CONTRACT A/C): a query + Enter
runs ``SearchViewModel.search`` and fills the results table; selecting a row posts
``NavigateTo`` and the app pushes the entity screen; pasting a URL routes via
``SearchViewModel.open`` → ``resolve`` → the entity screen; a ``search`` error is a
toast with an empty table (no crash); and ``/`` focuses the input.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError
from spotdl_cli.tui.app import SpotdlApp
from spotdl_cli.tui.screens.home import HomeSearchScreen
from spotdl_cli.tui.widgets.nav_rail import NavRail
from spotdl_cli.viewmodels.factory import ViewModelFactory
from spotdl_cli.views import AlbumRefView, EntityView
from textual.widgets import DataTable, Input, Static

from .conftest import FakeConfigStore, FakeCredentialStore
from .fakes import FakeSpotdlClient, make_album, make_artist, make_playlist, make_track

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


async def test_query_enter_renders_result_rows() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.search_results = [
        make_track(
            id=track_id,
            name="One More Time",
            artists=["Daft Punk", "Romanthony"],
            duration_ms=185_000,
            album=AlbumRefView(id=str(uuid4()), name="Discovery"),
        )
    ]
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, HomeSearchScreen)
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("d", "a", "f", "t", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        table = app.screen.query_one("#search-results", DataTable)
        assert table.row_count == 1
        cells = [str(c) for c in table.get_row_at(0)]
        # Columns: # · Title · Artists · Duration · Source (CONTRACT §4).
        assert cells[0] == "1"
        assert cells[1] == "One More Time"
        assert cells[2] == "Daft Punk, Romanthony"
        assert cells[3] == "3:05"
        assert cells[4] == "—"  # search rows carry no source provider
        assert client.called("search")


async def test_row_selection_navigates_to_entity_screen() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.search_results = [make_track(id=track_id, name="Aerodynamic")]
    # Populate the track so the entity screen (once Task 6 registers it) loads clean.
    client.tracks[str(track_id)] = make_track(id=track_id, name="Aerodynamic")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("a", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        table = app.screen.query_one("#search-results", DataTable)
        table.focus()
        await pilot.press("enter")  # select the focused row
        await pilot.pause()

        assert len(app.screen_stack) == 2
        assert not isinstance(app.screen, HomeSearchScreen)


async def test_pasted_url_routes_through_open() -> None:
    client = FakeSpotdlClient()
    track_id = uuid4()
    client.resolve_result = EntityView(
        type="track", track=make_track(id=track_id, name="Around the World")
    )
    client.tracks[str(track_id)] = make_track(id=track_id, name="Around the World")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        search_input = app.screen.query_one("#search-input", Input)
        search_input.focus()
        search_input.value = "https://open.spotify.com/track/x"
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert client.called("resolve")
        assert not client.called("search")
        assert len(app.screen_stack) == 2
        assert not isinstance(app.screen, HomeSearchScreen)


async def test_search_error_toasts_and_leaves_table_empty() -> None:
    client = FakeSpotdlClient()
    client.errors["search"] = ApiError(ErrorCode.INTERNAL_ERROR, message="boom")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("x", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        table = app.screen.query_one("#search-results", DataTable)
        assert table.row_count == 0
        assert app._notifications  # the failure surfaced as a toast


async def test_degraded_search_surfaces_banner_and_yellow_dot() -> None:
    """§5 flow 5: a degraded search shows the in-panel banner + turns the nav dot yellow."""
    client = FakeSpotdlClient()
    client.search_results = [make_track(name="One More Time")]
    client.search_degraded = ["spotify"]
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("x", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        banner = app.screen.query_one("#degraded-banner", Static)
        assert "hidden" not in banner.classes
        assert "spotify" in str(banner.render())
        # The shell's nav-rail dot folds the session-degraded flag over transport.
        assert app.screen.query_one(NavRail).dot_state == "degraded"


def _universal_client() -> tuple[FakeSpotdlClient, dict[str, UUID]]:
    client = FakeSpotdlClient()
    album_id, artist_id, playlist_id = uuid4(), uuid4(), uuid4()
    client.search_results = [make_track(name="One More Time")]
    client.search_albums = [make_album(id=album_id, name="Discovery")]
    client.search_artists = [make_artist(id=artist_id, name="Daft Punk")]
    client.search_playlists = [make_playlist(id=playlist_id, name="Mix")]
    client.albums[str(album_id)] = make_album(id=album_id, name="Discovery")
    client.artists[str(artist_id)] = make_artist(id=artist_id, name="Daft Punk")
    client.playlists[str(playlist_id)] = make_playlist(id=playlist_id, name="Mix")
    return client, {"album": album_id, "artist": artist_id, "playlist": playlist_id}


async def _run_search(app: SpotdlApp, pilot: object) -> None:
    app.screen.query_one("#search-input", Input).focus()
    await pilot.press("d", "a", "f", "t", "enter")  # type: ignore[attr-defined]
    await app.workers.wait_for_complete()
    await pilot.pause()  # type: ignore[attr-defined]


async def test_universal_search_renders_four_sections_with_counts() -> None:
    client, _ = _universal_client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _run_search(app, pilot)

        for table_id in (
            "artists-results",
            "albums-results",
            "search-results",
            "playlists-results",
        ):
            assert app.screen.query_one(f"#{table_id}", DataTable).row_count == 1
        # Each visible section title carries its count.
        assert "Artists · 1" in str(app.screen.query_one("#artists-title", Static).render())
        assert "Songs · 1" in str(app.screen.query_one("#songs-title", Static).render())
        # The filter chips reflect the per-section counts.
        chips = str(app.screen.query_one("#filter-chips", Static).render())
        assert "Albums 1" in chips and "Playlists 1" in chips


async def test_filter_cycling_narrows_to_one_section() -> None:
    client, _ = _universal_client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _run_search(app, pilot)
        # all → artists: only the artists section stays visible.
        await pilot.press("f")
        await pilot.pause()
        assert "hidden" not in app.screen.query_one("#artists-results", DataTable).classes
        assert "hidden" in app.screen.query_one("#search-results", DataTable).classes
        assert "hidden" in app.screen.query_one("#albums-results", DataTable).classes


async def test_selecting_artist_hit_routes_to_collection_screen() -> None:
    client, ids = _universal_client()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        await _run_search(app, pilot)
        table = app.screen.query_one("#artists-results", DataTable)
        table.focus()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        from spotdl_cli.tui.screens.collection import ArtistScreen

        assert isinstance(app.screen, ArtistScreen)
        assert client.called("artist")


async def test_slash_focuses_the_search_input() -> None:
    client = FakeSpotdlClient()
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        table = app.screen.query_one("#search-results", DataTable)
        table.focus()
        await pilot.pause()
        assert app.focused is table
        await pilot.press("slash")
        await pilot.pause()
        assert app.focused is app.screen.query_one("#search-input", Input)


async def test_search_hit_resolves_provider_ref_before_opening() -> None:
    """A search hit is a snapshot preview, not a canonical entity. Selecting it
    must resolve `{provider}:track:{id}` → the canonical track id (which the track
    page loads), never navigate with the raw snapshot id (that 404s)."""
    client = FakeSpotdlClient()
    snapshot_id = uuid4()  # the search-row id (a provider snapshot)
    canonical_id = uuid4()  # what resolve returns
    client.search_results = [
        make_track(id=snapshot_id, name="KAMIKAZE", provider="deezer", provider_id="d123")
    ]
    client.resolve_result = EntityView(
        type="track", track=make_track(id=canonical_id, name="KAMIKAZE")
    )
    client.tracks[str(canonical_id)] = make_track(id=canonical_id, name="KAMIKAZE")
    app = SpotdlApp(_factory(client))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#search-input", Input).focus()
        await pilot.press("k", "enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        # Source column shows the provider now (was "—" before).
        table = app.screen.query_one("#search-results", DataTable)
        assert str(table.get_row_at(0)[4]) == "deezer"

        table.focus()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()

        # It resolved the provider ref (not a bare snapshot-id GET) and opened the track.
        assert client.called("resolve")
        resolve_calls = [c for c in client.calls if c[0] == "resolve"]
        assert resolve_calls[0][1] == ("deezer:track:d123",)
        assert len(app.screen_stack) == 2
        assert not isinstance(app.screen, HomeSearchScreen)
