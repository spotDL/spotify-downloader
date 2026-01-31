"""Tests for MusicBrainz metadata provider."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from spotdl.providers.metadata.musicbrainz import MusicBrainzProvider


# Create mock musicbrainzngs module for testing
@pytest.fixture(autouse=True)
def mock_musicbrainzngs():
    """Mock the musicbrainzngs module."""
    mock_mb = MagicMock()
    mock_mb.set_useragent = MagicMock()
    mock_mb.get_recordings_by_isrc = MagicMock()
    mock_mb.search_recordings = MagicMock()
    mock_mb.get_image_list = MagicMock()

    with patch.dict(sys.modules, {"musicbrainzngs": mock_mb}):
        yield mock_mb


class TestMusicBrainzProviderInit:
    """Tests for MusicBrainzProvider initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        provider = MusicBrainzProvider()
        assert provider.name == "musicbrainz"
        assert provider.display_name == "MusicBrainz"
        assert provider.requests_per_second == 1.0
        assert not provider._initialized

    def test_custom_init(self) -> None:
        """Test initialization with custom parameters."""
        provider = MusicBrainzProvider(
            app_name="test_app",
            app_version="1.0.0",
            contact="test@example.com",
        )
        assert provider._app_name == "test_app"
        assert provider._app_version == "1.0.0"
        assert provider._contact == "test@example.com"


