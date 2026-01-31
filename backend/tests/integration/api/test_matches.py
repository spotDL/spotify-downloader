"""Tests for matches API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from spotdl.core.services.match import Match
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song
from spotdl.db.models.user import User


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_song() -> Song:
    """Create a mock song for testing."""
    return Song(
        name="Test Song",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=200,
        platform=Platform.SPOTIFY,
        platform_id="abc123",
        url="https://open.spotify.com/track/abc123",
    )


@pytest.fixture
def mock_result() -> Result:
    """Create a mock result for testing."""
    return Result(
        name="Test Song",
        artists=["Artist 1"],
        artist="Artist 1",
        duration=200,
        platform=TargetPlatform.YOUTUBE,
        platform_id="xyz789",
        url="https://www.youtube.com/watch?v=xyz789",
        cover_url="https://example.com/thumb.jpg",
        views=100000,
    )


@pytest.fixture
def mock_match(mock_song: Song, mock_result: Result) -> Match:
    """Create a mock match for testing."""
    return Match(
        source_song=mock_song,
        target_result=mock_result,
        score=85.0,
        match_type="system",
        confidence=0.85,
    )


class TestMatchesEndpoints:
    """Tests for matches API endpoints."""

    async def test_get_platforms(self, client: AsyncClient) -> None:
        """Test GET /api/v1/matches/platforms returns target platforms."""
        response = await client.get("/api/v1/matches/platforms")

        assert response.status_code == 200
        data = response.json()
        assert "platforms" in data
        assert "youtube" in data["platforms"]
        assert "youtube_music" in data["platforms"]
        assert "soundcloud" in data["platforms"]


class TestMatchesFindWithMock:
    """Tests for matches find with mocked services."""

    async def test_find_matches_success(
        self, client: AsyncClient, mock_song: Song, mock_match: Match
    ) -> None:
        """Test successful match finding."""
        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc, \
             patch("spotdl.api.v1.matches.get_match_service") as mock_match_svc:
            # Mock song service
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(return_value=[mock_song])
            mock_song_svc.return_value = mock_song_service

            # Mock match service
            mock_match_service = MagicMock()
            mock_match_service.find_matches = AsyncMock(return_value=[mock_match])
            mock_match_svc.return_value = mock_match_service

            response = await client.post(
                "/api/v1/matches/find",
                json={
                    "source_url": "https://open.spotify.com/track/abc123",
                    "target_platforms": ["youtube"],
                    "limit": 5,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["matches"][0]["score"] == 85.0
            assert data["matches"][0]["target_platform"] == "youtube"

    async def test_find_matches_no_songs(self, client: AsyncClient) -> None:
        """Test match finding when no songs found."""
        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc:
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(return_value=[])
            mock_song_svc.return_value = mock_song_service

            response = await client.post(
                "/api/v1/matches/find",
                json={"source_url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 404

    async def test_find_matches_invalid_platform(
        self, client: AsyncClient, mock_song: Song
    ) -> None:
        """Test match finding with invalid platform."""
        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc:
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(return_value=[mock_song])
            mock_song_svc.return_value = mock_song_service

            response = await client.post(
                "/api/v1/matches/find",
                json={
                    "source_url": "https://open.spotify.com/track/abc123",
                    "target_platforms": ["invalid_platform"],
                },
            )

            assert response.status_code == 400

    async def test_find_matches_unsupported_url(self, client: AsyncClient) -> None:
        """Test match finding with unsupported URL."""
        from spotdl.core.services.song import UnsupportedURLError

        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc:
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(
                side_effect=UnsupportedURLError("Unsupported URL")
            )
            mock_song_svc.return_value = mock_song_service

            response = await client.post(
                "/api/v1/matches/find",
                json={"source_url": "https://unsupported-platform.com/track/123"},
            )

            assert response.status_code == 400

    async def test_find_matches_service_error(self, client: AsyncClient) -> None:
        """Test match finding when service raises error."""
        from spotdl.core.services.song import SongServiceError

        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc:
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(
                side_effect=SongServiceError("Service error")
            )
            mock_song_svc.return_value = mock_song_service

            response = await client.post(
                "/api/v1/matches/find",
                json={"source_url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 500

    async def test_find_matches_get_endpoint(
        self, client: AsyncClient, mock_song: Song, mock_match: Match
    ) -> None:
        """Test GET version of find matches."""
        with patch("spotdl.api.v1.matches.get_song_service") as mock_song_svc, \
             patch("spotdl.api.v1.matches.get_match_service") as mock_match_svc:
            mock_song_service = MagicMock()
            mock_song_service.resolve_url = AsyncMock(return_value=[mock_song])
            mock_song_svc.return_value = mock_song_service

            mock_match_service = MagicMock()
            mock_match_service.find_matches = AsyncMock(return_value=[mock_match])
            mock_match_svc.return_value = mock_match_service

            response = await client.get(
                "/api/v1/matches/find",
                params={"source_url": "https://open.spotify.com/track/abc123"},
            )

            assert response.status_code == 200


class TestMatchesSubmit:
    """Tests for match submission endpoint."""

    async def test_submit_match_youtube(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a YouTube match."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://www.youtube.com/watch?v=xyz789",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_platform"] == "youtube"
        assert data["match_type"] == "user"
        assert "id" in data

    async def test_submit_match_youtube_music(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a YouTube Music match."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://music.youtube.com/watch?v=xyz789",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_platform"] == "youtube_music"

    async def test_submit_match_soundcloud(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a SoundCloud match."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://soundcloud.com/artist/track",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_platform"] == "soundcloud"

    async def test_submit_match_bandcamp(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a Bandcamp match."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://artist.bandcamp.com/track/song",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_platform"] == "bandcamp"

    async def test_submit_match_piped(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a Piped match."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://piped.video/watch?v=xyz789",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_platform"] == "piped"

    async def test_submit_match_unsupported_target(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting with unsupported target URL."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/abc123",
                "target_url": "https://example.com/track/xyz",
            },
        )

        assert response.status_code == 400

    async def test_submit_match_unsupported_source(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting with unsupported source URL."""
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://example.com/track/abc123",  # Unsupported source
                "target_url": "https://www.youtube.com/watch?v=xyz789",
            },
        )

        assert response.status_code == 400

    async def test_submit_duplicate_match(
        self, client: AsyncClient, test_user: User
    ) -> None:
        """Test submitting a match that already exists."""
        # Submit first match
        await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/duplicate123",
                "target_url": "https://www.youtube.com/watch?v=dup456",
            },
        )

        # Submit same match again
        response = await client.post(
            "/api/v1/matches/submit",
            json={
                "source_url": "https://open.spotify.com/track/duplicate123",
                "target_url": "https://www.youtube.com/watch?v=dup456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Match already exists."
