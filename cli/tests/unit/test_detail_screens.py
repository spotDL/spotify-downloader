"""Tests for detail screens: TrackScreen, AlbumScreen, ArtistScreen, PlaylistScreen."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from textual.app import App
from textual.widgets import DataTable, Static
from textual.containers import Horizontal

from spotdl_cli.screens.track import TrackScreen
from spotdl_cli.screens.album import AlbumScreen
from spotdl_cli.screens.artist import ArtistScreen
from spotdl_cli.screens.playlist import PlaylistScreen
from spotdl_cli.core.types import Platform, Song


@pytest.fixture
def sample_song():
    """Create a sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Test Artist", "Featured Artist"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="test123",
        url="https://open.spotify.com/track/test123",
        album_name="Test Album",
        album_artist="Test Artist",
        genres=["Pop", "Rock"],
        year=2024,
        date="2024-01-15",
        track_number=1,
        disc_number=1,
        isrc="USABC1234567",
        cover_url="https://example.com/cover.jpg",
        explicit=False,
    )


@pytest.fixture
def explicit_song():
    """Create an explicit song for testing."""
    return Song(
        name="Explicit Song",
        artists=["Artist"],
        artist="Artist",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="explicit123",
        url="https://open.spotify.com/track/explicit123",
        genres=["Hip-Hop", "Rap", "Trap", "R&B", "Soul"],
        explicit=True,
    )


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.api_url = "http://localhost:8000"
    settings.offline_mode = False
    settings.auth_token = None
    settings.api_timeout = 30.0
    settings.audio_providers = []
    return settings


@pytest.fixture
def mock_spotdl_app():
    """Create a mock SpotDLApp."""
    app = MagicMock()
    app.is_online = True
    app.download_queue = AsyncMock()
    app.download_queue.add = AsyncMock()
    return app


def _make_test_app(screen_factory):
    """Create a TestApp that patches singletons before composing the screen."""

    class TestApp(App):
        def compose(self):
            yield screen_factory()

    return TestApp


# ── TrackScreen ──────────────────────────────────────────────────────────────


