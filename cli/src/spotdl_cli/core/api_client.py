"""API client for communicating with the SpotDL backend."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, TypeVar

import httpx

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core.types import (
    DownloadResult,
    EntityType,
    Platform,
    Song,
    TargetPlatform,
    UniversalSearchResponse,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class APIError(Exception):
    """Base exception for API errors."""


class ConnectionError(APIError):
    """Raised when cannot connect to the API."""


class NotFoundError(APIError):
    """Raised when a resource is not found."""


class CacheEntry:
    """Cache entry with TTL support."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class ResponseCache:
    """Simple in-memory cache with TTL and max size."""

    def __init__(self, max_size: int = 500, default_ttl: float = 300.0) -> None:
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def _make_key(self, *args: Any) -> str:
        """Create cache key from arguments."""
        key_data = ":".join(str(a) for a in args)
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, *args: Any) -> Any | None:
        """Get value from cache if not expired."""
        key = self._make_key(*args)
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                del self._cache[key]
                return None
            return entry.value

    async def set(self, value: Any, *args: Any, ttl: float | None = None) -> None:
        """Set value in cache with TTL."""
        key = self._make_key(*args)
        async with self._lock:
            # Evict oldest entries if at max size
            if len(self._cache) >= self._max_size:
                # Remove 20% oldest entries
                entries_to_remove = self._max_size // 5
                oldest_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].expires_at,
                )[:entries_to_remove]
                for k in oldest_keys:
                    del self._cache[k]

            self._cache[key] = CacheEntry(value, ttl or self._default_ttl)

    async def invalidate(self, *args: Any) -> None:
        """Invalidate a cache entry."""
        key = self._make_key(*args)
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()


