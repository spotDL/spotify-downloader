"""Tests for lyrics API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from spotdl.core.services.lyrics import LyricsResult
from spotdl.db.models.song import Song


@pytest.mark.asyncio
async def test_get_lyrics_for_song_not_found(authenticated_client: AsyncClient):
    """Test getting lyrics for non-existent song returns 404."""
    fake_id = str(uuid4())
    response = await authenticated_client.get(f"/api/v1/lyrics/song/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_lyrics_for_song_invalid_uuid(authenticated_client: AsyncClient):
    """Test getting lyrics with invalid UUID returns 400."""
    response = await authenticated_client.get("/api/v1/lyrics/song/not-a-uuid")
    assert response.status_code == 400
    assert "not a valid UUID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_lyrics_for_song_success(authenticated_client: AsyncClient, db_session):
    """Test successfully getting lyrics for a song."""
    # Create a test song
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="test123",
        platform_url="https://open.spotify.com/track/test123",
        name="Test Song",
        artists=["Test Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    mock_result = LyricsResult(
        lyrics_text="Test lyrics line 1\nTest lyrics line 2",
        lyrics_synced="[00:00.00] Test lyrics line 1\n[00:05.00] Test lyrics line 2",
        source="genius",
        from_cache=False,
    )

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_lyrics = AsyncMock(return_value=mock_result)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.get(f"/api/v1/lyrics/song/{song.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["song_id"] == str(song.id)
        assert data["lyrics_text"] == mock_result.lyrics_text
        assert data["lyrics_synced"] == mock_result.lyrics_synced
        assert data["source"] == "genius"
        assert data["from_cache"] is False


@pytest.mark.asyncio
async def test_get_lyrics_for_song_not_found_lyrics(authenticated_client: AsyncClient, db_session):
    """Test getting lyrics when no lyrics are found."""
    # Create a test song
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="test456",
        platform_url="https://open.spotify.com/track/test456",
        name="No Lyrics Song",
        artists=["Unknown Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_lyrics = AsyncMock(return_value=None)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.get(f"/api/v1/lyrics/song/{song.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["song_id"] == str(song.id)
        assert data["message"] == "No lyrics found"


@pytest.mark.asyncio
async def test_get_lyrics_for_song_force_refresh(authenticated_client: AsyncClient, db_session):
    """Test getting lyrics with force refresh parameter."""
    # Create a test song
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="test789",
        platform_url="https://open.spotify.com/track/test789",
        name="Refresh Song",
        artists=["Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    mock_result = LyricsResult(
        lyrics_text="Fresh lyrics",
        lyrics_synced=None,
        source="musixmatch",
        from_cache=False,
    )

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_lyrics = AsyncMock(return_value=mock_result)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.get(
            f"/api/v1/lyrics/song/{song.id}?force_refresh=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "musixmatch"

        # Verify force_refresh was passed to service
        mock_svc.fetch_lyrics.assert_called_once()
        call_kwargs = mock_svc.fetch_lyrics.call_args.kwargs
        assert call_kwargs["force_refresh"] is True


@pytest.mark.asyncio
async def test_search_lyrics_success(authenticated_client: AsyncClient):
    """Test searching for lyrics by name and artist."""
    mock_result = LyricsResult(
        lyrics_text="Search result lyrics",
        lyrics_synced="[00:00.00] Search result lyrics",
        source="genius",
        from_cache=False,
    )

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_lyrics = AsyncMock(return_value=mock_result)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.get(
            "/api/v1/lyrics/search?name=Test Song&artist=Test Artist"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["song_id"] == "search"
        assert data["lyrics_text"] == mock_result.lyrics_text
        assert data["source"] == "genius"
        assert data["from_cache"] is False


@pytest.mark.asyncio
async def test_search_lyrics_not_found(authenticated_client: AsyncClient):
    """Test searching for lyrics when nothing is found."""
    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_lyrics = AsyncMock(return_value=None)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.get(
            "/api/v1/lyrics/search?name=Unknown&artist=Nobody"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["song_id"] == "search"
        assert data["message"] == "No lyrics found"


@pytest.mark.asyncio
async def test_search_lyrics_missing_parameters(authenticated_client: AsyncClient):
    """Test searching for lyrics without required parameters."""
    # Missing artist
    response = await authenticated_client.get("/api/v1/lyrics/search?name=Test")
    assert response.status_code == 422

    # Missing name
    response = await authenticated_client.get("/api/v1/lyrics/search?artist=Artist")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_all_lyrics_for_song(authenticated_client: AsyncClient, db_session):
    """Test getting all lyrics sources for a song."""
    from spotdl.db.models.lyrics import Lyrics

    # Create a test song
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="multisrc",
        platform_url="https://open.spotify.com/track/multisrc",
        name="Multi Source Song",
        artists=["Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.flush()

    # Add lyrics from multiple sources
    lyrics1 = Lyrics(
        song_id=song.id,
        source="genius",
        lyrics_text="Genius lyrics",
        lyrics_synced=None,
        quality_score=0.95,
        is_verified=True,
    )
    lyrics2 = Lyrics(
        song_id=song.id,
        source="musixmatch",
        lyrics_text="Musixmatch lyrics",
        lyrics_synced="[00:00.00] Musixmatch lyrics",
        quality_score=0.87,
        is_verified=False,
    )
    db_session.add(lyrics1)
    db_session.add(lyrics2)
    await db_session.commit()

    response = await authenticated_client.get(f"/api/v1/lyrics/song/{song.id}/all")

    assert response.status_code == 200
    data = response.json()
    assert data["song_id"] == str(song.id)
    assert data["total_sources"] == 2
    assert len(data["lyrics"]) == 2

    # Check sources are present
    sources = [l["source"] for l in data["lyrics"]]
    assert "genius" in sources
    assert "musixmatch" in sources


@pytest.mark.asyncio
async def test_get_all_lyrics_song_not_found(authenticated_client: AsyncClient):
    """Test getting all lyrics for non-existent song."""
    fake_id = str(uuid4())
    response = await authenticated_client.get(f"/api/v1/lyrics/song/{fake_id}/all")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_all_lyrics_no_lyrics_cached(authenticated_client: AsyncClient, db_session):
    """Test getting all lyrics when none are cached."""
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="nocache",
        platform_url="https://open.spotify.com/track/nocache",
        name="No Cache Song",
        artists=["Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    response = await authenticated_client.get(f"/api/v1/lyrics/song/{song.id}/all")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sources"] == 0
    assert len(data["lyrics"]) == 0


@pytest.mark.asyncio
async def test_fetch_all_lyrics_sources(authenticated_client: AsyncClient, db_session):
    """Test fetching lyrics from all providers."""
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="fetchall",
        platform_url="https://open.spotify.com/track/fetchall",
        name="Fetch All Song",
        artists=["Artist"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    mock_results = [
        LyricsResult(
            lyrics_text="Genius lyrics",
            lyrics_synced=None,
            source="genius",
            from_cache=False,
        ),
        LyricsResult(
            lyrics_text="Musixmatch lyrics",
            lyrics_synced="[00:00.00] Musixmatch lyrics",
            source="musixmatch",
            from_cache=False,
        ),
    ]

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_all_lyrics = AsyncMock(return_value=mock_results)
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.post(
            f"/api/v1/lyrics/song/{song.id}/fetch-all"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["song_id"] == str(song.id)
        assert data["total_sources"] == 2
        assert len(data["lyrics"]) == 2

        # Verify sources
        sources = [l["source"] for l in data["lyrics"]]
        assert "genius" in sources
        assert "musixmatch" in sources


@pytest.mark.asyncio
async def test_fetch_all_lyrics_song_not_found(authenticated_client: AsyncClient):
    """Test fetching all lyrics for non-existent song."""
    fake_id = str(uuid4())
    response = await authenticated_client.post(f"/api/v1/lyrics/song/{fake_id}/fetch-all")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_fetch_all_lyrics_invalid_uuid(authenticated_client: AsyncClient):
    """Test fetching all lyrics with invalid UUID."""
    response = await authenticated_client.post("/api/v1/lyrics/song/invalid-uuid/fetch-all")
    assert response.status_code == 400
    assert "not a valid UUID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fetch_all_lyrics_empty_results(authenticated_client: AsyncClient, db_session):
    """Test fetching all lyrics when no providers return results."""
    song = Song(
        id=uuid4(),
        platform="spotify",
        platform_id="noresults",
        platform_url="https://open.spotify.com/track/noresults",
        name="No Results Song",
        artists=["Unknown"],
        duration_seconds=180,
    )
    db_session.add(song)
    await db_session.commit()

    with patch("spotdl.api.v1.lyrics.get_lyrics_service") as mock_service:
        mock_svc = MagicMock()
        mock_svc.fetch_all_lyrics = AsyncMock(return_value=[])
        mock_svc.__aenter__ = AsyncMock(return_value=mock_svc)
        mock_svc.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_svc

        response = await authenticated_client.post(
            f"/api/v1/lyrics/song/{song.id}/fetch-all"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_sources"] == 0
        assert len(data["lyrics"]) == 0
