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

    def _song_from_entity(self, entity: dict[str, Any]) -> Song:
        """Convert backend EntityResponse to a CLI Song."""
        canonical = entity.get("canonical", {})
        etype = entity.get("type", "track")

        # Extract platform info from canonical
        platform_str = canonical.get("platform", "spotify")
        try:
            platform = Platform(platform_str)
        except ValueError:
            platform = Platform.SPOTIFY

        artists = canonical.get("artists") or []
        artist = canonical.get("artist") or (artists[0] if artists else "Unknown")

        return Song(
            name=canonical.get("name") or entity.get("name", ""),
            artists=artists,
            artist=artist,
            duration=canonical.get("duration") or 0,
            platform=platform,
            platform_id=canonical.get("platform_id", ""),
            url=canonical.get("url", ""),
            album_name=canonical.get("album_name", ""),
            album_artist=canonical.get("album_artist", ""),
            album_id=canonical.get("album_id"),
            cover_url=canonical.get("cover_url"),
            isrc=canonical.get("isrc"),
            explicit=canonical.get("explicit", False),
            year=canonical.get("year", 0) or 0,
            genres=canonical.get("genres", []),
            track_number=canonical.get("track_number", 1) or 1,
            disc_number=canonical.get("disc_number", 1) or 1,
            song_id=entity.get("id", ""),
            lyrics=canonical.get("lyrics"),
        )

    def _match_entry_from_relation(
        self, relation: dict[str, Any], fallback_song: Song
    ) -> MatchEntry:
        """Convert backend RelationResponse to a MatchEntry."""
        target = relation.get("target", {})
        target_canonical = target.get("canonical", {}) if target else {}

        # Build DownloadResult from the target entity's canonical data
        platform_str = target_canonical.get("platform", "youtube")
        try:
            target_platform = TargetPlatform(platform_str)
        except ValueError:
            target_platform = TargetPlatform.YOUTUBE

        target_artists = target_canonical.get("artists", fallback_song.artists)
        target_artist = target_canonical.get("artist") or (
            target_artists[0] if target_artists else fallback_song.artist
        )

        result = DownloadResult(
            name=target_canonical.get("name", fallback_song.name),
            artists=target_artists,
            artist=target_artist,
            duration=target_canonical.get("duration", fallback_song.duration),
            platform=target_platform,
            platform_id=target_canonical.get("platform_id", ""),
            url=target_canonical.get("url", ""),
            verified=relation.get("status") == "confirmed",
            score=relation.get("match_score") or relation.get("confidence", 0.0),
            cover_url=target_canonical.get("cover_url"),
            views=target_canonical.get("views"),
        )

        return MatchEntry(
            id=relation.get("id"),
            source_url=fallback_song.url,
            target_url=result.url,
            target_platform=target_platform.value,
            score=relation.get("match_score") or 0.0,
            confidence=relation.get("confidence", 0.0),
            match_type=relation.get("relation_type", "audio_match"),
            status=relation.get("status"),
            result=result,
            upvotes=relation.get("upvotes", 0) or 0,
            downvotes=relation.get("downvotes", 0) or 0,
        )

    @staticmethod
    def _build_platform_url(platform: str, entity_type: str, entity_id: str) -> str:
        """Build a platform URL from platform name, entity type and ID."""
        platform = platform.lower()
        if platform == "spotify":
            return f"https://open.spotify.com/{entity_type}/{entity_id}"
        elif platform == "deezer":
            return f"https://www.deezer.com/{entity_type}/{entity_id}"
        elif platform in ("youtube", "youtube_music"):
            return f"https://www.youtube.com/watch?v={entity_id}"
        elif platform == "soundcloud":
            return f"https://soundcloud.com/{entity_id}"
        # Generic fallback
        return f"https://{platform}.com/{entity_type}/{entity_id}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Uses BackendManager to create the client — this automatically
        picks ASGI transport for local mode or HTTP for remote mode.
        """
        if self._client is None or self._client.is_closed:
            from spotdl_cli.core.backend import get_backend_manager

            manager = get_backend_manager()
            self._client = manager.create_client()
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
        Resolve a URL to songs via POST /api/v1/entities/discover.

        Args:
            url: URL to resolve (Spotify, Deezer, etc.)

        Returns:
            List of Song objects

        Raises:
            APIError: If request fails
            NotFoundError: If URL not supported
        """
        cached = await self._cache.get("resolve", url)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/entities/discover",
                json={"url": url},
            )

            if response.status_code == 404:
                raise NotFoundError(f"URL not supported: {url}")

            response.raise_for_status()
            data = response.json()

            result = [
                self._song_from_entity(e)
                for e in data.get("entities", [])
                if e.get("type") == "track"
            ]

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
        Search for songs via POST /api/v1/entities/discover.

        Args:
            query: Search query
            platform: Platform to search on (used as provider hint)
            limit: Maximum results
            offset: Ignored (discover doesn't support offset)

        Returns:
            List of matching Song objects
        """
        cached = await self._cache.get("search", query, platform.value, limit)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

            body: dict[str, Any] = {"query": query, "limit": limit}
            # Map platform to provider hint
            if platform != Platform.SPOTIFY:
                body["providers"] = [platform.value]

            response = await client.post(
                "/api/v1/entities/discover",
                json=body,
            )

            response.raise_for_status()
            data = response.json()

            result = [
                self._song_from_entity(e)
                for e in data.get("entities", [])
                if e.get("type") == "track"
            ]

            await self._cache.set(
                result, "search", query, platform.value, limit,
                ttl=self.CACHE_TTL_SEARCH,
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
        Universal search returning all entity types via POST /api/v1/entities/discover.

        Args:
            query: Search query or URL
            entity_types: Optional filter for entity types
            limit: Maximum results per page
            offset: Ignored (discover doesn't support offset)

        Returns:
            UniversalSearchResponse with artists, albums, tracks, playlists
        """
        et_key = ",".join(sorted(et.value for et in entity_types)) if entity_types else ""
        cached = await self._cache.get("universal", query, et_key, limit, offset)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

            body: dict[str, Any] = {"limit": limit}
            # Detect if query looks like a URL
            if query.startswith(("http://", "https://")):
                body["url"] = query
            else:
                body["query"] = query
            if entity_types:
                body["types"] = [et.value for et in entity_types]

            response = await client.post(
                "/api/v1/entities/discover",
                json=body,
            )

            response.raise_for_status()
            data = response.json()

            result = UniversalSearchResponse.from_dict(data)

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

        First discovers the entity, then discovers relations via
        POST /api/v1/entities/{entity_id}/relations:discover.

        Args:
            song: Song to find matches for
            target_platforms: Platforms to search (defaults to all)
            limit: Maximum matches per platform

        Returns:
            List of DownloadResult objects
        """
        platforms = self._get_target_platforms(target_platforms)
        platforms_key = ",".join(p.value for p in platforms)
        cached = await self._cache.get("matches", song.url, platforms_key, limit)
        if cached is not None:
            return cached

        try:
            client = await self._get_client()

            # Step 1: Discover the entity to get its ID
            entity_id = song.song_id
            if not entity_id:
                discover_resp = await client.post(
                    "/api/v1/entities/discover",
                    json={"url": song.url},
                )
                if discover_resp.status_code == 404:
                    return []
                discover_resp.raise_for_status()
                discover_data = discover_resp.json()
                entities = discover_data.get("entities", [])

                # Check top_relations first — discover may have already found matches
                top_relations = discover_data.get("top_relations", {})

                if entities:
                    entity_id = entities[0].get("id", "")
                    # If discover already returned relations for this entity, use them
                    entity_relations = top_relations.get(entity_id, [])
                    if entity_relations:
                        results = [
                            self._match_entry_from_relation(r, song).result
                            for r in entity_relations
                        ]
                        await self._cache.set(
                            results, "matches", song.url, platforms_key, limit,
                            ttl=self.CACHE_TTL_SEARCH,
                        )
                        return results

                if not entity_id:
                    return []

            # Step 2: Discover relations for the entity
            response = await client.post(
                f"/api/v1/entities/{entity_id}/relations:discover",
                json={
                    "target_providers": [p.value for p in platforms],
                    "limit": limit,
                },
            )

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            results = [
                self._match_entry_from_relation(r, song).result
                for r in data.get("relations", [])
            ]

            await self._cache.set(
                results, "matches", song.url, platforms_key, limit,
                ttl=self.CACHE_TTL_SEARCH,
            )
            return results

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    @staticmethod
    def _flatten_entity(data: dict[str, Any]) -> dict[str, Any]:
        """Flatten EntityResponse: merge canonical fields into top-level dict.

        The backend returns ``{id, type, name, canonical: {…}, …}``.
        Callers (screens) expect key fields at the top level, so we lift
        everything from ``canonical`` while preserving the original top-level
        keys (``id``, ``type``, ``name``, etc.).
        """
        canonical = data.get("canonical", {})
        result = dict(canonical)  # start with canonical fields
        # Overlay top-level entity fields (id, type, name, quality_score, …)
        result.update({k: v for k, v in data.items() if k != "canonical"})
        return result

    async def get_entity_song(
        self, song_id: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Get song/track entity details by internal UUID via GET /api/v1/entities/{id}."""
        if use_cache:
            cached = await self._cache.get("entity_song", song_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/{song_id}")
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
        """Get album entity by internal UUID via GET /api/v1/entities/{id}."""
        if use_cache:
            cached = await self._cache.get("entity_album", album_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/{album_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")
            response.raise_for_status()
            result = self._flatten_entity(response.json())
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
        """Get artist entity by internal UUID via GET /api/v1/entities/{id}."""
        if use_cache:
            cached = await self._cache.get("entity_artist", artist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/{artist_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")
            response.raise_for_status()
            result = self._flatten_entity(response.json())
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
        """Get playlist entity by internal UUID via GET /api/v1/entities/{id}."""
        if use_cache:
            cached = await self._cache.get("entity_playlist", playlist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/{playlist_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")
            response.raise_for_status()
            result = self._flatten_entity(response.json())
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
        Submit a user-discovered match via POST /api/v1/entities/{entity_id}/relations.

        First discovers the source entity, then creates a relation to the target URL.

        Args:
            source_url: Source song URL
            target_url: Target download URL

        Returns:
            Match submission result
        """
        try:
            client = await self._get_client()

            # Discover source entity to get its ID
            discover_resp = await client.post(
                "/api/v1/entities/discover",
                json={"url": source_url},
            )
            discover_resp.raise_for_status()
            discover_data = discover_resp.json()
            entities = discover_data.get("entities", [])
            if not entities:
                raise APIError(f"Could not resolve source URL: {source_url}")
            entity_id = entities[0]["id"]

            # Create relation
            response = await client.post(
                f"/api/v1/entities/{entity_id}/relations",
                json={
                    "to_url": target_url,
                    "relation_type": "audio_match",
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
            return self._match_entry_from_relation(data, song)

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_song_matches(
        self, song_id: str, fallback_song: Song
    ) -> list[MatchEntry]:
        """Get saved matches for a song via GET /api/v1/entities/{entity_id}/relations."""
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/entities/{song_id}/relations",
                params={"relation_type": "audio_match"},
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return [
                self._match_entry_from_relation(r, fallback_song)
                for r in data.get("relations", [])
            ]
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_match(self, match_id: str, fallback_song: Song) -> MatchEntry:
        """Get a match (relation) by ID via GET /api/v1/relations/{id}."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/relations/{match_id}")
            if response.status_code == 404:
                raise NotFoundError(f"Match not found: {match_id}")
            response.raise_for_status()
            data = response.json()
            return self._match_entry_from_relation(data, fallback_song)
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_match_votes(self, match_id: str) -> dict[str, Any]:
        """Get vote summary for a relation via GET /api/v1/relations/{id}/vote."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/relations/{match_id}/vote")
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
        """Cast a vote on a relation via POST /api/v1/relations/{id}/vote."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"/api/v1/relations/{match_id}/vote",
                json={"vote": vote_type},
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
        """Remove a vote from a relation via POST /api/v1/relations/{id}/vote with 'remove'."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"/api/v1/relations/{match_id}/vote",
                json={"vote": "remove"},
            )
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

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """
        Login to the backend.

        Args:
            username: Username
            password: Password

        Returns:
            Token response (access_token, refresh_token, user)
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            data = response.json()

            # Update settings with token
            token = data.get("access_token")
            if not token:
                raise APIError("Login response missing access_token")
            self._settings.auth_token = token
            self._settings.save()

            # Recreate client to use new token
            await self.close()

            return data
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"Login failed: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        """
        Register a new user.

        Args:
            username: Username
            email: Email address
            password: Password

        Returns:
            Token response (access_token, refresh_token, user)
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/auth/register",
                json={"username": username, "email": email, "password": password},
            )
            response.raise_for_status()
            data = response.json()

            # Update settings with token
            token = data.get("access_token")
            if not token:
                raise APIError("Registration response missing access_token")
            self._settings.auth_token = token
            self._settings.save()

            # Recreate client to use new token
            await self.close()

            return data
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"Registration failed: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_me(self) -> dict[str, Any]:
        """Get current user profile."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/auth/me")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def change_password(
        self, current_password: str, new_password: str
    ) -> dict[str, Any]:
        """Change user password."""
        try:
            client = await self._get_client()
            response = await client.put(
                "/api/v1/auth/password",
                json={
                    "current_password": current_password,
                    "new_password": new_password,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"Password change failed: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def delete_account(self) -> None:
        """Delete current user account."""
        try:
            client = await self._get_client()
            response = await client.delete("/api/v1/auth/me")
            response.raise_for_status()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"Account deletion failed: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

        self._settings.auth_token = None
        self._settings.save()
        await self.close()

    async def logout(self) -> None:
        """Logout and clear token."""
        try:
            client = await self._get_client()
            await client.post("/api/v1/auth/logout")
        except Exception:
            pass  # Ignore errors on logout
        
        self._settings.auth_token = None
        self._settings.save()
        await self.close()

    async def get_user_settings(self) -> dict[str, Any]:
        """Get user settings from server."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/settings/me")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def update_user_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Update user settings on server."""
        try:
            client = await self._get_client()
            response = await client.put("/api/v1/settings/me", json=settings)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def reset_user_settings(self) -> dict[str, Any]:
        """Reset user settings on server."""
        try:
            client = await self._get_client()
            response = await client.delete("/api/v1/settings/me")
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
        Get detailed information about a track by discovering it via platform URL.

        Args:
            track_id: Track ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Track details (EntityResponse)
        """
        if use_cache:
            cached = await self._cache.get("track", platform, track_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            url = self._build_platform_url(platform, "track", track_id)
            response = await client.post(
                "/api/v1/entities/discover",
                json={"url": url, "types": ["track"]},
            )

            if response.status_code == 404:
                raise NotFoundError(f"Track not found: {track_id}")

            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            if not entities:
                raise NotFoundError(f"Track not found: {track_id}")
            result = entities[0]

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
        Get detailed information about an album by discovering via platform URL.

        Args:
            album_id: Album ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Album EntityResponse from discover
        """
        if use_cache:
            cached = await self._cache.get("album", platform, album_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            url = self._build_platform_url(platform, "album", album_id)
            response = await client.post(
                "/api/v1/entities/discover",
                json={"url": url, "types": ["album"]},
            )

            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")

            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            if not entities:
                raise NotFoundError(f"Album not found: {album_id}")
            result = entities[0]

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
        Get detailed information about an artist by discovering via platform URL.

        Args:
            artist_id: Artist ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Artist EntityResponse from discover
        """
        if use_cache:
            cached = await self._cache.get("artist", platform, artist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            url = self._build_platform_url(platform, "artist", artist_id)
            response = await client.post(
                "/api/v1/entities/discover",
                json={"url": url, "types": ["artist"]},
            )

            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")

            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            if not entities:
                raise NotFoundError(f"Artist not found: {artist_id}")
            result = entities[0]

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
        Get detailed information about a playlist by discovering via platform URL.

        Args:
            playlist_id: Playlist ID on the platform
            platform: Platform name (spotify, deezer, etc.)
            use_cache: Whether to use cached response

        Returns:
            Playlist EntityResponse from discover
        """
        if use_cache:
            cached = await self._cache.get("playlist", platform, playlist_id)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            url = self._build_platform_url(platform, "playlist", playlist_id)
            response = await client.post(
                "/api/v1/entities/discover",
                json={"url": url, "types": ["playlist"]},
            )

            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")

            response.raise_for_status()
            data = response.json()
            entities = data.get("entities", [])
            if not entities:
                raise NotFoundError(f"Playlist not found: {playlist_id}")
            result = entities[0]

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
                f"/api/v1/lyrics/entity/{song_id}",
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
            response = await client.get(f"/api/v1/lyrics/entity/{song_id}/all")
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
            response = await client.post(f"/api/v1/lyrics/entity/{song_id}/fetch-all")
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
        """Get metadata snapshots for an entity via GET /api/v1/entities/{id}/snapshots."""
        if use_cache:
            cached = await self._cache.get("metadata_sources", song_id, include_raw)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/entities/{song_id}/snapshots")
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
        """Refresh entity metadata via POST /api/v1/entities/{id}/refresh."""
        try:
            client = await self._get_client()
            response = await client.post(f"/api/v1/entities/{entity_id}/refresh", json={})
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
        """Enrich song metadata via POST /api/v1/entities/{id}/refresh."""
        return await self.refresh_entity("songs", song_id)

    async def enrich_song_all_sources(self, song_id: str) -> dict[str, Any]:
        """Fetch metadata from all sources via POST /api/v1/entities/{id}/refresh."""
        return await self.refresh_entity("songs", song_id)

    async def get_admin_stats(self) -> dict[str, Any]:
        """Get admin dashboard statistics."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/admin/stats")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_admin_matches(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Get matches for admin review via GET /api/v1/admin/matches."""
        try:
            client = await self._get_client()
            page = (offset // limit) + 1 if limit else 1
            params: dict[str, Any] = {"page": page, "per_page": limit}
            if status:
                params["status"] = status
            response = await client.get("/api/v1/admin/matches", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def approve_match(self, match_id: str) -> dict[str, Any]:
        """Approve a match via PATCH /api/v1/admin/matches/{id} with status=confirmed."""
        try:
            client = await self._get_client()
            response = await client.patch(
                f"/api/v1/admin/matches/{match_id}",
                json={"status": "confirmed"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def reject_match(self, match_id: str) -> dict[str, Any]:
        """Reject a match via PATCH /api/v1/admin/matches/{id} with status=rejected."""
        try:
            client = await self._get_client()
            response = await client.patch(
                f"/api/v1/admin/matches/{match_id}",
                json={"status": "rejected"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_admin_reports(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Get reports for admin review via GET /api/v1/reports."""
        try:
            client = await self._get_client()
            page = (offset // limit) + 1 if limit else 1
            params: dict[str, Any] = {"page": page, "page_size": limit}
            if status:
                params["status"] = status
            response = await client.get("/api/v1/reports", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def resolve_report(
        self, report_id: str, action: str, details: str = ""
    ) -> dict[str, Any]:
        """Resolve a report."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"/api/v1/admin/reports/{report_id}/resolve",
                json={"action": action, "details": details},
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_admin_users(
        self, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """Get users for admin view."""
        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/admin/users", params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def update_user_role(self, user_id: str, is_admin: bool) -> dict[str, Any]:
        """Update a user's role."""
        try:
            client = await self._get_client()
            response = await client.patch(
                f"/api/v1/admin/users/{user_id}/role", json={"is_admin": is_admin}
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def ban_user(self, user_id: str, reason: str = "") -> dict[str, Any]:
        """Ban or unban a user."""
        try:
            client = await self._get_client()
            response = await client.post(
                f"/api/v1/admin/users/{user_id}/ban", json={"reason": reason}
            )
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
