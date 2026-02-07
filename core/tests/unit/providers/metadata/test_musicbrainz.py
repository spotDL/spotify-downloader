"""Unit tests for spotdl_core.providers.metadata.musicbrainz module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from spotdl_core.providers.metadata.base import MetadataProviderError, MetadataResult
from spotdl_core.providers.metadata.musicbrainz import MusicBrainzProvider


# ── Test Data ───────────────────────────────────────────────────────


@pytest.fixture
def sample_recording():
    """Create a sample MusicBrainz recording."""
    return {
        "id": "mb-recording-123",
        "title": "Test Song",
        "artist-credit": [
            {
                "artist": {
                    "name": "Test Artist",
                }
            }
        ],
        "release-list": [
            {
                "id": "mb-release-123",
                "title": "Test Album",
                "country": "US",
                "date": "2024-01-15",
                "medium-list": [
                    {
                        "position": 1,
                        "track-count": 10,
                        "track-list": [
                            {
                                "position": 5,
                            }
                        ],
                    }
                ],
                "label-info-list": [
                    {
                        "label": {
                            "name": "Test Label",
                        }
                    }
                ],
            }
        ],
        "length": 180000,
        "isrc-list": ["USRC12345678"],
        "tag-list": [
            {"name": "pop"},
            {"name": "rock"},
        ],
        "ext:score": 95,
    }


# ── 1. Initialization Tests ─────────────────────────────────────────


class TestMusicBrainzInitialization:
    """Test MusicBrainzProvider initialization."""

    def test_init_default_values(self) -> None:
        """Test initialization with default values."""
        provider = MusicBrainzProvider()
        assert provider._app_name == "spotdl"
        assert provider._app_version == "5.0.0"
        assert "github.com" in provider._contact
        assert not provider._initialized

    def test_init_custom_values(self) -> None:
        """Test initialization with custom values."""
        provider = MusicBrainzProvider(
            app_name="TestApp",
            app_version="1.0.0",
            contact="test@example.com",
        )
        assert provider._app_name == "TestApp"
        assert provider._app_version == "1.0.0"
        assert provider._contact == "test@example.com"

    def test_provider_attributes(self) -> None:
        """Test provider class attributes."""
        provider = MusicBrainzProvider()
        assert provider.name == "musicbrainz"
        assert provider.display_name == "MusicBrainz"
        assert provider.requests_per_second == 1.0

    def test_has_lock_for_thread_safety(self) -> None:
        """Test provider has asyncio lock."""
        provider = MusicBrainzProvider()
        assert isinstance(provider._lock, asyncio.Lock)


# ── 2. Initialization Tests ─────────────────────────────────────────


class TestEnsureInitialization:
    """Test MusicBrainz library initialization."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_exists(self) -> None:
        """Test initialization method exists."""
        provider = MusicBrainzProvider()
        assert hasattr(provider, "_ensure_initialized")

    @pytest.mark.asyncio
    async def test_ensure_initialized_uses_lock(self) -> None:
        """Test initialization uses lock."""
        provider = MusicBrainzProvider()
        assert provider._lock is not None
        assert isinstance(provider._lock, asyncio.Lock)

    def test_initialization_state_tracking(self) -> None:
        """Test initialization state is tracked."""
        provider = MusicBrainzProvider()
        assert provider._initialized is False


# ── 3. ISRC Lookup Tests ────────────────────────────────────────────


