"""Tests for offline mode: track metadata, auth guards, and settings fixes."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from textual.app import App
from textual.widgets import Button, DataTable, ProgressBar, Static

from spotdl_cli.screens.track import TrackScreen
from spotdl_cli.screens.main import MainScreen
from spotdl_cli.screens.account import AccountScreen
from spotdl_cli.screens.settings import SettingsScreen
from spotdl_cli.core.types import DownloadResult, MatchEntry, Platform, Song, TargetPlatform


@pytest.fixture
def sample_song():
    """Create a sample song with full metadata."""
    return Song(
        name="Test Song",
        artists=["Test Artist", "Featured"],
        artist="Test Artist",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
        album_name="Test Album",
        album_artist="Test Artist",
        genres=["Pop", "Rock"],
        year=2024,
        date="2024-06-15",
        track_number=3,
        disc_number=1,
        isrc="USABC1234567",
        cover_url="https://example.com/cover.jpg",
        explicit=True,
        publisher="Test Label",
        popularity=72,
        copyright_text="2024 Test Label",
    )


@pytest.fixture
def minimal_song():
    """Song with minimal metadata (typical offline search result)."""
    return Song(
        name="Minimal Song",
        artists=["Artist"],
        artist="Artist",
        duration=200,
        platform=Platform.YOUTUBE_MUSIC,
        platform_id="ytm123",
        url="https://music.youtube.com/watch?v=ytm123",
    )


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.api_url = "http://localhost:8000"
    settings.offline_mode = True
    settings.auth_token = None
    settings.api_timeout = 30.0
    settings.audio_providers = []
    settings.spotify_client_id = ""
    settings.spotify_client_secret = ""
    return settings


@pytest.fixture
def mock_offline_app():
    """Mock SpotDLApp in offline mode."""
    app = MagicMock()
    app.is_online = False
    app.download_queue = AsyncMock()
    app.download_queue.add = AsyncMock()
    return app


@pytest.fixture
def mock_online_app():
    """Mock SpotDLApp in online mode."""
    app = MagicMock()
    app.is_online = True
    app.download_queue = AsyncMock()
    app.download_queue.add = AsyncMock()
    return app


def _make_test_app(screen_factory):
    """Create a TestApp that composes a screen directly."""

    class TestApp(App):
        def compose(self):
            yield screen_factory()

    return TestApp


# ── TrackScreen offline metadata display ─────────────────────────────────────


class TestTrackScreenOfflineMetadata:
    """Tests for track screen metadata population in offline mode."""

    def test_build_track_details_from_song_full(self, sample_song, mock_settings):
        """Verify _build_track_details_from_song captures all Song fields."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(sample_song)
        details = screen._build_track_details_from_song()

        assert details["name"] == "Test Song"
        assert details["artist"] == "Test Artist"
        assert details["isrc"] == "USABC1234567"
        assert details["label"] == "Test Label"
        assert details["popularity"] == 72
        assert details["copyright"] == "2024 Test Label"

    def test_build_track_details_from_song_minimal(self, minimal_song, mock_settings):
        """Verify minimal Song produces dict with None/empty values."""
        with patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings):
            screen = TrackScreen(minimal_song)
        details = screen._build_track_details_from_song()

        assert details["name"] == "Minimal Song"
        assert details["isrc"] is None
        assert details["label"] is None  # empty publisher -> None
        assert details["popularity"] is None
        assert details["copyright"] is None

    @pytest.mark.asyncio
    async def test_update_track_details_full_data(self, sample_song, mock_settings):
        """Verify all sidebar fields are populated with full data."""
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

                screen._track_details = {
                    "isrc": "USABC1234567",
                    "label": "Test Label",
                    "popularity": 72,
                    "copyright": "2024 Test Label",
                    "matches_count": 5,
                }
                screen._entity_id = "uuid-123"
                screen._update_track_details()
                await pilot.pause()

                assert "USABC1234567" in str(pilot.app.query_one("#detail-isrc", Static).content)
                assert "Test Label" in str(pilot.app.query_one("#detail-label", Static).content)
                assert "72/100" in str(pilot.app.query_one("#detail-popularity", Static).content)
                assert "abc123" in str(pilot.app.query_one("#detail-platform-id", Static).content)
                assert "uuid-123" in str(pilot.app.query_one("#detail-internal-id", Static).content)
                assert "5" in str(pilot.app.query_one("#detail-matches-count", Static).content)

    @pytest.mark.asyncio
    async def test_update_track_details_missing_data_shows_dashes(self, minimal_song, mock_settings):
        """Verify missing fields show '--' placeholder instead of being empty."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(minimal_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                screen._track_details = {"name": "Minimal Song"}
                screen._update_track_details()
                await pilot.pause()

                # All fields should show -- for missing data
                isrc_text = str(pilot.app.query_one("#detail-isrc", Static).content)
                assert "--" in isrc_text

                label_text = str(pilot.app.query_one("#detail-label", Static).content)
                assert "--" in label_text

                pop_text = str(pilot.app.query_one("#detail-popularity", Static).content)
                assert "--" in pop_text

    @pytest.mark.asyncio
    async def test_update_track_details_empty_dict(self, sample_song, mock_settings):
        """Verify _update_track_details works with empty track_details."""
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

                screen._track_details = {}
                screen._update_track_details()
                await pilot.pause()

                # Should show dashes, not crash
                isrc_text = str(pilot.app.query_one("#detail-isrc", Static).content)
                assert "--" in isrc_text

    @pytest.mark.asyncio
    async def test_widgets_have_initial_placeholders(self, sample_song, mock_settings):
        """Verify compose() initializes detail widgets with placeholder text."""
        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher"),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                # All detail widgets should have placeholder text from compose
                for widget_id in [
                    "#detail-isrc",
                    "#detail-label",
                    "#detail-popularity",
                    "#detail-platform-id",
                    "#detail-internal-id",
                    "#detail-matches-count",
                    "#detail-copyright",
                ]:
                    text = str(pilot.app.query_one(widget_id, Static).content)
                    assert "--" in text, f"{widget_id} should have placeholder"

    @pytest.mark.asyncio
    async def test_audio_features_update(self, sample_song, mock_settings):
        """Verify audio features are populated from Spotify data."""
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

                screen._audio_features = {
                    "tempo": 120.5,
                    "energy": 0.85,
                    "danceability": 0.72,
                    "valence": 0.60,
                    "loudness": -5.3,
                    "time_signature": 4,
                    "key": 0,
                    "mode": 1,
                }
                screen._update_audio_features()
                await pilot.pause()

                bpm = str(pilot.app.query_one("#feature-bpm", Static).content)
                assert "120" in bpm or "121" in bpm

                loudness = str(pilot.app.query_one("#feature-loudness", Static).content)
                assert "-5.3" in loudness

                time_sig = str(pilot.app.query_one("#feature-time-sig", Static).content)
                assert "4/4" in time_sig

    @pytest.mark.asyncio
    async def test_load_offline_data_calls_all_steps(self, sample_song, mock_settings, mock_offline_app):
        """Verify _load_offline_data calls enrich, details, features, matches, lyrics."""
        mock_matcher = AsyncMock()
        mock_matcher.enrich_song = AsyncMock(return_value=sample_song)
        mock_matcher.get_audio_features = AsyncMock(return_value={"tempo": 120, "energy": 0.8})
        mock_matcher.get_all_lyrics = AsyncMock(return_value={"Genius": "Test lyrics"})
        mock_matcher.find_matches = AsyncMock(return_value=[])

        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher", return_value=mock_matcher),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                with patch.object(
                    type(screen), "spotdl_app",
                    new_callable=PropertyMock, return_value=mock_offline_app,
                ):
                    await screen._load_offline_data()

                mock_matcher.enrich_song.assert_called_once()
                mock_matcher.get_audio_features.assert_called_once()
                mock_matcher.get_all_lyrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_offline_data_populates_lyrics_selector(self, sample_song, mock_settings, mock_offline_app):
        """Verify multi-source lyrics populate the selector."""
        mock_matcher = AsyncMock()
        mock_matcher.enrich_song = AsyncMock(return_value=sample_song)
        mock_matcher.get_audio_features = AsyncMock(return_value=None)
        mock_matcher.get_all_lyrics = AsyncMock(return_value={
            "Genius": "Genius lyrics here",
            "Musixmatch": "Musixmatch lyrics here",
        })
        mock_matcher.find_matches = AsyncMock(return_value=[])

        with (
            patch("spotdl_cli.screens.track.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.track.get_api_client"),
            patch("spotdl_cli.screens.track.get_offline_matcher", return_value=mock_matcher),
            patch.object(TrackScreen, "_load_track_data", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(lambda: TrackScreen(sample_song))
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                screen = pilot.app.query_one(TrackScreen)

                with patch.object(
                    type(screen), "spotdl_app",
                    new_callable=PropertyMock, return_value=mock_offline_app,
                ):
                    await screen._load_offline_data()
                    await pilot.pause()

                assert screen._all_lyrics == {
                    "Genius": "Genius lyrics here",
                    "Musixmatch": "Musixmatch lyrics here",
                }
                assert screen._lyrics_sources_count == 2
                assert screen._lyrics is not None

    @pytest.mark.asyncio
    async def test_matches_count_updated_after_find(self, sample_song, mock_settings, mock_offline_app):
        """Verify matches count in sidebar updates after matches are found."""
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

                # Simulate having found matches
                match = MatchEntry(
                    id=None,
                    source_url="https://example.com",
                    target_url="https://youtube.com/watch?v=test",
                    target_platform="youtube",
                    score=95.0,
                    confidence=0.0,
                    match_type="system",
                    status=None,
                    result=DownloadResult(
                        name="Test", artists=["Artist"], artist="Artist",
                        duration=180, platform=TargetPlatform.YOUTUBE,
                        platform_id="test", url="https://youtube.com/watch?v=test",
                        score=95.0,
                    ),
                )
                screen._matches = [match]
                screen._update_matches_table()
                await pilot.pause()

                count_text = str(pilot.app.query_one("#detail-matches-count", Static).content)
                assert "1" in count_text


# ── Authentication guards ────────────────────────────────────────────────────


class TestAuthGuardsOffline:
    """Tests for auth-related behavior in offline mode."""

    @pytest.mark.asyncio
    async def test_ensure_authenticated_offline_returns_false(self, sample_song, mock_settings, mock_offline_app):
        """_ensure_authenticated returns False in offline mode without showing login."""
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
                    type(screen), "spotdl_app",
                    new_callable=PropertyMock, return_value=mock_offline_app,
                ):
                    with patch.object(screen, "notify") as mock_notify:
                        result = await screen._ensure_authenticated()
                        assert result is False
                        mock_notify.assert_called_once()
                        assert "online" in mock_notify.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_ensure_authenticated_online_with_token(self, sample_song, mock_settings, mock_online_app):
        """_ensure_authenticated returns True when online and has token."""
        mock_settings.auth_token = "valid-token"
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
                    type(screen), "spotdl_app",
                    new_callable=PropertyMock, return_value=mock_online_app,
                ):
                    result = await screen._ensure_authenticated()
                    assert result is True


# ── MainScreen login button visibility ───────────────────────────────────────


class TestMainScreenLoginButton:
    """Tests for login button visibility in online/offline mode."""

    @pytest.mark.asyncio
    async def test_login_button_hidden_offline(self, mock_settings, mock_offline_app):
        """Login button should be hidden when offline."""
        with (
            patch("spotdl_cli.screens.main.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.main.get_api_client"),
            patch("spotdl_cli.screens.main.get_offline_matcher"),
            patch.object(
                MainScreen, "spotdl_app",
                new_callable=PropertyMock, return_value=mock_offline_app,
            ),
        ):
            TestApp = _make_test_app(MainScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                btn = pilot.app.query_one("#login-btn", Button)
                assert btn.has_class("hidden")

    @pytest.mark.asyncio
    async def test_login_button_visible_online(self, mock_settings, mock_online_app):
        """Login button should be visible when online."""
        mock_api = AsyncMock()
        mock_api.get_service_status = AsyncMock(return_value={"overall_state": "ok", "sources": [], "targets": [], "metadata": []})
        with (
            patch("spotdl_cli.screens.main.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.main.get_offline_matcher"),
            patch.object(
                MainScreen, "spotdl_app",
                new_callable=PropertyMock, return_value=mock_online_app,
            ),
        ):
            TestApp = _make_test_app(MainScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                btn = pilot.app.query_one("#login-btn", Button)
                assert not btn.has_class("hidden")

    @pytest.mark.asyncio
    async def test_login_button_shows_logout_when_authenticated(self, mock_settings, mock_online_app):
        """Login button shows 'Logout' when auth_token is set."""
        mock_settings.auth_token = "valid-token"
        mock_api = AsyncMock()
        mock_api.get_service_status = AsyncMock(return_value={"overall_state": "ok", "sources": [], "targets": [], "metadata": []})
        with (
            patch("spotdl_cli.screens.main.get_settings", return_value=mock_settings),
            patch("spotdl_cli.screens.main.get_api_client", return_value=mock_api),
            patch("spotdl_cli.screens.main.get_offline_matcher"),
            patch.object(
                MainScreen, "spotdl_app",
                new_callable=PropertyMock, return_value=mock_online_app,
            ),
        ):
            TestApp = _make_test_app(MainScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()

                btn = pilot.app.query_one("#login-btn", Button)
                assert str(btn.label) == "Logout"


# ── Settings DataTable fix ───────────────────────────────────────────────────


class TestSettingsDataTable:
    """Tests for settings screen DataTable column_count fix."""

    @pytest.mark.asyncio
    async def test_provider_tables_render_without_error(self):
        """Provider tables should render without AttributeError (regression: column_count)."""
        from spotdl_cli.config import Settings

        settings = Settings(
            api_url="http://localhost:8000",
            offline_mode=True,
            output_dir="/tmp/test",
            audio_format="mp3",
            audio_quality="best",
            threads=2,
        )
        with (
            patch("spotdl_cli.screens.settings.get_settings", return_value=settings),
            patch("spotdl_cli.screens.settings.get_api_client"),
            patch.object(SettingsScreen, "_load_service_status", new_callable=AsyncMock),
        ):
            TestApp = _make_test_app(SettingsScreen)
            async with TestApp().run_test() as pilot:
                await pilot.pause()
                # If we get here, no AttributeError on column_count
                table = pilot.app.query_one("#audio-source-table", DataTable)
                assert len(table.columns) > 0


# ── OfflineMatcher new methods ───────────────────────────────────────────────


class TestOfflineMatcherMethods:
    """Tests for OfflineMatcher.get_audio_features and get_all_lyrics."""

    @pytest.mark.asyncio
    async def test_get_audio_features_no_spotify(self):
        """Returns None when Spotify provider is not configured."""
        from spotdl_cli.core.offline import OfflineMatcher

        matcher = OfflineMatcher()
        matcher._providers_initialized = True
        matcher._spotify_provider = None

        result = await matcher.get_audio_features(
            Song(
                name="Test", artists=["A"], artist="A", duration=180,
                platform=Platform.YOUTUBE_MUSIC, platform_id="x", url="https://x.com",
            )
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_audio_features_with_spotify(self):
        """Returns features when Spotify is configured."""
        from spotdl_cli.core.offline import OfflineMatcher

        mock_client = MagicMock()
        mock_client.audio_features.return_value = [
            {"tempo": 120, "energy": 0.8, "danceability": 0.7}
        ]

        mock_provider = MagicMock()
        mock_provider._get_client.return_value = mock_client

        matcher = OfflineMatcher()
        matcher._providers_initialized = True
        matcher._spotify_provider = mock_provider

        song = Song(
            name="Test", artists=["A"], artist="A", duration=180,
            platform=Platform.SPOTIFY, platform_id="track123", url="https://open.spotify.com/track/track123",
        )

        result = await matcher.get_audio_features(song)
        assert result is not None
        assert result["tempo"] == 120
        assert result["energy"] == 0.8

    @pytest.mark.asyncio
    async def test_get_all_lyrics_returns_dict(self):
        """Returns a dict of provider name -> lyrics text."""
        from spotdl_cli.core.offline import OfflineMatcher

        # Mock syncedlyrics Lyrics objects
        mock_musixmatch_result = MagicMock()
        mock_musixmatch_result.unsynced = "Musixmatch lyrics text"
        mock_musixmatch_result.synced = None

        mock_genius_result = MagicMock()
        mock_genius_result.unsynced = "Genius lyrics text"
        mock_genius_result.synced = None

        # Lrclib returns None (not found)
        mock_musixmatch_cls = MagicMock()
        mock_musixmatch_cls.return_value.get_lrc.return_value = mock_musixmatch_result

        mock_genius_cls = MagicMock()
        mock_genius_cls.return_value.get_lrc.return_value = mock_genius_result

        mock_lrclib_cls = MagicMock()
        mock_lrclib_cls.return_value.get_lrc.return_value = None

        matcher = OfflineMatcher()
        matcher._providers_initialized = True

        song = Song(
            name="Test", artists=["Artist"], artist="Artist", duration=180,
            platform=Platform.SPOTIFY, platform_id="x", url="https://x.com",
        )

        with patch("syncedlyrics.Musixmatch", mock_musixmatch_cls), \
             patch("syncedlyrics.Genius", mock_genius_cls), \
             patch("syncedlyrics.Lrclib", mock_lrclib_cls):
            result = await matcher.get_all_lyrics(song)

        assert "Musixmatch" in result
        assert result["Musixmatch"] == "Musixmatch lyrics text"
        assert "Genius" in result
        assert result["Genius"] == "Genius lyrics text"
        assert "Lrclib" not in result  # returned None

    @pytest.mark.asyncio
    async def test_get_audio_features_search_fallback(self):
        """When song is not from Spotify, searches Spotify first."""
        from spotdl_cli.core.offline import OfflineMatcher

        mock_client = MagicMock()
        mock_client.search.return_value = {
            "tracks": {"items": [{"id": "found123"}]}
        }
        mock_client.audio_features.return_value = [
            {"tempo": 140, "energy": 0.9}
        ]

        mock_provider = MagicMock()
        mock_provider._get_client.return_value = mock_client

        matcher = OfflineMatcher()
        matcher._providers_initialized = True
        matcher._spotify_provider = mock_provider

        song = Song(
            name="NonSpotify", artists=["A"], artist="A", duration=180,
            platform=Platform.YOUTUBE_MUSIC, platform_id="yt123",
            url="https://music.youtube.com/watch?v=yt123",
        )

        result = await matcher.get_audio_features(song)
        assert result is not None
        assert result["tempo"] == 140
        mock_client.search.assert_called_once()
        mock_client.audio_features.assert_called_once_with(["found123"])


# ── Refresh metadata offline ─────────────────────────────────────────────────


class TestRefreshMetadataOffline:
    """Tests for refresh metadata in offline mode."""

    @pytest.mark.asyncio
    async def test_refresh_metadata_offline_calls_load_offline(self, sample_song, mock_settings, mock_offline_app):
        """Offline refresh should call _load_offline_data."""
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

                with (
                    patch.object(
                        type(screen), "spotdl_app",
                        new_callable=PropertyMock, return_value=mock_offline_app,
                    ),
                    patch.object(screen, "_load_offline_data", new_callable=AsyncMock) as mock_load,
                    patch.object(screen, "notify"),
                ):
                    await screen._refresh_metadata()
                    mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_metadata_offline_error_handling(self, sample_song, mock_settings, mock_offline_app):
        """Offline refresh failure shows error notification."""
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

                with (
                    patch.object(
                        type(screen), "spotdl_app",
                        new_callable=PropertyMock, return_value=mock_offline_app,
                    ),
                    patch.object(
                        screen, "_load_offline_data",
                        new_callable=AsyncMock, side_effect=Exception("Network error"),
                    ),
                    patch.object(screen, "notify") as mock_notify,
                ):
                    await screen._refresh_metadata()
                    # Should have called notify with error
                    calls = [str(c) for c in mock_notify.call_args_list]
                    assert any("error" in c.lower() or "failed" in c.lower() for c in calls)
