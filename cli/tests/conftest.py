"""Shared test fixtures for SpotDL CLI."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from spotdl_cli.config import Settings
from spotdl_cli.core.types import (
    DownloadItem,
    DownloadResult,
    DownloadStatus,
    Platform,
    Song,
    TargetPlatform,
)


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        api_url="http://localhost:8000",
        offline_mode=False,
        output_dir="/tmp/spotdl-test",
        audio_format="mp3",
        audio_quality="best",
        threads=2,
    )


@pytest.fixture
def sample_song() -> Song:
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
def sample_result() -> DownloadResult:
    """Create a sample download result for testing."""
    return DownloadResult(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        duration=182,
        platform=TargetPlatform.YOUTUBE,
        platform_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        verified=True,
        score=95.5,
        cover_url="https://example.com/yt-cover.jpg",
    )


@pytest.fixture
def sample_download_item(sample_song: Song, sample_result: DownloadResult) -> DownloadItem:
    """Create a sample download item for testing."""
    return DownloadItem(
        song=sample_song,
        result=sample_result,
        status=DownloadStatus.PENDING,
    )


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create a mock HTTP client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.is_closed = False
    client.aclose = AsyncMock()
    return client