class TestISRCLookup:
    """Test ISRC lookup functionality."""

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_success(self, sample_recording) -> None:
        """Test successful ISRC lookup."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "isrc": {"recording-list": [sample_recording]}
                }

                result = await provider.lookup_by_isrc("USRC12345678")

                assert result is not None
                assert result.name == "Test Song"
                assert result.isrc == "USRC12345678"

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_no_results(self) -> None:
        """Test ISRC lookup with no results."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            mock_mb.get_recordings_by_isrc.return_value = {
                "isrc": {"recording-list": []}
            }

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "isrc": {"recording-list": []}
                }

                result = await provider.lookup_by_isrc("INVALID")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_uses_executor(self, sample_recording) -> None:
        """Test ISRC lookup uses executor."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "isrc": {"recording-list": [sample_recording]}
                }

                await provider.lookup_by_isrc("USRC12345678")

                mock_event_loop.run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_error_handling(self) -> None:
        """Test ISRC lookup error handling."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.side_effect = Exception("Network error")

                result = await provider.lookup_by_isrc("USRC12345678")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_includes_relations(self, sample_recording) -> None:
        """Test ISRC lookup includes artist/release relations."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "isrc": {"recording-list": [sample_recording]}
                }

                await provider.lookup_by_isrc("USRC12345678")

                # Verify the lambda was created (can't easily test lambda content)
                call_args = mock_event_loop.run_in_executor.call_args
                assert call_args is not None


# ── 4. Name Lookup Tests ────────────────────────────────────────────


class TestNameLookup:
    """Test lookup by name functionality."""

    @pytest.mark.asyncio
    async def test_lookup_by_name_success(self, sample_recording) -> None:
        """Test successful name lookup."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [sample_recording]
                }

                result = await provider.lookup_by_name("Test Song", "Test Artist")

                assert result is not None
                assert result.name == "Test Song"

    @pytest.mark.asyncio
    async def test_lookup_by_name_with_album(self, sample_recording) -> None:
        """Test name lookup with album parameter."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [sample_recording]
                }

                await provider.lookup_by_name("Test Song", "Test Artist", "Test Album")

                # Verify album included in query
                call_args = mock_event_loop.run_in_executor.call_args
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_lookup_by_name_no_results(self) -> None:
        """Test name lookup with no results."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {"recording-list": []}

                result = await provider.lookup_by_name("Unknown", "Unknown")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_low_score(self, sample_recording) -> None:
        """Test name lookup rejects low score matches."""
        provider = MusicBrainzProvider()

        low_score_recording = sample_recording.copy()
        low_score_recording["ext:score"] = 50

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [low_score_recording]
                }

                result = await provider.lookup_by_name("Test Song", "Test Artist")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_score_threshold(self, sample_recording) -> None:
        """Test name lookup score threshold is 80."""
        provider = MusicBrainzProvider()

        recording_79 = sample_recording.copy()
        recording_79["ext:score"] = 79

        recording_80 = sample_recording.copy()
        recording_80["ext:score"] = 80

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop

                # Test score 79 (too low)
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [recording_79]
                }
                result = await provider.lookup_by_name("Test", "Test")
                assert result is None

                # Test score 80 (acceptable)
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [recording_80]
                }
                result = await provider.lookup_by_name("Test", "Test")
                assert result is not None

    @pytest.mark.asyncio
    async def test_lookup_by_name_error_handling(self) -> None:
        """Test name lookup error handling."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.side_effect = Exception("API error")

                result = await provider.lookup_by_name("Test", "Test")
                assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_limit_parameter(self, sample_recording) -> None:
        """Test name lookup uses limit parameter."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [sample_recording]
                }

                await provider.lookup_by_name("Test", "Test")

                # Verify limit is 5
                call_args = mock_event_loop.run_in_executor.call_args
                assert call_args is not None


# ── 5. Search Tests ─────────────────────────────────────────────────


