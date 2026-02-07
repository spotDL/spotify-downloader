"""Tests for API client."""

import asyncio
import time

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from spotdl_cli.config import Settings
from spotdl_cli.core.api_client import (
    APIClient,
    APIError,
    CacheEntry,
    ConnectionError,
    NotFoundError,
    ResponseCache,
    get_api_client,
)
from spotdl_cli.core.types import EntityType, Platform, TargetPlatform


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_init(self) -> None:
        """Test cache entry initialization."""
        entry = CacheEntry("test_value", ttl=10.0)
        assert entry.value == "test_value"
        assert entry.expires_at > time.monotonic()

    def test_is_expired_false(self) -> None:
        """Test cache entry not expired."""
        entry = CacheEntry("value", ttl=100.0)
        assert entry.is_expired is False

    def test_is_expired_true(self) -> None:
        """Test cache entry expired."""
        entry = CacheEntry("value", ttl=0.0)
        time.sleep(0.01)
        assert entry.is_expired is True


class TestResponseCache:
    """Tests for ResponseCache class."""

    @pytest.fixture
    def cache(self) -> ResponseCache:
        """Create test cache."""
        return ResponseCache(max_size=10, default_ttl=60.0)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: ResponseCache) -> None:
        """Test setting and getting cache values."""
        await cache.set("value1", "key1", "key2")
        result = await cache.get("key1", "key2")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_miss(self, cache: ResponseCache) -> None:
        """Test cache miss returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_expired(self, cache: ResponseCache) -> None:
        """Test expired entries return None."""
        await cache.set("value", "key", ttl=0.001)
        await asyncio.sleep(0.01)
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache: ResponseCache) -> None:
        """Test cache invalidation."""
        await cache.set("value", "key")
        await cache.invalidate("key")
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, cache: ResponseCache) -> None:
        """Test cache clearing."""
        await cache.set("value1", "key1")
        await cache.set("value2", "key2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_eviction(self) -> None:
        """Test cache eviction when max size reached."""
        cache = ResponseCache(max_size=5, default_ttl=60.0)
        for i in range(6):
            await cache.set(f"value{i}", f"key{i}")
        # Should have evicted 20% (1 entry)
        assert len(cache._cache) <= 5

    @pytest.mark.asyncio
    async def test_make_key(self, cache: ResponseCache) -> None:
        """Test key generation is consistent."""
        key1 = cache._make_key("a", "b", "c")
        key2 = cache._make_key("a", "b", "c")
        key3 = cache._make_key("a", "b", "d")
        assert key1 == key2
        assert key1 != key3


class TestAPIClient:
    """Tests for APIClient class."""

    @pytest.fixture
    def client(self, settings: Settings) -> APIClient:
        """Create test API client."""
        return APIClient(settings)

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: APIClient) -> None:
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client: APIClient) -> None:
        """Test failed health check."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
            mock_get.return_value = mock_http

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_non_200(self, client: APIClient) -> None:
        """Test health check with non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_online_offline_mode(self, settings: Settings) -> None:
        """Test is_online returns False in offline mode."""
        settings.offline_mode = True
        client = APIClient(settings)

        result = await client.is_online()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_online_online_mode(self, client: APIClient) -> None:
        """Test is_online returns True when backend is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.is_online()
            assert result is True

    @pytest.mark.asyncio
    async def test_resolve_url_success(self, client: APIClient) -> None:
        """Test successful URL resolution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "songs": [
                {
                    "name": "Test Song",
                    "artists": ["Artist1"],
                    "artist": "Artist1",
                    "duration": 180,
                    "platform": "spotify",
                    "platform_id": "test123",
                    "url": "https://spotify.com/track/test123",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            songs = await client.resolve_url("https://spotify.com/track/test123")

            assert len(songs) == 1
            assert songs[0].name == "Test Song"
            assert songs[0].platform == Platform.SPOTIFY

    @pytest.mark.asyncio
    async def test_resolve_url_cached(self, client: APIClient) -> None:
        """Test URL resolution uses cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "songs": [
                {
                    "name": "Test Song",
                    "artists": ["Artist1"],
                    "artist": "Artist1",
                    "duration": 180,
                    "platform": "spotify",
                    "platform_id": "test123",
                    "url": "https://spotify.com/track/test123",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            # First call
            await client.resolve_url("https://spotify.com/track/test123")
            # Second call should use cache
            await client.resolve_url("https://spotify.com/track/test123")

            # Should only call the API once
            assert mock_http.get.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_url_not_found(self, client: APIClient) -> None:
        """Test URL resolution with not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.resolve_url("https://invalid.url/xyz")

    @pytest.mark.asyncio
    async def test_resolve_url_connection_error(self, client: APIClient) -> None:
        """Test URL resolution with connection error."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("Failed"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError):
                await client.resolve_url("https://spotify.com/track/test")

    @pytest.mark.asyncio
    async def test_resolve_url_http_error(self, client: APIClient) -> None:
        """Test URL resolution with HTTP status error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(APIError):
                await client.resolve_url("https://spotify.com/track/test")

    @pytest.mark.asyncio
    async def test_search_success(self, client: APIClient) -> None:
        """Test successful search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "songs": [
                {
                    "name": "Found Song",
                    "artists": ["Artist"],
                    "artist": "Artist",
                    "duration": 200,
                    "platform": "spotify",
                    "platform_id": "found123",
                    "url": "https://spotify.com/track/found123",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            songs = await client.search("test query")

            assert len(songs) == 1
            assert songs[0].name == "Found Song"

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, client: APIClient) -> None:
        """Test search with pagination parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"songs": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query", limit=50, offset=20)

            mock_http.get.assert_called_once()
            call_kwargs = mock_http.get.call_args
            assert call_kwargs.kwargs["params"]["limit"] == 50
            assert call_kwargs.kwargs["params"]["offset"] == 20

    @pytest.mark.asyncio
    async def test_search_with_platform(self, client: APIClient) -> None:
        """Test search with specific platform."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"songs": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query", platform=Platform.DEEZER)

            call_kwargs = mock_http.get.call_args
            assert call_kwargs.kwargs["params"]["platform"] == "deezer"

    @pytest.mark.asyncio
    async def test_search_cached(self, client: APIClient) -> None:
        """Test search uses cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"songs": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query")
            await client.search("query")

            assert mock_http.get.call_count == 1

    @pytest.mark.asyncio
    async def test_universal_search_success(self, client: APIClient) -> None:
        """Test successful universal search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "query_type": "text",
            "results": [
                {
                    "id": "track1",
                    "entity_type": "track",
                    "name": "Test Track",
                    "subtitle": "Artist",
                    "platforms": [
                        {"platform": "spotify", "platform_id": "id1", "url": "url1"}
                    ],
                },
                {
                    "id": "artist1",
                    "entity_type": "artist",
                    "name": "Test Artist",
                    "platforms": [],
                },
            ],
            "entities_created": 0,
            "total": 2,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.universal_search("test")

            assert result.query == "test"
            assert len(result.results) == 2
            assert len(result.tracks) == 1
            assert len(result.artists) == 1

    @pytest.mark.asyncio
    async def test_universal_search_with_entity_types(self, client: APIClient) -> None:
        """Test universal search with entity type filter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "query_type": "text",
            "results": [],
            "entities_created": 0,
            "total": 0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.universal_search(
                "test", entity_types=[EntityType.TRACK, EntityType.ALBUM]
            )

            call_kwargs = mock_http.post.call_args
            assert "entity_types" in call_kwargs.kwargs["json"]

    @pytest.mark.asyncio
    async def test_find_matches_success(
        self, client: APIClient, sample_song
    ) -> None:
        """Test successful match finding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {
                    "target_platform": "youtube",
                    "score": 95.0,
                    "result": {
                        "name": "Test Song",
                        "artists": ["Artist"],
                        "artist": "Artist",
                        "duration": 182,
                        "platform": "youtube",
                        "platform_id": "abc123",
                        "url": "https://youtube.com/watch?v=abc123",
                        "verified": True,
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.find_matches(sample_song)

            assert len(matches) == 1
            assert matches[0].platform == TargetPlatform.YOUTUBE
            assert matches[0].verified is True
            assert matches[0].score == 95.0

    @pytest.mark.asyncio
    async def test_find_matches_with_platforms(
        self, client: APIClient, sample_song
    ) -> None:
        """Test match finding with specific platforms."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.find_matches(
                sample_song,
                target_platforms=[TargetPlatform.SOUNDCLOUD],
            )

            call_kwargs = mock_http.post.call_args
            assert "soundcloud" in call_kwargs.kwargs["json"]["target_platforms"]

    @pytest.mark.asyncio
    async def test_find_matches_no_results(
        self, client: APIClient, sample_song
    ) -> None:
        """Test match finding with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.find_matches(sample_song)
            assert matches == []

    @pytest.mark.asyncio
    async def test_submit_match_success(self, client: APIClient) -> None:
        """Test successful match submission."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "match-123",
            "source_url": "https://spotify.com/track/test",
            "target_url": "https://youtube.com/watch?v=abc",
            "target_platform": "youtube",
            "score": 0.0,
            "confidence": 0.0,
            "match_type": "user",
            "status": "pending",
            "upvotes": 0,
            "downvotes": 0,
            "net_votes": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "result": {
                "name": "Test Song",
                "artists": ["Artist"],
                "artist": "Artist",
                "duration": 182,
                "platform": "youtube",
                "platform_id": "abc123",
                "url": "https://youtube.com/watch?v=abc",
                "verified": False,
            },
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.submit_match(
                "https://spotify.com/track/test",
                "https://youtube.com/watch?v=abc",
            )

            assert result.id == "match-123"
            assert result.target_url == "https://youtube.com/watch?v=abc"

    @pytest.mark.asyncio
    async def test_get_song_matches_success(
        self, client: APIClient, sample_song
    ) -> None:
        """Test fetching matches for a song."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "match-1",
                "source_url": "https://spotify.com/track/test",
                "target_url": "https://youtube.com/watch?v=abc",
                "target_platform": "youtube",
                "score": 82.0,
                "confidence": 0.82,
                "match_type": "system",
                "status": "verified",
                "upvotes": 2,
                "downvotes": 0,
                "net_votes": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "result": {
                    "name": "Test Song",
                    "artists": ["Artist"],
                    "artist": "Artist",
                    "duration": 182,
                    "platform": "youtube",
                    "platform_id": "abc123",
                    "url": "https://youtube.com/watch?v=abc",
                    "verified": True,
                },
            }
        ]
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.get_song_matches("song-123", sample_song)

            assert len(matches) == 1
            assert matches[0].id == "match-1"
            assert matches[0].net_votes == 2

    @pytest.mark.asyncio
    async def test_get_match_votes_success(self, client: APIClient) -> None:
        """Test fetching match votes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "match_id": "match-1",
            "upvotes": 3,
            "downvotes": 1,
            "score": 2,
            "total_votes": 4,
            "confidence": 0.7,
            "user_vote": "up",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_match_votes("match-1")

            assert result["upvotes"] == 3
            assert result["user_vote"] == "up"

    @pytest.mark.asyncio
    async def test_create_report_success(self, client: APIClient) -> None:
        """Test submitting a report."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "report-1"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.create_report(
                entity_type="song",
                entity_id="song-1",
                field_name="name",
                current_value="Old",
                suggested_value="New",
            )

            assert result["id"] == "report-1"

    @pytest.mark.asyncio
    async def test_get_track_success(self, client: APIClient) -> None:
        """Test getting track details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "track123",
            "name": "Test Track",
            "artists": ["Artist"],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_track("track123")

            assert result["name"] == "Test Track"

    @pytest.mark.asyncio
    async def test_get_track_not_found(self, client: APIClient) -> None:
        """Test getting track that doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_track("nonexistent")

    @pytest.mark.asyncio
    async def test_get_track_cached(self, client: APIClient) -> None:
        """Test track details are cached."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "track123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.get_track("track123")
            await client.get_track("track123")

            assert mock_http.get.call_count == 1

    @pytest.mark.asyncio
    async def test_get_track_no_cache(self, client: APIClient) -> None:
        """Test getting track without cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "track123"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.get_track("track123", use_cache=False)
            await client.get_track("track123", use_cache=False)

            assert mock_http.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_album_success(self, client: APIClient) -> None:
        """Test getting album details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "album123",
            "name": "Test Album",
            "tracks": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_album("album123")

            assert result["name"] == "Test Album"

    @pytest.mark.asyncio
    async def test_get_album_not_found(self, client: APIClient) -> None:
        """Test getting album that doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_album("nonexistent")

    @pytest.mark.asyncio
    async def test_get_artist_success(self, client: APIClient) -> None:
        """Test getting artist details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "artist123",
            "name": "Test Artist",
            "albums": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_artist("artist123")

            assert result["name"] == "Test Artist"

    @pytest.mark.asyncio
    async def test_get_artist_not_found(self, client: APIClient) -> None:
        """Test getting artist that doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_artist("nonexistent")

    @pytest.mark.asyncio
    async def test_get_playlist_success(self, client: APIClient) -> None:
        """Test getting playlist details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "playlist123",
            "name": "Test Playlist",
            "tracks": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_playlist("playlist123")

            assert result["name"] == "Test Playlist"

    @pytest.mark.asyncio
    async def test_get_playlist_not_found(self, client: APIClient) -> None:
        """Test getting playlist that doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_playlist("nonexistent")

    @pytest.mark.asyncio
    async def test_get_lyrics_success(self, client: APIClient) -> None:
        """Test getting lyrics."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lyrics_text": "Test lyrics here",
            "lyrics_synced": True,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_lyrics("track123")

            assert result["lyrics_text"] == "Test lyrics here"
            assert result["lyrics_synced"] is True

    @pytest.mark.asyncio
    async def test_get_lyrics_not_found(self, client: APIClient) -> None:
        """Test getting lyrics when not found returns empty."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            )
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_lyrics("track123")

            assert result["lyrics_text"] is None
            assert result["lyrics_synced"] is None

    @pytest.mark.asyncio
    async def test_get_all_lyrics_success(self, client: APIClient) -> None:
        """Test getting lyrics from all sources."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sources": [
                {"source": "genius", "lyrics_text": "Test lyrics"},
                {"source": "azlyrics", "lyrics_text": "More lyrics"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_all_lyrics("track123")

            assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    async def test_search_lyrics_not_found(self, client: APIClient) -> None:
        """Test searching lyrics when not found returns empty."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            )
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.search_lyrics("Track", "Artist")

            assert result["lyrics_text"] is None
            assert result["lyrics_synced"] is None

    @pytest.mark.asyncio
    async def test_get_metadata_sources_success(self, client: APIClient) -> None:
        """Test getting metadata sources."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sources": ["musicbrainz", "spotify"]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_metadata_sources()

            assert "musicbrainz" in result.get("sources", [])

    @pytest.mark.asyncio
    async def test_close(self, client: APIClient) -> None:
        """Test closing the client."""
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_already_closed(self, client: APIClient) -> None:
        """Test closing an already closed client."""
        mock_http = AsyncMock()
        mock_http.is_closed = True
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_no_client(self, client: APIClient) -> None:
        """Test closing when no client exists."""
        client._client = None
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_clear_cache(self, client: APIClient) -> None:
        """Test clearing the cache."""
        # Populate cache
        await client._cache.set("value", "key")
        assert await client._cache.get("key") is not None

        await client.clear_cache()

        assert await client._cache.get("key") is None

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self, client: APIClient) -> None:
        """Test _get_client creates new client when needed."""
        assert client._client is None

        with patch("spotdl_cli.core.api_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance

            result = await client._get_client()

            assert result == mock_instance
            mock_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_sets_auth_header(self, settings: Settings) -> None:
        """Test _get_client includes auth header when configured."""
        settings.auth_token = "test-token"
        client = APIClient(settings)

        with patch("spotdl_cli.core.api_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance

            await client._get_client()

            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self, client: APIClient) -> None:
        """Test _get_client reuses existing client."""
        mock_http = AsyncMock()
        mock_http.is_closed = False
        client._client = mock_http

        result = await client._get_client()

        assert result == mock_http

    @pytest.mark.asyncio
    async def test_get_client_recreates_when_closed(self, client: APIClient) -> None:
        """Test _get_client recreates client when closed."""
        mock_http = AsyncMock()
        mock_http.is_closed = True
        client._client = mock_http

        with patch("spotdl_cli.core.api_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance

            result = await client._get_client()

            assert result == mock_instance


class TestGetApiClient:
    """Tests for get_api_client function."""

    def test_get_api_client_singleton(self) -> None:
        """Test get_api_client returns singleton."""
        with patch("spotdl_cli.core.api_client._api_client", None):
            client1 = get_api_client()
            client2 = get_api_client()
            assert client1 is client2