class APIClient:
    """
    Client for the SpotDL backend API.

    Features:
    - Connection pooling with HTTP/2 support
    - Response caching with TTL
    - Pagination support

    Provides methods to:
    - Resolve URLs to songs
    - Search for songs
    - Find matches (download URLs)
    - Check server health
    """

    # Cache TTL values (seconds)
    CACHE_TTL_SEARCH = 120.0  # 2 minutes for search
    CACHE_TTL_DETAIL = 300.0  # 5 minutes for detail pages
    CACHE_TTL_LYRICS = 3600.0  # 1 hour for lyrics (rarely changes)
    CACHE_TTL_FEATURES = 3600.0  # 1 hour for audio features

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the API client.

        Args:
            settings: Settings instance (uses global if not provided)
        """
        self._settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None
        self._cache = ResponseCache(max_size=500, default_ttl=300.0)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_url,
                timeout=self._settings.api_timeout,
                headers={
                    "User-Agent": "SpotDL-CLI/5.0.0",
                    "Accept": "application/json",
                },
                # Connection pooling
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0,
                ),
                # Enable HTTP/2
                http2=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def clear_cache(self) -> None:
        """Clear all cached responses."""
        await self._cache.clear()

    async def health_check(self) -> bool:
        """
        Check if the backend is healthy.

        Returns:
            True if backend is healthy
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def is_online(self) -> bool:
        """
        Check if we can connect to the backend.

        Returns:
            True if backend is reachable
        """
        if self._settings.offline_mode:
            return False
        return await self.health_check()

    async def resolve_url(self, url: str) -> list[Song]:
        """
        Resolve a URL to songs.

        Args:
            url: URL to resolve (Spotify, Deezer, etc.)

        Returns:
            List of Song objects

        Raises:
            APIError: If request fails
            NotFoundError: If URL not supported
        """
        # Check cache
        cached = await self._cache.get("resolve", url)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/songs/resolve",
                params={"url": url},
            )

            if response.status_code == 404:
                raise NotFoundError(f"URL not supported: {url}")

            response.raise_for_status()
            data = response.json()

            result = [Song.from_dict(s) for s in data.get("songs", [])]

            # Cache result
            await self._cache.set(result, "resolve", url, ttl=self.CACHE_TTL_DETAIL)
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def search(
        self,
        query: str,
        platform: Platform = Platform.SPOTIFY,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Song]:
        """
        Search for songs with pagination support.

        Args:
            query: Search query
            platform: Platform to search on
            limit: Maximum results per page
            offset: Offset for pagination

        Returns:
            List of matching Song objects
        """
        # Check cache
        cached = await self._cache.get("search", query, platform.value, limit, offset)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/songs/search",
                params={
                    "q": query,
                    "platform": platform.value,
                    "limit": limit,
                    "offset": offset,
                },
            )

            response.raise_for_status()
            data = response.json()

            result = [Song.from_dict(s) for s in data.get("songs", [])]

            # Cache result
            await self._cache.set(
                result, "search", query, platform.value, limit, offset,
                ttl=self.CACHE_TTL_SEARCH
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def universal_search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> UniversalSearchResponse:
        """
        Universal search returning all entity types with pagination.

        Args:
            query: Search query or URL
            entity_types: Optional filter for entity types
            limit: Maximum results per page
            offset: Offset for pagination

        Returns:
            UniversalSearchResponse with artists, albums, tracks, playlists
        """
        # Build cache key
        et_key = ",".join(sorted(et.value for et in entity_types)) if entity_types else ""
        cached = await self._cache.get("universal", query, et_key, limit, offset)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

            body: dict[str, Any] = {
                "query": query,
                "limit": limit,
                "offset": offset,
            }
            if entity_types:
                body["entity_types"] = [et.value for et in entity_types]

            response = await client.post(
                "/api/v1/search",
                json=body,
            )

            response.raise_for_status()
            data = response.json()

            result = UniversalSearchResponse.from_dict(data)

            # Cache result
            await self._cache.set(
                result, "universal", query, et_key, limit, offset,
                ttl=self.CACHE_TTL_SEARCH
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def find_matches(
        self,
        song: Song,
        target_platforms: list[TargetPlatform] | None = None,
        limit: int = 5,
    ) -> list[DownloadResult]:
        """
        Find download matches for a song.

        Args:
            song: Song to find matches for
            target_platforms: Platforms to search (defaults to all)
            limit: Maximum matches per platform

        Returns:
            List of DownloadResult objects
        """
        # Check cache
        platforms_key = ",".join(
            p.value for p in (target_platforms or [TargetPlatform.YOUTUBE])
        )
        cached = await self._cache.get("matches", song.url, platforms_key, limit)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

            platforms = target_platforms or [
                TargetPlatform.YOUTUBE,
                TargetPlatform.YOUTUBE_MUSIC,
            ]

            response = await client.post(
                "/api/v1/matches/find",
                json={
                    "source_url": song.url,
                    "target_platforms": [p.value for p in platforms],
                    "limit": limit,
                },
            )

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            results = []
            for match in data.get("matches", []):
                result = DownloadResult(
                    name=match.get("name", song.name),
                    artists=match.get("artists", song.artists),
                    artist=match.get("artist", song.artist),
                    duration=match.get("duration", song.duration),
                    platform=TargetPlatform(match.get("target_platform", "youtube")),
                    platform_id=match.get("platform_id", ""),
                    url=match.get("url", ""),
                    verified=match.get("verified", False),
                    score=match.get("score", 0.0),
                    cover_url=match.get("cover_url"),
                )
                results.append(result)

            # Cache result
            await self._cache.set(
                results, "matches", song.url, platforms_key, limit,
                ttl=self.CACHE_TTL_SEARCH
            )
            return results

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def submit_match(
        self,
        source_url: str,
        target_url: str,
    ) -> dict[str, Any]:
        """
        Submit a user-discovered match.

        Args:
            source_url: Source song URL
            target_url: Target download URL

        Returns:
            Match submission result
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/matches/submit",
                json={
                    "source_url": source_url,
                    "target_url": target_url,
                },
            )

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    # ============== Detail Endpoints ==============

    async def get_track(
        self, track_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed information about a track.

        Args:
            track_id: Track ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Track details including metadata, matches, lyrics, audio features
        """
        if use_cache:
            cached = await self._cache.get("track", platform, track_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Track not found: {track_id}")

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "track", platform, track_id, ttl=self.CACHE_TTL_DETAIL
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_album(
        self, album_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed information about an album.

        Args:
            album_id: Album ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Album details including tracks, metadata
        """
        if use_cache:
            cached = await self._cache.get("album", platform, album_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/albums/{platform}/{album_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "album", platform, album_id, ttl=self.CACHE_TTL_DETAIL
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_artist(
        self, artist_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed information about an artist.

        Args:
            artist_id: Artist ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Artist details including albums, top tracks
        """
        if use_cache:
            cached = await self._cache.get("artist", platform, artist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/artists/{platform}/{artist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "artist", platform, artist_id, ttl=self.CACHE_TTL_DETAIL
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_playlist(
        self, playlist_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed information about a playlist.

        Args:
            playlist_id: Playlist ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Playlist details including tracks
        """
        if use_cache:
            cached = await self._cache.get("playlist", platform, playlist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/playlists/{platform}/{playlist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "playlist", platform, playlist_id, ttl=self.CACHE_TTL_DETAIL
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_lyrics(
        self, track_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get lyrics for a track.

        Args:
            track_id: Track ID on the platform
            platform: Platform name
            use_cache: Whether to use cached response

        Returns:
            Lyrics data including synced and plain text
        """
        if use_cache:
            cached = await self._cache.get("lyrics", platform, track_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}/lyrics",
            )

            if response.status_code == 404:
                result = {"lyrics": None, "synced": False}
                await self._cache.set(
                    result, "lyrics", platform, track_id, ttl=self.CACHE_TTL_LYRICS
                )
                return result

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "lyrics", platform, track_id, ttl=self.CACHE_TTL_LYRICS
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"lyrics": None, "synced": False}
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_audio_features(
        self, track_id: str, platform: str = "spotify", use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Get audio features for a track (BPM, energy, etc.).

        Args:
            track_id: Track ID on the platform
            platform: Platform name
            use_cache: Whether to use cached response

        Returns:
            Audio features data
        """
        if use_cache:
            cached = await self._cache.get("features", platform, track_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}/audio-features",
            )

            if response.status_code == 404:
                await self._cache.set(
                    {}, "features", platform, track_id, ttl=self.CACHE_TTL_FEATURES
                )
                return {}

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "features", platform, track_id, ttl=self.CACHE_TTL_FEATURES
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {}
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e


# Global client instance
_api_client: APIClient | None = None


def get_api_client() -> APIClient:
    """Get the global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client