class TestMusicBrainzProviderLookup:
    """Tests for MusicBrainzProvider lookup methods."""

    @pytest.fixture
    def provider(self) -> MusicBrainzProvider:
        """Create a provider for testing."""
        return MusicBrainzProvider()

    @pytest.fixture
    def mock_recording(self) -> dict:
        """Create a mock MusicBrainz recording response."""
        return {
            "id": "12345678-1234-1234-1234-123456789012",
            "title": "Test Track",
            "length": 180000,  # 3 minutes in ms
            "artist-credit": [
                {"artist": {"name": "Test Artist", "id": "artist-id-1"}},
                {"artist": {"name": "Featured Artist", "id": "artist-id-2"}},
            ],
            "release-list": [
                {
                    "title": "Test Album",
                    "date": "2020-05-15",
                    "country": "US",
                    "medium-list": [
                        {
                            "position": 1,
                            "track-count": 12,
                            "track-list": [{"position": 5}],
                        }
                    ],
                    "label-info-list": [{"label": {"name": "Test Label"}}],
                }
            ],
            "isrc-list": ["USRC17607839"],
            "tag-list": [{"name": "rock"}, {"name": "pop"}],
        }

    @pytest.mark.asyncio
    async def test_ensure_initialized(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test initialization happens on first use."""
        await provider._ensure_initialized()
        assert provider._initialized
        mock_musicbrainzngs.set_useragent.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_found(
        self, provider: MusicBrainzProvider, mock_recording: dict, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test ISRC lookup when recording is found."""
        mock_musicbrainzngs.get_recordings_by_isrc.return_value = {
            "isrc": {"recording-list": [mock_recording]}
        }

        result = await provider.lookup_by_isrc("USRC17607839")

        assert result is not None
        assert result.name == "Test Track"
        assert result.isrc == "USRC17607839"
        assert result.source == "musicbrainz"

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_not_found(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test ISRC lookup when no recording found."""
        mock_musicbrainzngs.get_recordings_by_isrc.return_value = {
            "isrc": {"recording-list": []}
        }

        result = await provider.lookup_by_isrc("UNKNOWN123456")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_isrc_error(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test ISRC lookup handles errors gracefully."""
        mock_musicbrainzngs.get_recordings_by_isrc.side_effect = Exception("API Error")

        result = await provider.lookup_by_isrc("USRC17607839")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_by_name_found(
        self, provider: MusicBrainzProvider, mock_recording: dict, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test name lookup when recording is found."""
        mock_recording["ext:score"] = "95"
        mock_musicbrainzngs.search_recordings.return_value = {
            "recording-list": [mock_recording]
        }

        result = await provider.lookup_by_name(
            track_name="Test Track",
            artist_name="Test Artist",
            album_name="Test Album",
        )

        assert result is not None
        assert result.name == "Test Track"

    @pytest.mark.asyncio
    async def test_lookup_by_name_low_score(
        self, provider: MusicBrainzProvider, mock_recording: dict, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test name lookup rejects low-scoring results."""
        mock_recording["ext:score"] = "50"
        mock_musicbrainzngs.search_recordings.return_value = {
            "recording-list": [mock_recording]
        }

        result = await provider.lookup_by_name(
            track_name="Test Track",
            artist_name="Test Artist",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_search(
        self, provider: MusicBrainzProvider, mock_recording: dict, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test search returns results."""
        mock_musicbrainzngs.search_recordings.return_value = {
            "recording-list": [mock_recording, mock_recording]
        }

        results = await provider.search("test query", limit=5)

        assert len(results) == 2
        assert all(r.source == "musicbrainz" for r in results)

    @pytest.mark.asyncio
    async def test_search_error(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test search handles errors gracefully."""
        mock_musicbrainzngs.search_recordings.side_effect = Exception("API Error")

        results = await provider.search("test query")
        assert results == []


class TestMusicBrainzProviderParsing:
    """Tests for MusicBrainzProvider parsing methods."""

    @pytest.fixture
    def provider(self) -> MusicBrainzProvider:
        """Create a provider for testing."""
        return MusicBrainzProvider()

    def test_parse_recording_full(self, provider: MusicBrainzProvider) -> None:
        """Test parsing a complete recording."""
        recording = {
            "id": "mb-id-123",
            "title": "Track Name",
            "length": 240000,
            "artist-credit": [
                {"artist": {"name": "Main Artist"}},
                {"artist": {"name": "Featured"}},
            ],
            "release-list": [
                {
                    "title": "Album Name",
                    "date": "2021-06-20",
                    "country": "UK",
                    "medium-list": [
                        {
                            "position": 2,
                            "track-count": 10,
                            "track-list": [{"position": 3}],
                        }
                    ],
                    "label-info-list": [{"label": {"name": "Record Label"}}],
                }
            ],
            "isrc-list": ["GBXXX1234567"],
            "tag-list": [{"name": "indie"}, {"name": "alternative"}],
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.name == "Track Name"
        assert result.artists == ["Main Artist", "Featured"]
        assert result.album_name == "Album Name"
        assert result.musicbrainz_id == "mb-id-123"
        assert result.isrc == "GBXXX1234567"
        assert result.year == 2021
        assert result.date == "2021-06-20"
        assert result.track_number == 3
        assert result.disc_number == 2
        assert result.total_tracks == 10
        assert result.label == "Record Label"
        assert result.country == "UK"
        assert result.duration_ms == 240000
        assert "indie" in result.genres
        assert "alternative" in result.genres

    def test_parse_recording_minimal(self, provider: MusicBrainzProvider) -> None:
        """Test parsing a minimal recording."""
        recording = {
            "id": "mb-id-123",
            "title": "Track Name",
        }

        result = provider._parse_recording(recording)

        assert result is not None
        assert result.name == "Track Name"
        assert result.artists is None or result.artists == []
        assert result.album_name is None

    def test_parse_recording_no_title(self, provider: MusicBrainzProvider) -> None:
        """Test parsing a recording without title returns None."""
        recording = {"id": "mb-id-123"}

        result = provider._parse_recording(recording)
        assert result is None

    def test_parse_recording_with_provided_isrc(
        self, provider: MusicBrainzProvider
    ) -> None:
        """Test parsing uses provided ISRC over embedded one."""
        recording = {
            "id": "mb-id-123",
            "title": "Track",
            "isrc-list": ["EMBEDDED_ISRC"],
        }

        result = provider._parse_recording(recording, isrc="PROVIDED_ISRC")

        assert result is not None
        assert result.isrc == "PROVIDED_ISRC"


class TestMusicBrainzCoverArt:
    """Tests for MusicBrainz cover art functionality."""

    @pytest.fixture
    def provider(self) -> MusicBrainzProvider:
        """Create a provider for testing."""
        return MusicBrainzProvider()

    @pytest.mark.asyncio
    async def test_get_cover_art_found(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test getting cover art when available."""
        mock_musicbrainzngs.get_image_list.return_value = {
            "images": [
                {"type": "back", "image": "https://example.com/back.jpg"},
                {"type": "front", "front": True, "image": "https://example.com/front.jpg"},
            ]
        }

        url = await provider.get_cover_art("release-id-123")
        assert url == "https://example.com/front.jpg"

    @pytest.mark.asyncio
    async def test_get_cover_art_no_front(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test getting cover art falls back to first image."""
        mock_musicbrainzngs.get_image_list.return_value = {
            "images": [
                {"type": "back", "image": "https://example.com/back.jpg"},
            ]
        }

        url = await provider.get_cover_art("release-id-123")
        assert url == "https://example.com/back.jpg"

    @pytest.mark.asyncio
    async def test_get_cover_art_not_found(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test getting cover art when none available."""
        mock_musicbrainzngs.get_image_list.return_value = {"images": []}

        url = await provider.get_cover_art("release-id-123")
        assert url is None

    @pytest.mark.asyncio
    async def test_get_cover_art_error(
        self, provider: MusicBrainzProvider, mock_musicbrainzngs: MagicMock
    ) -> None:
        """Test getting cover art handles errors."""
        mock_musicbrainzngs.get_image_list.side_effect = Exception("Not found")

        url = await provider.get_cover_art("release-id-123")
        assert url is None
