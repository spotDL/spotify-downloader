"""Tests for offline mode handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from spotdl_cli.config import Settings
from spotdl_cli.core.offline import (
    OfflineMatcher,
    get_offline_matcher,
)


class TestOfflineMatcher:
    """Tests for OfflineMatcher class."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings(
            api_url="http://localhost:8000",
            offline_mode=True,
            output_dir="/tmp/spotdl-test",
            audio_format="mp3",
            audio_quality="best",
            threads=2,
        )

    @pytest.fixture
    def matcher(self, settings: Settings) -> OfflineMatcher:
        """Create test offline matcher."""
        return OfflineMatcher(settings)

    def test_init(self, matcher: OfflineMatcher) -> None:
        """Test offline matcher initialization."""
        assert matcher._providers_initialized is False
        assert matcher._spotify_provider is None
        assert matcher._deezer_provider is None

    def test_get_yt_dlp_options(self, matcher: OfflineMatcher) -> None:
        """Test yt-dlp options generation."""
        options = matcher._get_yt_dlp_options()

        assert options["format"] == "bestaudio/best"
        assert options["quiet"] is True
        assert options["no_warnings"] is True
        assert options["default_search"] == "ytsearch"

    def test_get_yt_dlp_options_with_cookies(self, tmp_path) -> None:
        """Test yt-dlp options include cookies path when exists."""
        # Create a cookies file in the temp config directory
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.write_text("cookie data")

        # Create settings with config_dir pointing to tmp_path
        settings = Settings(
            api_url="http://localhost:8000",
            offline_mode=True,
            output_dir="/tmp/spotdl-test",
            config_dir=tmp_path,
        )
        matcher = OfflineMatcher(settings)

        options = matcher._get_yt_dlp_options()

        assert options["cookiefile"] == str(cookies_file)

    @pytest.mark.asyncio
    async def test_resolve_url_unsupported(self, matcher: OfflineMatcher) -> None:
        """Test resolving unsupported URL returns empty list."""
        with patch(
            "spotdl_cli.core.offline.detect_platform", return_value=None
        ):
            result = await matcher.resolve_url("https://invalid.url/test")

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_url_spotify_no_credentials(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test resolving Spotify URL without credentials."""
        from spotdl_core import Platform

        with patch(
            "spotdl_cli.core.offline.detect_platform",
            return_value=Platform.SPOTIFY,
        ):
            matcher._init_providers()
            matcher._spotify_provider = None  # No credentials

            result = await matcher._resolve_spotify_url(
                "https://open.spotify.com/track/test"
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_url_deezer(self, matcher: OfflineMatcher) -> None:
        """Test resolving Deezer URL."""
        from spotdl_core import Platform, Song

        mock_song = MagicMock(spec=Song)
        mock_song.name = "Test Song"
        mock_song.artists = ["Test Artist"]

        mock_provider = AsyncMock()
        mock_provider.get_songs_from_url = AsyncMock(return_value=[mock_song])

        with patch(
            "spotdl_cli.core.offline.detect_platform",
            return_value=Platform.DEEZER,
        ):
            matcher._providers_initialized = True
            matcher._deezer_provider = mock_provider

            result = await matcher.resolve_url("https://deezer.com/track/123")

        assert len(result) == 1
        mock_provider.get_songs_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_url_apple_music_not_supported(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test Apple Music URLs are not supported offline."""
        from spotdl_core import Platform

        with patch(
            "spotdl_cli.core.offline.detect_platform",
            return_value=Platform.APPLE_MUSIC,
        ):
            result = await matcher.resolve_url("https://music.apple.com/track/123")

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_url_tidal_not_supported(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test Tidal URLs are not supported offline."""
        from spotdl_core import Platform

        with patch(
            "spotdl_cli.core.offline.detect_platform",
            return_value=Platform.TIDAL,
        ):
            result = await matcher.resolve_url("https://tidal.com/track/123")

        assert result == []

    @pytest.mark.asyncio
    async def test_resolve_youtube_url(self, matcher: OfflineMatcher) -> None:
        """Test resolving YouTube URL."""
        mock_info = {
            "id": "abc123",
            "title": "Artist - Song Title",
            "duration": 200,
            "channel": "Artist Channel",
        }

        with patch.object(
            matcher, "_extract_info", return_value=mock_info
        ):
            result = await matcher._resolve_youtube_url(
                "https://www.youtube.com/watch?v=abc123"
            )

        assert len(result) == 1
        assert result[0].name == "Song Title"
        assert result[0].artist == "Artist"

    @pytest.mark.asyncio
    async def test_resolve_youtube_url_playlist(self, matcher: OfflineMatcher) -> None:
        """Test resolving YouTube playlist URL."""
        mock_info = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Song 1",
                    "duration": 180,
                    "channel": "Artist",
                },
                {
                    "id": "video2",
                    "title": "Song 2",
                    "duration": 200,
                    "channel": "Artist",
                },
            ]
        }

        with patch.object(
            matcher, "_extract_info", return_value=mock_info
        ):
            result = await matcher._resolve_youtube_url(
                "https://www.youtube.com/playlist?list=PLtest"
            )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_resolve_youtube_url_no_result(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test resolving YouTube URL with no result."""
        with patch.object(matcher, "_extract_info", return_value=None):
            result = await matcher._resolve_youtube_url(
                "https://www.youtube.com/watch?v=invalid"
            )

        assert result == []

    def test_yt_entry_to_song(self, matcher: OfflineMatcher) -> None:
        """Test converting yt-dlp entry to Song."""
        entry = {
            "id": "abc123",
            "title": "Artist - Song Title",
            "duration": 200,
            "channel": "Artist Channel",
            "thumbnail": "https://example.com/thumb.jpg",
        }

        song = matcher._yt_entry_to_song(entry)

        assert song is not None
        assert song.name == "Song Title"
        assert song.artist == "Artist"
        assert song.duration == 200
        assert song.platform_id == "abc123"

    def test_yt_entry_to_song_no_title_separator(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test converting entry without title separator."""
        entry = {
            "id": "abc123",
            "title": "Just a Title",
            "duration": 200,
            "channel": "Channel Name",
        }

        song = matcher._yt_entry_to_song(entry)

        assert song is not None
        assert song.name == "Just a Title"
        assert song.artist == "Channel Name"

    def test_yt_entry_to_song_missing_id(self, matcher: OfflineMatcher) -> None:
        """Test converting entry with missing ID returns None."""
        entry = {"title": "Test", "duration": 200}

        song = matcher._yt_entry_to_song(entry)

        assert song is None

    def test_yt_entry_to_song_missing_title(self, matcher: OfflineMatcher) -> None:
        """Test converting entry with missing title returns None."""
        entry = {"id": "abc123", "duration": 200}

        song = matcher._yt_entry_to_song(entry)

        assert song is None

    def test_yt_entry_to_song_exception(self, matcher: OfflineMatcher) -> None:
        """Test converting entry with exception returns None."""
        entry = None  # Will cause exception

        # Should not raise, returns None
        song = matcher._yt_entry_to_song(entry)  # type: ignore

        assert song is None

    @pytest.mark.asyncio
    async def test_search_youtube(self, matcher: OfflineMatcher) -> None:
        """Test YouTube search."""
        mock_results = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test Song",
                    "duration": 200,
                    "channel": "Artist",
                },
            ]
        }

        with patch.object(
            matcher, "_extract_info", return_value=mock_results
        ):
            results = await matcher.search_youtube("test query", limit=5)

        assert len(results) == 1
        assert results[0].name == "Test Song"

    @pytest.mark.asyncio
    async def test_search_youtube_no_results(self, matcher: OfflineMatcher) -> None:
        """Test YouTube search with no results."""
        with patch.object(matcher, "_extract_info", return_value=None):
            results = await matcher.search_youtube("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_youtube_music(self, matcher: OfflineMatcher) -> None:
        """Test YouTube Music search."""
        mock_results = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test Song",
                    "duration": 200,
                    "channel": "Artist",
                    "channel_is_verified": True,
                },
            ]
        }

        with patch.object(
            matcher, "_extract_info", return_value=mock_results
        ):
            results = await matcher.search_youtube_music("test query", limit=5)

        assert len(results) == 1
        assert results[0].verified is True

    @pytest.mark.asyncio
    async def test_search_youtube_music_fallback(
        self, matcher: OfflineMatcher
    ) -> None:
        """Test YouTube Music search falls back to YouTube."""
        mock_yt_results = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test Song",
                    "duration": 200,
                    "channel": "Artist",
                },
            ]
        }

        # First call (YTM) returns None, second call (YT) returns results
        with patch.object(
            matcher,
            "_extract_info",
            side_effect=[None, mock_yt_results],
        ):
            results = await matcher.search_youtube_music("test query")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_all(self, matcher: OfflineMatcher) -> None:
        """Test search across all platforms."""
        from spotdl_core import Song

        mock_song = MagicMock(spec=Song)
        mock_song.platform_id = "song123"

        mock_deezer = AsyncMock()
        mock_deezer.search = AsyncMock(return_value=[mock_song])

        mock_yt_results = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test",
                    "duration": 200,
                    "channel": "Artist",
                },
            ]
        }

        matcher._providers_initialized = True
        matcher._deezer_provider = mock_deezer
        matcher._spotify_provider = None
        matcher._ytm_source_provider = None

        with patch.object(
            matcher, "_extract_info", return_value=mock_yt_results
        ):
            results = await matcher.search_all("test", limit=5)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_all_deduplication(self, matcher: OfflineMatcher) -> None:
        """Test search_all deduplicates results."""
        from spotdl_core import Song

        mock_song = MagicMock(spec=Song)
        mock_song.platform_id = "same_id"

        mock_deezer = AsyncMock()
        mock_deezer.search = AsyncMock(return_value=[mock_song, mock_song])

        matcher._providers_initialized = True
        matcher._deezer_provider = mock_deezer
        matcher._spotify_provider = None
        matcher._ytm_source_provider = None

        with patch.object(
            matcher, "_extract_info", return_value={"entries": []}
        ):
            results = await matcher.search_all("test", limit=5)

        # Should have deduplicated
        assert len(results) == 1

    def test_entry_to_result(self, matcher: OfflineMatcher) -> None:
        """Test converting yt-dlp entry to Result."""
        from spotdl_core import TargetPlatform

        entry = {
            "id": "abc123",
            "title": "Test Song",
            "duration": 200,
            "channel": "Artist",
            "channel_is_verified": True,
            "view_count": 1000000,
            "thumbnail": "https://example.com/thumb.jpg",
        }

        result = matcher._entry_to_result(entry, TargetPlatform.YOUTUBE)

        assert result is not None
        assert result.name == "Test Song"
        assert result.platform == TargetPlatform.YOUTUBE
        assert result.verified is True
        assert result.views == 1000000

    def test_entry_to_result_youtube_music(self, matcher: OfflineMatcher) -> None:
        """Test entry to result for YouTube Music."""
        from spotdl_core import TargetPlatform

        entry = {
            "id": "abc123",
            "title": "Test Song",
            "duration": 200,
            "channel": "Artist",
        }

        result = matcher._entry_to_result(entry, TargetPlatform.YOUTUBE_MUSIC)

        assert result is not None
        assert "music.youtube.com" in result.url

    def test_entry_to_result_missing_id(self, matcher: OfflineMatcher) -> None:
        """Test entry to result with missing ID."""
        from spotdl_core import TargetPlatform

        entry = {"title": "Test", "duration": 200}

        result = matcher._entry_to_result(entry, TargetPlatform.YOUTUBE)

        assert result is None

    def test_entry_to_result_exception(self, matcher: OfflineMatcher) -> None:
        """Test entry to result with exception."""
        from spotdl_core import TargetPlatform

        result = matcher._entry_to_result(None, TargetPlatform.YOUTUBE)  # type: ignore

        assert result is None

    def test_result_to_song(self, matcher: OfflineMatcher) -> None:
        """Test converting Result to Song."""
        from spotdl_core import Result, TargetPlatform

        result = Result(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=200,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc123",
            url="https://youtube.com/watch?v=abc123",
        )

        song = matcher._result_to_song(result)

        assert song.name == "Test Song"
        assert song.artist == "Artist"
        assert song.duration == 200

    def test_extract_info_success(self, matcher: OfflineMatcher) -> None:
        """Test yt-dlp extract_info success."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"id": "test", "title": "Test"}

        with patch("spotdl_cli.core.offline.yt_dlp.YoutubeDL") as mock_cls:
            mock_cls.return_value.__enter__.return_value = mock_ydl

            result = matcher._extract_info("https://youtube.com/watch?v=test", {})

        assert result is not None
        assert result["id"] == "test"

    def test_extract_info_download_error(self, matcher: OfflineMatcher) -> None:
        """Test yt-dlp extract_info with download error."""
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Error")

        with patch("spotdl_cli.core.offline.yt_dlp.YoutubeDL") as mock_cls:
            mock_cls.return_value.__enter__.return_value = mock_ydl

            result = matcher._extract_info("https://invalid.url", {})

        assert result is None

    def test_extract_info_exception(self, matcher: OfflineMatcher) -> None:
        """Test yt-dlp extract_info with unexpected exception."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Unexpected error")

        with patch("spotdl_cli.core.offline.yt_dlp.YoutubeDL") as mock_cls:
            mock_cls.return_value.__enter__.return_value = mock_ydl

            result = matcher._extract_info("https://url", {})

        assert result is None

    @pytest.mark.asyncio
    async def test_find_matches(self, matcher: OfflineMatcher, sample_song) -> None:
        """Test finding matches for a song."""
        from spotdl_core import Result, TargetPlatform

        mock_result = Result(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc123",
            url="https://youtube.com/watch?v=abc123",
        )

        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[mock_result])

        matcher._providers_initialized = True
        matcher._yt_target_provider = mock_provider
        matcher._ytm_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        with patch(
            "spotdl_cli.core.offline.order_results",
            return_value={mock_result: 90.0},
        ):
            results = await matcher.find_matches(sample_song, limit=5)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_matches_no_results(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test finding matches with no results."""
        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[])

        matcher._providers_initialized = True
        matcher._yt_target_provider = mock_provider
        matcher._ytm_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        results = await matcher.find_matches(sample_song)

        assert results == []

    @pytest.mark.asyncio
    async def test_find_matches_with_specific_platforms(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test finding matches on specific platforms."""
        from spotdl_core import TargetPlatform

        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[])

        matcher._providers_initialized = True
        matcher._soundcloud_target_provider = mock_provider

        results = await matcher.find_matches(
            sample_song, platforms=[TargetPlatform.SOUNDCLOUD]
        )

        mock_provider.search.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_find_matches_provider_error(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test finding matches handles provider errors."""
        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(side_effect=Exception("Provider error"))

        matcher._providers_initialized = True
        matcher._yt_target_provider = mock_provider
        matcher._ytm_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        # Should not raise, returns empty list
        results = await matcher.find_matches(sample_song)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_best_match(self, matcher: OfflineMatcher, sample_song) -> None:
        """Test getting best match for a song."""
        from spotdl_core import Result, TargetPlatform

        mock_result = Result(
            name="Test Song",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc123",
            url="https://youtube.com/watch?v=abc123",
        )

        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[mock_result])

        matcher._providers_initialized = True
        matcher._ytm_target_provider = mock_provider
        matcher._yt_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        with patch(
            "spotdl_cli.core.offline.order_results",
            return_value={mock_result: 95.0},
        ):
            result = await matcher.get_best_match(sample_song)

        assert result is not None
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_get_best_match_below_threshold(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test get_best_match returns None when below threshold."""
        from spotdl_core import Result, TargetPlatform

        mock_result = Result(
            name="Test",
            artists=["Artist"],
            artist="Artist",
            duration=180,
            platform=TargetPlatform.YOUTUBE,
            platform_id="abc123",
            url="https://youtube.com/watch?v=abc123",
        )

        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[mock_result])

        matcher._providers_initialized = True
        matcher._ytm_target_provider = mock_provider
        matcher._yt_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        with patch(
            "spotdl_cli.core.offline.order_results",
            return_value={mock_result: 50.0},  # Below default threshold
        ):
            result = await matcher.get_best_match(sample_song, min_score=80.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_best_match_no_results(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test get_best_match with no results."""
        mock_provider = AsyncMock()
        mock_provider.search = AsyncMock(return_value=[])

        matcher._providers_initialized = True
        matcher._ytm_target_provider = mock_provider
        matcher._yt_target_provider = None
        matcher._soundcloud_target_provider = None
        matcher._bandcamp_target_provider = None

        result = await matcher.get_best_match(sample_song)

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_song(self, matcher: OfflineMatcher, sample_song) -> None:
        """Test enriching a song with metadata."""
        mock_enriched = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.enrich_song = AsyncMock(return_value=mock_enriched)

        matcher._providers_initialized = True
        matcher._musicbrainz_provider = mock_provider

        result = await matcher.enrich_song(sample_song)

        assert result == mock_enriched

    @pytest.mark.asyncio
    async def test_enrich_song_no_provider(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test enrich_song without MusicBrainz provider."""
        matcher._providers_initialized = True
        matcher._musicbrainz_provider = None

        result = await matcher.enrich_song(sample_song)

        assert result == sample_song

    @pytest.mark.asyncio
    async def test_enrich_song_error(
        self, matcher: OfflineMatcher, sample_song
    ) -> None:
        """Test enrich_song handles errors."""
        mock_provider = AsyncMock()
        mock_provider.enrich_song = AsyncMock(side_effect=Exception("Error"))

        matcher._providers_initialized = True
        matcher._musicbrainz_provider = mock_provider

        result = await matcher.enrich_song(sample_song)

        # Returns original song on error
        assert result == sample_song

    @pytest.mark.asyncio
    async def test_close(self, matcher: OfflineMatcher) -> None:
        """Test closing the matcher."""
        mock_spotify = AsyncMock()
        mock_deezer = AsyncMock()
        mock_yt = AsyncMock()
        mock_sc = AsyncMock()
        mock_bc = AsyncMock()

        matcher._spotify_provider = mock_spotify
        matcher._deezer_provider = mock_deezer
        matcher._yt_target_provider = mock_yt
        matcher._soundcloud_target_provider = mock_sc
        matcher._bandcamp_target_provider = mock_bc

        await matcher.close()

        mock_spotify.close.assert_called_once()
        mock_deezer.close.assert_called_once()
        mock_yt.close.assert_called_once()
        mock_sc.close.assert_called_once()
        mock_bc.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_providers(self, matcher: OfflineMatcher) -> None:
        """Test closing when no providers initialized."""
        await matcher.close()  # Should not raise


class TestGetOfflineMatcher:
    """Tests for get_offline_matcher function."""

    def test_singleton(self) -> None:
        """Test get_offline_matcher returns singleton."""
        with patch("spotdl_cli.core.offline._offline_matcher", None):
            matcher1 = get_offline_matcher()
            matcher2 = get_offline_matcher()
            assert matcher1 is matcher2