class TestTrackScreen:
    """Tests for TrackScreen."""

    def test_initialization(self, sample_song, mock_settings):
        """Test TrackScreen constructor sets expected attributes."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(sample_song, track_id="tid", platform="deezer")

        assert screen._song is sample_song
        assert screen._track_id == "tid"
        assert screen._platform == "deezer"

    def test_initialization_defaults(self, sample_song, mock_settings):
        """Test TrackScreen defaults track_id to song.platform_id."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(sample_song)

        assert screen._track_id == sample_song.platform_id
        assert screen._platform == "spotify"

    @pytest.mark.asyncio
    async def test_compose_layout(self, sample_song, mock_settings):
        """Test TrackScreen compose creates proper layout."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#track-container") is not None
                assert pilot.app.query_one("#matches-table", DataTable) is not None
                assert pilot.app.query_one("#track-title", Static) is not None

    @pytest.mark.asyncio
    async def test_update_song_display(self, sample_song, mock_settings):
        """Test display is populated from song data."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)
                screen._update_song_display()
                await pilot.pause()

                title = pilot.app.query_one("#track-title", Static)
                assert "Test Song" in str(title.content)

    @pytest.mark.asyncio
    async def test_genre_badges_cleared_on_update(self, sample_song, mock_settings):
        """Regression: genre badges should not accumulate on repeated calls."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                # Call twice – badges should NOT double
                screen._update_song_display()
                await pilot.pause()
                screen._update_song_display()
                await pilot.pause()

                genres_container = pilot.app.query_one("#track-genres", Horizontal)
                # sample_song has 2 genres
                assert len(genres_container.children) == 2

    @pytest.mark.asyncio
    async def test_genre_badges_limit_4(self, explicit_song, mock_settings):
        """Genres are capped at 4 badges."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(explicit_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)
                screen._update_song_display()
                await pilot.pause()

                genres_container = pilot.app.query_one("#track-genres", Horizontal)
                assert len(genres_container.children) <= 4

    @pytest.mark.asyncio
    async def test_explicit_badge_shown(self, explicit_song, mock_settings):
        """Explicit flag shows badge."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(explicit_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)
                screen._update_song_display()
                await pilot.pause()

                badge = pilot.app.query_one("#explicit-badge", Static)
                assert not badge.has_class("hidden")

    @pytest.mark.asyncio
    async def test_explicit_badge_hidden(self, sample_song, mock_settings):
        """Non-explicit song hides explicit badge."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                badge = pilot.app.query_one("#explicit-badge", Static)
                assert badge.has_class("hidden")

    @pytest.mark.asyncio
    async def test_load_track_data_online(self, sample_song, mock_settings, mock_spotdl_app):
        """Verify _load_online_data called when online."""
        mock_spotdl_app.is_online = True
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(
                TrackScreen, "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
            ),
            patch.object(TrackScreen, "_load_online_data", new_callable=AsyncMock) as mock_online,
            patch.object(TrackScreen, "_load_offline_data", new_callable=AsyncMock) as mock_offline,
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                # on_mount called _load_track_data, which should call _load_online_data
                mock_online.assert_called()
                mock_offline.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_track_data_offline(self, sample_song, mock_settings, mock_spotdl_app):
        """Verify _load_offline_data called when offline."""
        mock_spotdl_app.is_online = False
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(
                TrackScreen, "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
            ),
            patch.object(TrackScreen, "_load_online_data", new_callable=AsyncMock) as mock_online,
            patch.object(TrackScreen, "_load_offline_data", new_callable=AsyncMock) as mock_offline,
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                mock_offline.assert_called()
                mock_online.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_track_data_force_refresh(self, sample_song, mock_settings, mock_spotdl_app):
        """Verify use_cache=False when force_refresh=True."""
        mock_spotdl_app.is_online = True
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(
                TrackScreen, "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
            ),
            patch.object(TrackScreen, "_load_online_data", new_callable=AsyncMock) as mock_online,
            patch.object(TrackScreen, "_load_offline_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)
                # Reset the mock to clear on_mount call
                mock_online.reset_mock()
                await screen._load_track_data(force_refresh=True)
                mock_online.assert_called_once_with(use_cache=False)

    @pytest.mark.asyncio
    async def test_inline_submit_match_correct_params(self, sample_song, mock_settings, mock_spotdl_app):
        """Regression: submit_match called with source_url, target_url, fallback_song."""
        mock_api = AsyncMock()
        mock_api.submit_match = AsyncMock(return_value=MagicMock(id=None))

        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                with patch.object(
                    type(screen), "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
                ):
                    mock_spotdl_app.is_online = True
                    mock_settings.auth_token = "test-token"
                    with patch.object(
                        screen, "_ensure_authenticated", new_callable=AsyncMock, return_value=True
                    ):
                        from textual.widgets import Input
                        url_input = pilot.app.query_one("#submit-match-url", Input)
                        url_input.value = "https://youtube.com/watch?v=abc123"

                        await screen._inline_submit_match()

                        mock_api.submit_match.assert_called_once_with(
                            source_url=sample_song.url,
                            target_url="https://youtube.com/watch?v=abc123",
                            fallback_song=sample_song,
                        )

    @pytest.mark.asyncio
    async def test_inline_submit_match_offline_warning(self, sample_song, mock_settings, mock_spotdl_app):
        """Verify warning when offline."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                with patch.object(
                    type(screen), "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
                ):
                    mock_spotdl_app.is_online = False
                    with patch.object(screen, "notify") as mock_notify:
                        await screen._inline_submit_match()
                        mock_notify.assert_called_once()
                        assert "online" in mock_notify.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_inline_submit_match_empty_url(self, sample_song, mock_settings, mock_spotdl_app):
        """Verify warning when URL empty."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                with patch.object(
                    type(screen), "spotdl_app", new_callable=PropertyMock, return_value=mock_spotdl_app
                ):
                    mock_spotdl_app.is_online = True
                    with patch.object(
                        screen, "_ensure_authenticated", new_callable=AsyncMock, return_value=True
                    ):
                        with patch.object(screen, "notify") as mock_notify:
                            await screen._inline_submit_match()
                            mock_notify.assert_called_once()
                            assert "url" in mock_notify.call_args[0][0].lower()

    def test_bindings_exist(self, sample_song, mock_settings):
        """Verify all key bindings declared."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(sample_song)
        binding_keys = {b.key for b in screen.BINDINGS}
        for key in ("escape", "d", "r", "m", "s", "p", "u", "n"):
            assert key in binding_keys

    def test_build_report_fields(self, sample_song, mock_settings):
        """Verify report fields built from track details."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(sample_song)
        screen._track_details = {
            "name": "Test Song",
            "artist": "Test Artist",
            "album_name": "Test Album",
            "isrc": "USABC1234567",
        }
        fields = screen._build_report_fields()
        field_names = [f["name"] for f in fields]
        assert "name" in field_names
        assert "artist" in field_names
        assert "album_name" in field_names
        assert "isrc" in field_names


