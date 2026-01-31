"""Pytest configuration and fixtures."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.main import app


@pytest.fixture
def sample_song() -> Song:
    """Create a sample song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist One", "Artist Two"],
        artist="Artist One",
        duration=180,
        platform=Platform.SPOTIFY,
        platform_id="test123",
        url="https://open.spotify.com/track/test123",
        album_name="Test Album",
        album_artist="Artist One",
        year=2024,
        isrc="USRC12345678",
        explicit=False,
    )


@pytest.fixture
def sample_result() -> Result:
    """Create a sample result for testing."""
    return Result(
        source=TargetPlatform.YOUTUBE_MUSIC,
        url="https://music.youtube.com/watch?v=abc123",
        verified=True,
        name="Artist One - Test Song",
        duration=181.0,
        author="Artist One",
        result_id="abc123",
        artists=("Artist One", "Artist Two"),
        album="Test Album",
    )


@pytest.fixture
def sample_result_unverified() -> Result:
    """Create an unverified result for testing."""
    return Result(
        source=TargetPlatform.YOUTUBE,
        url="https://www.youtube.com/watch?v=xyz789",
        verified=False,
        name="Test Song - Artist One",
        duration=185.0,
        author="RandomChannel",
        result_id="xyz789",
    )


def create_song(
    name: str = "Test Song",
    artists: list[str] | None = None,
    duration: int = 180,
    album_name: str = "Test Album",
    explicit: bool = False,
    **kwargs: Any,
) -> Song:
    """Helper to create songs with default values."""
    if artists is None:
        artists = ["Artist One"]

    return Song(
        name=name,
        artists=artists,
        artist=artists[0] if artists else "",
        duration=duration,
        platform=Platform.SPOTIFY,
        platform_id=str(uuid.uuid4())[:8],
        url=f"https://open.spotify.com/track/{uuid.uuid4()}",
        album_name=album_name,
        album_artist=artists[0] if artists else "",
        explicit=explicit,
        **kwargs,
    )


def create_result(
    name: str = "Test Song",
    duration: float = 180.0,
    verified: bool = True,
    artists: tuple[str, ...] | None = None,
    source: TargetPlatform = TargetPlatform.YOUTUBE_MUSIC,
    album: str | None = None,
    explicit: bool | None = None,
    isrc_search: bool | None = None,
    **kwargs: Any,
) -> Result:
    """Helper to create results with default values."""
    result_id = str(uuid.uuid4())[:11]
    return Result(
        source=source,
        url=f"https://music.youtube.com/watch?v={result_id}",
        verified=verified,
        name=name,
        duration=duration,
        author=artists[0] if artists else "Unknown",
        result_id=result_id,
        artists=artists,
        album=album,
        explicit=explicit,
        isrc_search=isrc_search,
        **kwargs,
    )


@pytest.fixture
async def client():
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
