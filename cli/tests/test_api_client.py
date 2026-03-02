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
        """Test successful URL resolution via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [
                {
                    "id": "entity-1",
                    "type": "track",
                    "name": "Test Song",
                    "canonical": {
                        "name": "Test Song",
                        "artists": ["Artist1"],
                        "artist": "Artist1",
                        "duration": 180,
                        "platform": "spotify",
                        "platform_id": "test123",
                        "url": "https://spotify.com/track/test123",
                    },
                    "capabilities": {},
                    "quality_score": 0.9,
                    "last_merged_at": "2024-01-01T00:00:00Z",
                    "merge_version": 1,
                }
            ],
            "total": 1,
            "entities_created": 1,
            "query": "https://spotify.com/track/test123",
            "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
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
            "entities": [
                {
                    "id": "entity-1",
                    "type": "track",
                    "name": "Test Song",
                    "canonical": {
                        "name": "Test Song",
                        "artists": ["Artist1"],
                        "artist": "Artist1",
                        "duration": 180,
                        "platform": "spotify",
                        "platform_id": "test123",
                        "url": "https://spotify.com/track/test123",
                    },
                    "capabilities": {},
                    "quality_score": 0.9,
                    "last_merged_at": "2024-01-01T00:00:00Z",
                    "merge_version": 1,
                }
            ],
            "total": 1,
            "entities_created": 0,
            "query": "",
            "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.resolve_url("https://spotify.com/track/test123")
            await client.resolve_url("https://spotify.com/track/test123")

            assert mock_http.post.call_count == 1

    @pytest.mark.asyncio
    async def test_resolve_url_not_found(self, client: APIClient) -> None:
        """Test URL resolution with not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.resolve_url("https://invalid.url/xyz")

    @pytest.mark.asyncio
    async def test_resolve_url_connection_error(self, client: APIClient) -> None:
        """Test URL resolution with connection error."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("Failed"))
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
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(APIError):
                await client.resolve_url("https://spotify.com/track/test")

    @pytest.mark.asyncio
    async def test_search_success(self, client: APIClient) -> None:
        """Test successful search via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [
                {
                    "id": "entity-2",
                    "type": "track",
                    "name": "Found Song",
                    "canonical": {
                        "name": "Found Song",
                        "artists": ["Artist"],
                        "artist": "Artist",
                        "duration": 200,
                        "platform": "spotify",
                        "platform_id": "found123",
                        "url": "https://spotify.com/track/found123",
                    },
                    "capabilities": {},
                    "quality_score": 0.9,
                    "last_merged_at": "2024-01-01T00:00:00Z",
                    "merge_version": 1,
                }
            ],
            "total": 1,
            "entities_created": 0,
            "query": "test query",
            "query_type": "text",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            songs = await client.search("test query")

            assert len(songs) == 1
            assert songs[0].name == "Found Song"

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, client: APIClient) -> None:
        """Test search with limit parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [], "total": 0, "entities_created": 0,
            "query": "query", "query_type": "text", "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query", limit=50, offset=20)

            mock_http.post.assert_called_once()
            call_kwargs = mock_http.post.call_args
            assert call_kwargs.kwargs["json"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_search_with_platform(self, client: APIClient) -> None:
        """Test search with specific platform sends providers hint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [], "total": 0, "entities_created": 0,
            "query": "query", "query_type": "text", "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query", platform=Platform.DEEZER)

            call_kwargs = mock_http.post.call_args
            assert "deezer" in call_kwargs.kwargs["json"]["providers"]

    @pytest.mark.asyncio
    async def test_search_cached(self, client: APIClient) -> None:
        """Test search uses cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [], "total": 0, "entities_created": 0,
            "query": "query", "query_type": "text", "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.search("query")
            await client.search("query")

            assert mock_http.post.call_count == 1

    @pytest.mark.asyncio
    async def test_universal_search_success(self, client: APIClient) -> None:
        """Test successful universal search via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "query_type": "text",
            "entities": [
                {
                    "id": "track1",
                    "type": "track",
                    "name": "Test Track",
                    "canonical": {"name": "Test Track", "artist": "Artist"},
                    "capabilities": {},
                    "quality_score": 0.9,
                    "last_merged_at": "2024-01-01T00:00:00Z",
                    "merge_version": 1,
                },
                {
                    "id": "artist1",
                    "type": "artist",
                    "name": "Test Artist",
                    "canonical": {"name": "Test Artist"},
                    "capabilities": {},
                    "quality_score": 0.8,
                    "last_merged_at": "2024-01-01T00:00:00Z",
                    "merge_version": 1,
                },
            ],
            "entities_created": 0,
            "total": 2,
            "top_relations": {},
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
        """Test universal search with entity type filter sends types."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "query": "test",
            "query_type": "text",
            "entities": [],
            "entities_created": 0,
            "total": 0,
            "top_relations": {},
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
            assert "types" in call_kwargs.kwargs["json"]

    @pytest.mark.asyncio
    async def test_find_matches_success(
        self, client: APIClient, sample_song
    ) -> None:
        """Test successful match finding via relations:discover.

        sample_song has song_id set (from __post_init__), so discover is skipped
        and relations:discover is called directly.
        """
        relations_response = MagicMock()
        relations_response.status_code = 200
        relations_response.json.return_value = {
            "entity_id": sample_song.song_id,
            "relations": [
                {
                    "id": "rel-1",
                    "from_entity_id": sample_song.song_id,
                    "to_entity_id": "target-1",
                    "relation_type": "audio_match",
                    "match_score": 95.0,
                    "confidence": 0.95,
                    "status": "confirmed",
                    "discovered_by": "system",
                    "upvotes": 0, "downvotes": 0, "net_votes": 0,
                    "relation_data": {},
                    "target": {
                        "id": "target-1",
                        "type": "track",
                        "name": "Test Song",
                        "canonical": {
                            "name": "Test Song",
                            "artists": ["Artist"],
                            "artist": "Artist",
                            "duration": 182,
                            "platform": "youtube",
                            "platform_id": "abc123",
                            "url": "https://youtube.com/watch?v=abc123",
                        },
                        "capabilities": {},
                        "quality_score": 0.8,
                        "last_merged_at": "",
                        "merge_version": 1,
                    },
                }
            ],
            "total": 1,
        }
        relations_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=relations_response)
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
        """Test match finding passes target_providers to relations:discover."""
        relations_response = MagicMock()
        relations_response.status_code = 200
        relations_response.json.return_value = {
            "entity_id": sample_song.song_id, "relations": [], "total": 0,
        }
        relations_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=relations_response)
            mock_get.return_value = mock_http

            await client.find_matches(
                sample_song,
                target_platforms=[TargetPlatform.SOUNDCLOUD],
            )

            call_kwargs = mock_http.post.call_args
            assert "soundcloud" in call_kwargs.kwargs["json"]["target_providers"]

    @pytest.mark.asyncio
    async def test_find_matches_no_results(
        self, client: APIClient, sample_song
    ) -> None:
        """Test match finding with no results from relations:discover."""
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
        """Test successful match submission via discover + create relation."""
        discover_response = MagicMock()
        discover_response.status_code = 200
        discover_response.json.return_value = {
            "entities": [{"id": "entity-1", "type": "track", "name": "Test",
                          "canonical": {}, "capabilities": {}, "quality_score": 0.9,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        discover_response.raise_for_status = MagicMock()

        relation_response = MagicMock()
        relation_response.status_code = 200
        relation_response.json.return_value = {
            "id": "rel-123",
            "from_entity_id": "entity-1",
            "to_entity_id": "target-1",
            "relation_type": "audio_match",
            "match_score": None,
            "confidence": 0.0,
            "status": "pending",
            "discovered_by": "user",
            "upvotes": 0, "downvotes": 0, "net_votes": 0,
            "relation_data": {},
            "target": {
                "id": "target-1",
                "type": "track",
                "name": "Test Song",
                "canonical": {
                    "name": "Test Song",
                    "platform": "youtube",
                    "platform_id": "abc123",
                    "url": "https://youtube.com/watch?v=abc",
                },
                "capabilities": {},
                "quality_score": 0.5,
                "last_merged_at": "",
                "merge_version": 1,
            },
        }
        relation_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(
                side_effect=[discover_response, relation_response]
            )
            mock_get.return_value = mock_http

            result = await client.submit_match(
                "https://spotify.com/track/test",
                "https://youtube.com/watch?v=abc",
            )

            assert result.id == "rel-123"
            assert result.target_url == "https://youtube.com/watch?v=abc"

    @pytest.mark.asyncio
    async def test_get_song_matches_success(
        self, client: APIClient, sample_song
    ) -> None:
        """Test fetching matches for a song via GET /entities/{id}/relations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entity_id": "song-123",
            "relations": [
                {
                    "id": "rel-1",
                    "from_entity_id": "song-123",
                    "to_entity_id": "target-1",
                    "relation_type": "audio_match",
                    "match_score": 82.0,
                    "confidence": 0.82,
                    "status": "confirmed",
                    "discovered_by": "system",
                    "upvotes": 2, "downvotes": 0, "net_votes": 2,
                    "relation_data": {},
                    "target": {
                        "id": "target-1",
                        "type": "track",
                        "name": "Test Song",
                        "canonical": {
                            "name": "Test Song",
                            "artists": ["Artist"],
                            "artist": "Artist",
                            "duration": 182,
                            "platform": "youtube",
                            "platform_id": "abc123",
                            "url": "https://youtube.com/watch?v=abc",
                        },
                        "capabilities": {},
                        "quality_score": 0.8,
                        "last_merged_at": "",
                        "merge_version": 1,
                    },
                }
            ],
            "total": 1,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            matches = await client.get_song_matches("song-123", sample_song)

            assert len(matches) == 1
            assert matches[0].id == "rel-1"

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
        """Test getting track details via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "track123", "type": "track", "name": "Test Track",
                          "canonical": {"name": "Test Track", "artists": ["Artist"]},
                          "capabilities": {}, "quality_score": 0.9,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
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
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_track("nonexistent")

    @pytest.mark.asyncio
    async def test_get_track_cached(self, client: APIClient) -> None:
        """Test track details are cached."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "track123", "type": "track", "name": "T",
                          "canonical": {}, "capabilities": {}, "quality_score": 0.9,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.get_track("track123")
            await client.get_track("track123")
            assert mock_http.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_track_no_cache(self, client: APIClient) -> None:
        """Test getting track without cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "track123", "type": "track", "name": "T",
                          "canonical": {}, "capabilities": {}, "quality_score": 0.9,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            await client.get_track("track123", use_cache=False)
            await client.get_track("track123", use_cache=False)
            assert mock_http.post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_album_success(self, client: APIClient) -> None:
        """Test getting album details via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "album123", "type": "album", "name": "Test Album",
                          "canonical": {"name": "Test Album"},
                          "capabilities": {}, "quality_score": 0.9,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
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
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_album("nonexistent")

    @pytest.mark.asyncio
    async def test_get_artist_success(self, client: APIClient) -> None:
        """Test getting artist details via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "artist123", "type": "artist", "name": "Test Artist",
                          "canonical": {"name": "Test Artist"},
                          "capabilities": {}, "quality_score": 0.8,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
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
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(NotFoundError):
                await client.get_artist("nonexistent")

    @pytest.mark.asyncio
    async def test_get_playlist_success(self, client: APIClient) -> None:
        """Test getting playlist details via POST /entities/discover."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entities": [{"id": "playlist123", "type": "playlist",
                          "name": "Test Playlist",
                          "canonical": {"name": "Test Playlist"},
                          "capabilities": {}, "quality_score": 0.7,
                          "last_merged_at": "", "merge_version": 1}],
            "total": 1, "entities_created": 0, "query": "", "query_type": "url",
            "top_relations": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
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
            mock_http.post = AsyncMock(return_value=mock_response)
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

            result = await client.get_metadata_sources("song123")

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
        """Test _get_client creates new client via BackendManager."""
        assert client._client is None

        mock_http = AsyncMock()
        with patch("spotdl_cli.core.backend.get_backend_manager") as mock_mgr:
            mock_mgr.return_value.create_client.return_value = mock_http

            result = await client._get_client()

            assert result == mock_http
            mock_mgr.return_value.create_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_sets_auth_header(self, settings: Settings) -> None:
        """Test _get_client uses BackendManager which includes auth when configured."""
        settings.auth_token = "test-token"
        settings.backend_mode = "remote"
        client = APIClient(settings)

        # BackendManager.create_client() handles auth headers for remote mode
        mock_http = AsyncMock()
        with patch("spotdl_cli.core.backend.get_backend_manager") as mock_mgr:
            mock_mgr.return_value.create_client.return_value = mock_http

            result = await client._get_client()

            assert result == mock_http

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

        new_mock_http = AsyncMock()
        with patch("spotdl_cli.core.backend.get_backend_manager") as mock_mgr:
            mock_mgr.return_value.create_client.return_value = new_mock_http

            result = await client._get_client()

            assert result == new_mock_http