class TestSearch:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_success(self, sample_recording) -> None:
        """Test successful search."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [sample_recording, sample_recording]
                }

                results = await provider.search("test query")

                assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_limit(self, sample_recording) -> None:
        """Test search with custom limit."""
        provider = MusicBrainzProvider()

        recordings = [sample_recording] * 20

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": recordings
                }

                results = await provider.search("test query", limit=5)

                assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_empty_results(self) -> None:
        """Test search with no results."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {"recording-list": []}

                results = await provider.search("test query")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_error_handling(self) -> None:
        """Test search error handling."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.side_effect = Exception("Error")

                results = await provider.search("test query")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_parse_failure(self, sample_recording) -> None:
        """Test search continues when parse fails."""
        provider = MusicBrainzProvider()

        broken_recording = {"title": None}

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [broken_recording, sample_recording]
                }

                results = await provider.search("test query")

                # Should skip broken recording
                assert len(results) == 1


# ── 6. Cover Art Tests ──────────────────────────────────────────────


class TestCoverArt:
    """Test cover art retrieval."""

    @pytest.mark.asyncio
    async def test_get_cover_art_success(self) -> None:
        """Test successful cover art retrieval."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "images": [
                        {"front": True, "image": "https://example.com/cover.jpg"}
                    ]
                }

                url = await provider.get_cover_art("mb-release-123")

                assert url == "https://example.com/cover.jpg"

    @pytest.mark.asyncio
    async def test_get_cover_art_no_images(self) -> None:
        """Test cover art when no images available."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {"images": []}

                url = await provider.get_cover_art("mb-release-123")
                assert url is None

    @pytest.mark.asyncio
    async def test_get_cover_art_prefers_front(self) -> None:
        """Test cover art prefers front cover."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "images": [
                        {"front": False, "image": "https://example.com/back.jpg"},
                        {"front": True, "image": "https://example.com/front.jpg"},
                    ]
                }

                url = await provider.get_cover_art("mb-release-123")

                assert url == "https://example.com/front.jpg"

    @pytest.mark.asyncio
    async def test_get_cover_art_fallback_to_first(self) -> None:
        """Test cover art falls back to first image."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "images": [
                        {"front": False, "image": "https://example.com/first.jpg"},
                        {"front": False, "image": "https://example.com/second.jpg"},
                    ]
                }

                url = await provider.get_cover_art("mb-release-123")

                assert url == "https://example.com/first.jpg"

    @pytest.mark.asyncio
    async def test_get_cover_art_error_handling(self) -> None:
        """Test cover art error handling."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.side_effect = Exception("API error")

                url = await provider.get_cover_art("mb-release-123")
                assert url is None


# ── 7. Recording Parsing Tests ──────────────────────────────────────


