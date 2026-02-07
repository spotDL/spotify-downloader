"""API client for communicating with the SpotDL backend."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Any, TypeVar

import httpx

from spotdl_cli.config import Settings, get_settings
from spotdl_cli.core.types import (
    DownloadResult,
    EntityType,
    MatchEntry,
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

    def _normalize_provider_id(self, provider_id: str) -> str:
        """Normalize provider IDs to TargetPlatform naming."""
        return provider_id.strip().lower().replace("-", "_")

    def _get_target_platforms(
        self, target_platforms: list[TargetPlatform] | None = None
    ) -> list[TargetPlatform]:
        """Resolve target platforms from settings when not provided."""
        if target_platforms:
            return target_platforms

        provider_ids: list[str] = []
        prefs = getattr(self._settings, "audio_source_preferences", None)
        if prefs:
            provider_ids = [
                p.get("id", "")
                for p in prefs
                if p and p.get("enabled", True)
            ]
        elif self._settings.audio_providers:
            provider_ids = list(self._settings.audio_providers)

        platforms: list[TargetPlatform] = []
        for provider_id in provider_ids:
            normalized = self._normalize_provider_id(provider_id)
            try:
                platforms.append(TargetPlatform(normalized))
            except ValueError:
                continue

        if not platforms:
            platforms = [TargetPlatform.YOUTUBE, TargetPlatform.YOUTUBE_MUSIC]

        return platforms

    def _match_entry_from_api(self, match: dict[str, Any], fallback_song: Song) -> MatchEntry:
        """Convert API match response to MatchEntry."""
        result_data = match.get("result", {})
        result = DownloadResult(
            name=result_data.get("name", fallback_song.name),
            artists=result_data.get("artists", fallback_song.artists),
            artist=result_data.get("artist", fallback_song.artist),
            duration=result_data.get("duration", fallback_song.duration),
            platform=TargetPlatform(result_data.get("platform", "youtube")),
            platform_id=result_data.get("platform_id", ""),
            url=result_data.get("url", ""),
            verified=result_data.get("verified", False),
            score=match.get("score", 0.0),
            cover_url=result_data.get("cover_url"),
            views=result_data.get("views"),
        )

        return MatchEntry(
            id=match.get("id"),
            source_url=match.get("source_url", fallback_song.url),
            target_url=match.get("target_url", result.url),
            target_platform=match.get("target_platform", result.platform.value),
            score=match.get("score", 0.0),
            confidence=match.get("confidence", 0.0),
            match_type=match.get("match_type", "system"),
            status=match.get("status"),
            result=result,
            upvotes=match.get("upvotes", 0) or 0,
            downvotes=match.get("downvotes", 0) or 0,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": "SpotDL-CLI/5.0.0",
                "Accept": "application/json",
            }
            if self._settings.auth_token:
                headers["Authorization"] = f"Bearer {self._settings.auth_token}"
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_url,
                timeout=self._settings.api_timeout,
                headers=headers,
                # Connection pooling
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0,
                ),
                # Enable HTTP/2
                http2=True,
                follow_redirects=True,
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
                    "query": query,
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
        platforms = self._get_target_platforms(target_platforms)
        platforms_key = ",".join(p.value for p in platforms)
        cached = await self._cache.get("matches", song.url, platforms_key, limit)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

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
                result_data = match.get("result", {})
                result = DownloadResult(
                    name=result_data.get("name", song.name),
                    artists=result_data.get("artists", song.artists),
                    artist=result_data.get("artist", song.artist),
                    duration=result_data.get("duration", song.duration),
                    platform=TargetPlatform(result_data.get("platform", "youtube")),
                    platform_id=result_data.get("platform_id", ""),
                    url=result_data.get("url", ""),
                    verified=result_data.get("verified", False),
                    score=match.get("score", 0.0),
                    cover_url=result_data.get("cover_url"),
                    views=result_data.get("views"),
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

    def _primary_platform(self, platforms: list[dict[str, Any]]) -> dict[str, Any]:
        """Return the first platform entry when available."""
        return platforms[0] if platforms else {}

    def _normalize_entity_song(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize internal song response into CLI-friendly fields."""
        platforms = data.get("platforms", [])
        primary = self._primary_platform(platforms)
        artist = data.get("artist")
        artists = data.get("artists") or ([artist] if artist else [])
        return {
            "name": data.get("name", ""),
            "artists": artists,
            "artist": artist or (artists[0] if artists else "Unknown"),
            "duration": data.get("duration", 0) or 0,
            "platform": primary.get("platform") or data.get("platform") or "spotify",
            "platform_id": primary.get("platform_id") or data.get("platform_id") or "",
            "url": primary.get("url") or data.get("url") or "",
            "album": data.get("album_name"),
            "album_name": data.get("album_name"),
            "cover_url": data.get("cover_url"),
            "track_number": data.get("track_number"),
            "disc_number": data.get("disc_number"),
            "isrc": data.get("isrc"),
            "explicit": data.get("explicit", False),
            "year": data.get("year"),
            "genres": data.get("genres", []),
        }

    async def get_entity_song(
        self, song_id: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get song details by internal UUID."""
        if use_cache:
            cached = await self._cache.get("entity_song", song_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/songs/{song_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Song not found: {song_id}")
            response.raise_for_status()
            result = response.json()
            await self._cache.set(result, "entity_song", song_id, ttl=self.CACHE_TTL_DETAIL)
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_entity_album(
        self, album_id: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get album details by internal UUID (normalized for CLI screens)."""
        if use_cache:
            cached = await self._cache.get("entity_album", album_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/albums/{album_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")
            response.raise_for_status()
            data = response.json()

            tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            platforms = data.get("platforms", [])
            primary = self._primary_platform(platforms)

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "artist": data.get("artist_name") or data.get("artist"),
                "artists": [data.get("artist_name")] if data.get("artist_name") else [],
                "tracks": tracks,
                "total_tracks": data.get("total_tracks"),
                "release_date": data.get("release_date"),
                "year": data.get("year"),
                "cover_url": data.get("cover_url"),
                "album_type": data.get("album_type"),
                "label": data.get("label"),
                "popularity": data.get("popularity"),
                "genres": data.get("genres", []),
                "platforms": platforms,
                "platform": primary.get("platform"),
                "platform_id": primary.get("platform_id"),
                "url": primary.get("url"),
            }

            await self._cache.set(result, "entity_album", album_id, ttl=self.CACHE_TTL_DETAIL)
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_entity_artist(
        self, artist_id: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get artist details by internal UUID (normalized for CLI screens)."""
        if use_cache:
            cached = await self._cache.get("entity_artist", artist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/artists/{artist_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")
            response.raise_for_status()
            data = response.json()

            top_tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            albums = [
                {
                    "id": album.get("id"),
                    "name": album.get("name"),
                    "year": album.get("year"),
                    "total_tracks": album.get("total_tracks"),
                    "album_type": album.get("album_type"),
                    "type": album.get("album_type"),
                    "cover_url": album.get("cover_url"),
                }
                for album in data.get("albums", [])
            ]

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "image_url": data.get("image_url"),
                "genres": data.get("genres", []),
                "bio": data.get("bio"),
                "popularity": data.get("popularity"),
                "followers": data.get("monthly_listeners") or 0,
                "albums": albums,
                "top_tracks": top_tracks,
                "platforms": data.get("platforms", []),
            }

            await self._cache.set(result, "entity_artist", artist_id, ttl=self.CACHE_TTL_DETAIL)
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_entity_playlist(
        self, playlist_id: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get playlist details by internal UUID (normalized for CLI screens)."""
        if use_cache:
            cached = await self._cache.get("entity_playlist", playlist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/playlists/{playlist_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")
            response.raise_for_status()
            data = response.json()

            tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            platforms = data.get("platforms", [])
            primary = self._primary_platform(platforms)

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "description": data.get("description"),
                "cover_url": data.get("cover_url"),
                "owner": {"display_name": data.get("owner_name") or "Unknown"},
                "tracks": tracks,
                "total_tracks": data.get("total_tracks"),
                "followers": data.get("followers") or 0,
                "public": data.get("is_public", True),
                "platforms": platforms,
                "platform": primary.get("platform"),
                "platform_id": primary.get("platform_id"),
                "url": primary.get("url"),
            }

            await self._cache.set(result, "entity_playlist", playlist_id, ttl=self.CACHE_TTL_DETAIL)
            return result
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
        fallback_song: Song | None = None,
    ) -> MatchEntry:
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
            data = response.json()
            song = fallback_song or Song(
                name="Unknown",
                artists=["Unknown"],
                artist="Unknown",
                duration=0,
                platform=Platform.SPOTIFY,
                platform_id="",
                url=source_url,
            )
            return self._match_entry_from_api(data, song)

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_song_matches(
        self, song_id: str, fallback_song: Song
    ) -> list[MatchEntry]:
        """Get saved matches for a song."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/songs/{song_id}/matches")
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return [self._match_entry_from_api(m, fallback_song) for m in data]
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_match(self, match_id: str, fallback_song: Song) -> MatchEntry:
        """Get a match by ID."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/matches/{match_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Match not found: {match_id}")
            response.raise_for_status()
            data = response.json()
            return self._match_entry_from_api(data, fallback_song)
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_match_votes(self, match_id: str) -> dict[str, Any]:
        """Get vote summary for a match."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/votes/{match_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Match not found: {match_id}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def cast_vote(self, match_id: str, vote_type: str) -> dict[str, Any]:
        """Cast a vote on a match."""
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/votes",
                json={"match_id": match_id, "vote_type": vote_type},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def remove_vote(self, match_id: str) -> dict[str, Any]:
        """Remove a vote from a match."""
        try:
            client = await self._get_client()
            response = await client.delete(f"/api/v1/votes/{match_id}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def create_report(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        current_value: str,
        suggested_value: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Submit a metadata report."""
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/reports",
                json={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "field_name": field_name,
                    "current_value": current_value,
                    "suggested_value": suggested_value,
                    "description": description,
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

    async def get_service_status(self) -> dict[str, Any]:
        """Get service health status."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/health/services")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def start_download(self, request: dict[str, Any]) -> dict[str, Any]:
        """Start a backend download."""
        try:
            client = await self._get_client()
            response = await client.post("/api/v1/download/start", json=request)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_download_status(self, download_id: str) -> dict[str, Any]:
        """Get download status from backend."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/download/status/{download_id}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def list_downloads(self) -> dict[str, Any]:
        """List backend downloads."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/download/list")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def cancel_download(self, download_id: str) -> dict[str, Any]:
        """Cancel a backend download."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/download/cancel/{download_id}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def download_file(self, download_id: str, destination: Path) -> Path:
        """Download a completed file to a local path."""
        try:
            client = await self._get_client()
            async with client.stream(
                "GET", f"/api/v1/download/file/{download_id}"
            ) as response:
                response.raise_for_status()
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        handle.write(chunk)
            return destination
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
                f"/api/v1/entities/songs/platform/{platform}/{track_id}",
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
                f"/api/v1/entities/albums/platform/{platform}/{album_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")

            response.raise_for_status()
            data = response.json()

            tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            platforms = data.get("platforms", [])
            primary = self._primary_platform(platforms)
            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "artist": data.get("artist_name") or data.get("artist"),
                "artists": [data.get("artist_name")] if data.get("artist_name") else [],
                "tracks": tracks,
                "total_tracks": data.get("total_tracks"),
                "release_date": data.get("release_date"),
                "year": data.get("year"),
                "cover_url": data.get("cover_url"),
                "album_type": data.get("album_type"),
                "label": data.get("label"),
                "popularity": data.get("popularity"),
                "genres": data.get("genres", []),
                "platforms": platforms,
                "platform": primary.get("platform"),
                "platform_id": primary.get("platform_id"),
                "url": primary.get("url"),
            }

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
                f"/api/v1/entities/artists/platform/{platform}/{artist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")

            response.raise_for_status()
            data = response.json()

            top_tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            albums = [
                {
                    "id": album.get("id"),
                    "name": album.get("name"),
                    "year": album.get("year"),
                    "total_tracks": album.get("total_tracks"),
                    "album_type": album.get("album_type"),
                    "type": album.get("album_type"),
                    "cover_url": album.get("cover_url"),
                }
                for album in data.get("albums", [])
            ]

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "image_url": data.get("image_url"),
                "genres": data.get("genres", []),
                "bio": data.get("bio"),
                "popularity": data.get("popularity"),
                "followers": data.get("monthly_listeners") or 0,
                "albums": albums,
                "top_tracks": top_tracks,
                "platforms": data.get("platforms", []),
            }

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
                f"/api/v1/entities/playlists/platform/{platform}/{playlist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")

            response.raise_for_status()
            data = response.json()

            tracks = [self._normalize_entity_song(s) for s in data.get("songs", [])]
            platforms = data.get("platforms", [])
            primary = self._primary_platform(platforms)
            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "description": data.get("description"),
                "cover_url": data.get("cover_url"),
                "owner": {"display_name": data.get("owner_name") or "Unknown"},
                "tracks": tracks,
                "total_tracks": data.get("total_tracks"),
                "followers": data.get("followers") or 0,
                "public": data.get("is_public", True),
                "platforms": platforms,
                "platform": primary.get("platform"),
                "platform_id": primary.get("platform_id"),
                "url": primary.get("url"),
            }

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
        self, song_id: str, use_cache: bool = True, force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Get lyrics for a song by internal ID.

        Args:
            song_id: Internal song UUID
            use_cache: Whether to use cached response
            force_refresh: Force refresh from providers

        Returns:
            Lyrics data including synced and plain text
        """
        if use_cache:
            cached = await self._cache.get("lyrics", song_id, force_refresh)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/lyrics/song/{song_id}",
                params={"force_refresh": force_refresh},
            )

            response.raise_for_status()
            result = response.json()

            await self._cache.set(
                result, "lyrics", song_id, force_refresh, ttl=self.CACHE_TTL_LYRICS
            )
            return result

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"lyrics_text": None, "lyrics_synced": None}
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_all_lyrics(self, song_id: str, use_cache: bool = True) -> dict[str, Any]:
        """Get lyrics from all sources for a song by internal ID."""
        if use_cache:
            cached = await self._cache.get("lyrics_all", song_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/lyrics/song/{song_id}/all")
            response.raise_for_status()
            result = response.json()
            await self._cache.set(result, "lyrics_all", song_id, ttl=self.CACHE_TTL_LYRICS)
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def fetch_all_lyrics(self, song_id: str) -> dict[str, Any]:
        """Fetch lyrics from all sources and store them."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/lyrics/song/{song_id}/fetch-all")
            response.raise_for_status()
            result = response.json()
            await self._cache.set(result, "lyrics_all", song_id, ttl=self.CACHE_TTL_LYRICS)
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def search_lyrics(self, name: str, artist: str) -> dict[str, Any]:
        """Search lyrics by song name and artist."""
        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/lyrics/search",
                params={"name": name, "artist": artist},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"lyrics_text": None, "lyrics_synced": None}
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_metadata_sources(
        self, song_id: str, include_raw: bool = False, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get metadata sources for a song by internal ID."""
        if use_cache:
            cached = await self._cache.get("metadata_sources", song_id, include_raw)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/entities/songs/{song_id}/metadata-sources",
                params={"include_raw": include_raw},
            )
            response.raise_for_status()
            result = response.json()
            await self._cache.set(
                result, "metadata_sources", song_id, include_raw, ttl=self.CACHE_TTL_DETAIL
            )
            return result
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def refresh_entity(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """Refresh entity metadata by internal ID."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/entities/{entity_type}/{entity_id}/refresh")
            response.raise_for_status()
            cache_keys = {
                "songs": "entity_song",
                "albums": "entity_album",
                "artists": "entity_artist",
                "playlists": "entity_playlist",
            }
            cache_key = cache_keys.get(entity_type)
            if cache_key:
                await self._cache.invalidate(cache_key, entity_id)
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def enrich_song(self, song_id: str) -> dict[str, Any]:
        """Enrich song metadata from external sources."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/entities/songs/{song_id}/enrich")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def enrich_song_all_sources(self, song_id: str) -> dict[str, Any]:
        """Fetch metadata and lyrics from all sources for a song."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/entities/songs/{song_id}/enrich-all")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
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