class TestAPIClientAuth:
    """Tests for APIClient auth methods."""

    @pytest.fixture
    def client(self, settings: Settings) -> APIClient:
        """Create test API client with a mock-friendly settings object."""
        client = APIClient(settings)
        # Replace pydantic settings with a MagicMock so .save() works
        mock_settings = MagicMock()
        mock_settings.api_url = settings.api_url
        mock_settings.offline_mode = settings.offline_mode
        mock_settings.api_timeout = settings.api_timeout
        mock_settings.auth_token = settings.auth_token
        mock_settings.audio_providers = []
        client._settings = mock_settings
        return client

    @pytest.mark.asyncio
    async def test_login_success(self, client: APIClient) -> None:
        """Verify POST to /api/v1/auth/login, token saved, client closed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token-123",
            "refresh_token": "refresh-456",
            "user": {"username": "testuser"},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.is_closed = False
            mock_http.aclose = AsyncMock()
            mock_get.return_value = mock_http

            result = await client.login("testuser", "password123")

            assert result["access_token"] == "new-token-123"
            assert client._settings.auth_token == "new-token-123"
            client._settings.save.assert_called()
            mock_http.post.assert_called_once_with(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "password123"},
            )

    @pytest.mark.asyncio
    async def test_login_missing_token(self, client: APIClient) -> None:
        """Regression: response without access_token raises APIError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"username": "testuser"}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(APIError, match="missing access_token"):
                await client.login("testuser", "password123")

    @pytest.mark.asyncio
    async def test_login_connection_error(self, client: APIClient) -> None:
        """ConnectError raised as ConnectionError."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("Failed"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError):
                await client.login("user", "pass")

    @pytest.mark.asyncio
    async def test_login_http_error(self, client: APIClient) -> None:
        """HTTPStatusError raised as APIError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )
        )

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(APIError, match="Login failed"):
                await client.login("user", "wrong")

    @pytest.mark.asyncio
    async def test_register_success(self, client: APIClient) -> None:
        """Verify POST to /api/v1/auth/register, token saved."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "reg-token-123",
            "user": {"username": "newuser"},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_http.is_closed = False
            mock_http.aclose = AsyncMock()
            mock_get.return_value = mock_http

            result = await client.register("newuser", "new@example.com", "password123")

            assert result["access_token"] == "reg-token-123"
            assert client._settings.auth_token == "reg-token-123"
            client._settings.save.assert_called()
            mock_http.post.assert_called_once_with(
                "/api/v1/auth/register",
                json={"username": "newuser", "email": "new@example.com", "password": "password123"},
            )

    @pytest.mark.asyncio
    async def test_register_missing_token(self, client: APIClient) -> None:
        """Regression: response without access_token raises APIError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"username": "newuser"}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(APIError, match="missing access_token"):
                await client.register("newuser", "new@example.com", "pass")

    @pytest.mark.asyncio
    async def test_register_connection_error(self, client: APIClient) -> None:
        """Connection error handling."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("Failed"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError):
                await client.register("user", "email@test.com", "pass")

    @pytest.mark.asyncio
    async def test_get_me_success(self, client: APIClient) -> None:
        """Verify GET to /api/v1/auth/me."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "username": "testuser",
            "email": "test@example.com",
            "is_admin": False,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.get_me()

            assert result["username"] == "testuser"
            mock_http.get.assert_called_once_with("/api/v1/auth/me")

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: APIClient) -> None:
        """Verify PUT to /api/v1/auth/password."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Password updated"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.put = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            result = await client.change_password("oldpass", "newpass123")

            assert result["message"] == "Password updated"
            mock_http.put.assert_called_once_with(
                "/api/v1/auth/password",
                json={"current_password": "oldpass", "new_password": "newpass123"},
            )

    @pytest.mark.asyncio
    async def test_delete_account_success(self, client: APIClient) -> None:
        """Verify DELETE to /api/v1/auth/me, token cleared."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.delete = AsyncMock(return_value=mock_response)
            mock_http.is_closed = False
            mock_http.aclose = AsyncMock()
            mock_get.return_value = mock_http

            await client.delete_account()

            assert client._settings.auth_token is None
            client._settings.save.assert_called()
            mock_http.delete.assert_called_once_with("/api/v1/auth/me")

    @pytest.mark.asyncio
    async def test_logout_success(self, client: APIClient) -> None:
        """Verify POST to /api/v1/auth/logout, token cleared."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock()
            mock_http.is_closed = False
            mock_http.aclose = AsyncMock()
            mock_get.return_value = mock_http

            await client.logout()

            assert client._settings.auth_token is None
            client._settings.save.assert_called()

    @pytest.mark.asyncio
    async def test_logout_ignores_errors(self, client: APIClient) -> None:
        """Verify logout succeeds even on API errors."""
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.HTTPError("Error"))
            mock_http.is_closed = False
            mock_http.aclose = AsyncMock()
            mock_get.return_value = mock_http

            # Should not raise
            await client.logout()

            assert client._settings.auth_token is None


class TestGetApiClient:
    """Tests for get_api_client function."""

    def test_get_api_client_singleton(self) -> None:
        """Test get_api_client returns singleton."""
        with patch("spotdl_cli.core.api_client._api_client", None):
            client1 = get_api_client()
            client2 = get_api_client()
            assert client1 is client2