# ── AlbumScreen ──────────────────────────────────────────────────────────────


class TestAlbumScreen:
    """Tests for AlbumScreen."""

    def test_initialization(self, mock_settings):
        """Test AlbumScreen constructor."""
        with patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings):
            screen = AlbumScreen("album123", platform="deezer")
        assert screen._album_id == "album123"
        assert screen._platform == "deezer"
        assert screen._album_data == {}

    def test_initialization_with_initial_data(self, mock_settings):
        """Test AlbumScreen stores initial_data."""
        data = {"name": "My Album", "artist": "Artist"}
        with patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings):
            screen = AlbumScreen("album123", initial_data=data)
        assert screen._album_data == data

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_settings):
        """Test AlbumScreen compose creates proper layout."""
        with (
            patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.album.get_api_client"),
            patch("spotdl_cli.screens.album.get_offline_matcher"),
            patch.object(AlbumScreen, "_load_album_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: AlbumScreen("album123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#album-container") is not None
                assert pilot.app.query_one("#tracks-table", DataTable) is not None

    @pytest.mark.asyncio
    async def test_genre_badges_cleared_on_update(self, mock_settings):
        """Regression: genre badge accumulation fix."""
        with (
            patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.album.get_api_client"),
            patch("spotdl_cli.screens.album.get_offline_matcher"),
            patch.object(AlbumScreen, "_load_album_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: AlbumScreen("album123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AlbumScreen)
                screen._album_data = {
                    "name": "Album",
                    "artist": "Artist",
                    "genres": ["Rock", "Pop"],
                    "tracks": [],
                }

                screen._update_display()
                await pilot.pause()
                screen._update_display()
                await pilot.pause()

                genres_container = pilot.app.query_one("#album-genres", Horizontal)
                assert len(genres_container.children) == 2

    @pytest.mark.asyncio
    async def test_load_album_data_online(self, mock_settings, mock_spotdl_app):
        """Mock API, verify data loaded."""
        mock_api = AsyncMock()
        mock_api.get_album = AsyncMock(return_value={
            "id": "e1",
            "name": "Album",
            "artist": "Artist",
            "tracks": [],
            "total_tracks": 0,
        })

        with (
            patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.album.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.album.get_offline_matcher"),
            patch.object(AlbumScreen, "_load_album_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: AlbumScreen("album123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AlbumScreen)
                screen._album_data = {}
                await screen._load_online_data(use_cache=True)
                mock_api.get_album.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_album_data_force_refresh(self, mock_settings, mock_spotdl_app):
        """Verify use_cache=False."""
        mock_api = AsyncMock()
        mock_api.get_album = AsyncMock(return_value={
            "id": "e1",
            "name": "Album",
            "artist": "Artist",
            "tracks": [],
        })

        with (
            patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.album.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.album.get_offline_matcher"),
            patch.object(AlbumScreen, "_load_album_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: AlbumScreen("album123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(AlbumScreen)
                screen._album_data = {}
                await screen._load_online_data(use_cache=False)
                mock_api.get_album.assert_called_once_with("album123", "spotify", use_cache=False)

    def test_build_report_fields(self, mock_settings):
        """Verify report fields."""
        with patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings):
            screen = AlbumScreen("album123")
        screen._album_data = {"name": "Album", "artist": "Artist", "label": "Label"}
        fields = screen._build_report_fields()
        field_names = [f["name"] for f in fields]
        assert "name" in field_names
        assert "artist_name" in field_names

    def test_bindings_exist(self, mock_settings):
        """Verify key bindings."""
        with patch("spotdl_cli.screens.album.get_settings", return_value=mock_settings):
            screen = AlbumScreen("album123")
        binding_keys = {b.key for b in screen.BINDINGS}
        for key in ("escape", "d", "enter", "a", "p"):
            assert key in binding_keys


# ── ArtistScreen ─────────────────────────────────────────────────────────────


class TestArtistScreen:
    """Tests for ArtistScreen."""

    def test_initialization(self, mock_settings):
        """Test ArtistScreen constructor."""
        with patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings):
            screen = ArtistScreen("artist123", platform="deezer")
        assert screen._artist_id == "artist123"
        assert screen._platform == "deezer"
        assert screen._artist_data == {}

    def test_initialization_with_initial_data(self, mock_settings):
        """Test initial_data stored."""
        data = {"name": "My Artist", "genres": ["Rock"]}
        with patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings):
            screen = ArtistScreen("artist123", initial_data=data)
        assert screen._artist_data == data

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_settings):
        """Test ArtistScreen containers exist."""
        with (
            patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.artist.get_api_client"),
            patch("spotdl_cli.screens.artist.get_offline_matcher"),
            patch.object(ArtistScreen, "_load_artist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: ArtistScreen("artist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#artist-container") is not None

    @pytest.mark.asyncio
    async def test_genre_badges_cleared_on_update(self, mock_settings):
        """Regression: genre badges should not accumulate."""
        with (
            patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.artist.get_api_client"),
            patch("spotdl_cli.screens.artist.get_offline_matcher"),
            patch.object(ArtistScreen, "_load_artist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: ArtistScreen("artist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(ArtistScreen)
                screen._artist_data = {
                    "name": "Artist",
                    "genres": ["Rock", "Pop"],
                    "albums": [],
                    "top_tracks": [],
                }

                screen._update_display()
                await pilot.pause()
                screen._update_display()
                await pilot.pause()

                genres_container = pilot.app.query_one("#artist-genres", Horizontal)
                assert len(genres_container.children) == 2

    @pytest.mark.asyncio
    async def test_load_artist_data_online(self, mock_settings, mock_spotdl_app):
        """Mock API load."""
        mock_api = AsyncMock()
        mock_api.get_artist = AsyncMock(return_value={
            "id": "e1",
            "name": "Artist",
            "genres": [],
            "albums": [],
            "top_tracks": [],
        })

        with (
            patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.artist.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.artist.get_offline_matcher"),
            patch.object(ArtistScreen, "_load_artist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: ArtistScreen("artist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(ArtistScreen)
                screen._artist_data = {}
                await screen._load_online_data(use_cache=True)
                mock_api.get_artist.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_artist_data_force_refresh(self, mock_settings, mock_spotdl_app):
        """Verify use_cache=False."""
        mock_api = AsyncMock()
        mock_api.get_artist = AsyncMock(return_value={
            "id": "e1",
            "name": "Artist",
            "genres": [],
            "albums": [],
            "top_tracks": [],
        })

        with (
            patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.artist.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.artist.get_offline_matcher"),
            patch.object(ArtistScreen, "_load_artist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: ArtistScreen("artist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(ArtistScreen)
                screen._artist_data = {}
                await screen._load_online_data(use_cache=False)
                mock_api.get_artist.assert_called_once_with(
                    "artist123", "spotify", use_cache=False
                )

    def test_build_report_fields(self, mock_settings):
        """Verify report fields."""
        with patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings):
            screen = ArtistScreen("artist123")
        screen._artist_data = {"name": "Artist", "genres": ["Rock"]}
        fields = screen._build_report_fields()
        field_names = [f["name"] for f in fields]
        assert "name" in field_names
        assert "genres" in field_names

    def test_bindings_exist(self, mock_settings):
        """Verify key bindings."""
        with patch("spotdl_cli.screens.artist.get_settings", return_value=mock_settings):
            screen = ArtistScreen("artist123")
        binding_keys = {b.key for b in screen.BINDINGS}
        for key in ("escape", "d", "enter", "tab", "p"):
            assert key in binding_keys


# ── PlaylistScreen ───────────────────────────────────────────────────────────


class TestPlaylistScreen:
    """Tests for PlaylistScreen."""

    def test_initialization(self, mock_settings):
        """Test PlaylistScreen constructor."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123", platform="deezer")
        assert screen._playlist_id == "playlist123"
        assert screen._platform == "deezer"
        assert screen._playlist_data == {}

    def test_initialization_with_initial_data(self, mock_settings):
        """Test initial_data stored."""
        data = {"name": "My Playlist", "owner": {"display_name": "Me"}}
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123", initial_data=data)
        assert screen._playlist_data == data

    @pytest.mark.asyncio
    async def test_compose_layout(self, mock_settings):
        """Test PlaylistScreen containers exist."""
        with (
            patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.playlist.get_api_client"),
            patch("spotdl_cli.screens.playlist.get_offline_matcher"),
            patch.object(PlaylistScreen, "_load_playlist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: PlaylistScreen("playlist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                assert pilot.app.query_one("#playlist-container") is not None
                assert pilot.app.query_one("#tracks-table", DataTable) is not None

    @pytest.mark.asyncio
    async def test_load_playlist_data_online(self, mock_settings, mock_spotdl_app):
        """Mock API load."""
        mock_api = AsyncMock()
        mock_api.get_playlist = AsyncMock(return_value={
            "id": "e1",
            "name": "Playlist",
            "owner": {"display_name": "Owner"},
            "tracks": [],
            "total_tracks": 0,
        })

        with (
            patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.playlist.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.playlist.get_offline_matcher"),
            patch.object(PlaylistScreen, "_load_playlist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: PlaylistScreen("playlist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(PlaylistScreen)
                screen._playlist_data = {}
                await screen._load_online_data(use_cache=True)
                mock_api.get_playlist.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_playlist_data_force_refresh(self, mock_settings, mock_spotdl_app):
        """Verify use_cache=False."""
        mock_api = AsyncMock()
        mock_api.get_playlist = AsyncMock(return_value={
            "id": "e1",
            "name": "Playlist",
            "tracks": [],
        })

        with (
            patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.playlist.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.playlist.get_offline_matcher"),
            patch.object(PlaylistScreen, "_load_playlist_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: PlaylistScreen("playlist123"))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(PlaylistScreen)
                screen._playlist_data = {}
                await screen._load_online_data(use_cache=False)
                mock_api.get_playlist.assert_called_once_with(
                    "playlist123", "spotify", use_cache=False
                )

    def test_build_report_fields_owner_dict(self, mock_settings):
        """Owner as dict works."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123")
        screen._playlist_data = {
            "name": "Playlist",
            "owner": {"display_name": "John"},
        }
        fields = screen._build_report_fields()
        owner_field = next((f for f in fields if f["name"] == "owner_name"), None)
        assert owner_field is not None
        assert owner_field["current_value"] == "John"

    def test_build_report_fields_owner_string(self, mock_settings):
        """Regression: owner as plain string does not crash."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123")
        screen._playlist_data = {
            "name": "Playlist",
            "owner": "StringOwner",
        }
        fields = screen._build_report_fields()
        owner_field = next((f for f in fields if f["name"] == "owner_name"), None)
        assert owner_field is not None
        assert owner_field["current_value"] == "StringOwner"

    def test_build_report_fields_owner_none(self, mock_settings):
        """Owner missing handled gracefully."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123")
        screen._playlist_data = {"name": "Playlist"}
        fields = screen._build_report_fields()
        owner_field = next((f for f in fields if f["name"] == "owner_name"), None)
        # owner_name should be None -> skipped by add_field
        assert owner_field is None

    def test_build_report_fields_owner_other_type(self, mock_settings):
        """Owner as unexpected type returns None."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123")
        screen._playlist_data = {
            "name": "Playlist",
            "owner": 12345,
        }
        fields = screen._build_report_fields()
        owner_field = next((f for f in fields if f["name"] == "owner_name"), None)
        # Non-str, non-dict should return None
        assert owner_field is None

    def test_bindings_exist(self, mock_settings):
        """Verify key bindings."""
        with patch("spotdl_cli.screens.playlist.get_settings", return_value=mock_settings):
            screen = PlaylistScreen("playlist123")
        binding_keys = {b.key for b in screen.BINDINGS}
        for key in ("escape", "d", "enter", "a", "p"):
            assert key in binding_keys