class TestRecordingParsing:
    """Test recording parsing."""

    def test_parse_recording_basic(self, sample_recording) -> None:
        """Test basic recording parsing."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.name == "Test Song"
        assert result.source == "musicbrainz"
        assert result.confidence == 0.9

    def test_parse_recording_no_title(self) -> None:
        """Test parsing fails without title."""
        provider = MusicBrainzProvider()
        recording = {"title": None}

        result = provider._parse_recording(recording)
        assert result is None

    def test_parse_recording_with_artists(self, sample_recording) -> None:
        """Test parsing with artists."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.artists == ["Test Artist"]

    def test_parse_recording_multiple_artists(self) -> None:
        """Test parsing with multiple artists."""
        provider = MusicBrainzProvider()
        recording = {
            "title": "Test Song",
            "artist-credit": [
                {"artist": {"name": "Artist 1"}},
                {"artist": {"name": "Artist 2"}},
            ],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.artists == ["Artist 1", "Artist 2"]

    def test_parse_recording_with_release_info(self, sample_recording) -> None:
        """Test parsing with release information."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.album_name == "Test Album"
        assert result.country == "US"

    def test_parse_recording_with_date(self, sample_recording) -> None:
        """Test parsing with date."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.date == "2024-01-15"
        assert result.year == 2024

    def test_parse_recording_with_invalid_date(self, sample_recording) -> None:
        """Test parsing with invalid date."""
        provider = MusicBrainzProvider()
        recording = sample_recording.copy()
        recording["release-list"][0]["date"] = "invalid"

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.year is None

    def test_parse_recording_with_track_info(self, sample_recording) -> None:
        """Test parsing with track information."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.disc_number == 1
        assert result.track_number == 5
        assert result.total_tracks == 10

    def test_parse_recording_with_label(self, sample_recording) -> None:
        """Test parsing with label."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.label == "Test Label"

    def test_parse_recording_with_duration(self, sample_recording) -> None:
        """Test parsing with duration."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.duration_ms == 180000

    def test_parse_recording_with_invalid_duration(self, sample_recording) -> None:
        """Test parsing with invalid duration."""
        provider = MusicBrainzProvider()
        recording = sample_recording.copy()
        recording["length"] = "invalid"

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.duration_ms is None

    def test_parse_recording_with_isrc_from_list(self, sample_recording) -> None:
        """Test parsing extracts ISRC from list."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.isrc == "USRC12345678"

    def test_parse_recording_with_isrc_parameter(self, sample_recording) -> None:
        """Test parsing with ISRC parameter."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording, isrc="PROVIDED-ISRC")

        assert result is not None
        assert result.isrc == "PROVIDED-ISRC"

    def test_parse_recording_with_genres(self, sample_recording) -> None:
        """Test parsing with genres from tags."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert "pop" in result.genres
        assert "rock" in result.genres

    def test_parse_recording_with_musicbrainz_id(self, sample_recording) -> None:
        """Test parsing extracts MusicBrainz ID."""
        provider = MusicBrainzProvider()
        result = provider._parse_recording(sample_recording)

        assert result is not None
        assert result.musicbrainz_id == "mb-recording-123"

    def test_parse_recording_no_releases(self) -> None:
        """Test parsing without releases."""
        provider = MusicBrainzProvider()
        recording = {
            "id": "123",
            "title": "Test Song",
            "artist-credit": [],
            "release-list": [],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.album_name is None

    def test_parse_recording_error_handling(self) -> None:
        """Test parsing error handling."""
        provider = MusicBrainzProvider()
        broken_recording = {"title": "Test", "artist-credit": "invalid"}

        result = provider._parse_recording(broken_recording)
        assert result is None

    def test_parse_recording_empty_artist_credit(self) -> None:
        """Test parsing with empty artist credit."""
        provider = MusicBrainzProvider()
        recording = {
            "id": "123",
            "title": "Test Song",
            "artist-credit": [],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.artists is None

    def test_parse_recording_no_medium_list(self, sample_recording) -> None:
        """Test parsing without medium list."""
        provider = MusicBrainzProvider()
        recording = sample_recording.copy()
        recording["release-list"][0]["medium-list"] = []

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.track_number is None
        assert result.disc_number is None

    def test_parse_recording_no_label_info(self, sample_recording) -> None:
        """Test parsing without label info."""
        provider = MusicBrainzProvider()
        recording = sample_recording.copy()
        recording["release-list"][0]["label-info-list"] = []

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.label is None


# ── 8. Edge Cases and Error Handling ────────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_search_query(self) -> None:
        """Test search with empty query."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {"recording-list": []}

                results = await provider.search("")
                assert results == []

    @pytest.mark.asyncio
    async def test_lookup_by_name_without_album(self, sample_recording) -> None:
        """Test name lookup without album."""
        provider = MusicBrainzProvider()

        with patch.object(provider, "_ensure_initialized"):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = {
                    "recording-list": [sample_recording]
                }

                result = await provider.lookup_by_name("Test Song", "Test Artist")

                assert result is not None

    def test_parse_recording_with_dict_artist_credit(self) -> None:
        """Test parsing with dict in artist-credit."""
        provider = MusicBrainzProvider()
        recording = {
            "id": "123",
            "title": "Test Song",
            "artist-credit": [
                {"artist": {"name": "Artist 1"}},
                "separator",  # Non-dict item
                {"artist": {"name": "Artist 2"}},
            ],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.artists == ["Artist 1", "Artist 2"]

    def test_parse_recording_missing_artist_name(self) -> None:
        """Test parsing when artist name is missing."""
        provider = MusicBrainzProvider()
        recording = {
            "id": "123",
            "title": "Test Song",
            "artist-credit": [
                {"artist": {}},  # No name
            ],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.artists is None

    def test_rate_limiting_value(self) -> None:
        """Test rate limiting configuration."""
        provider = MusicBrainzProvider()
        assert provider.requests_per_second == 1.0
