"""API client for communicating with the SpotDL backend."""

from __future__ import annotations

import logging
from typing import Any

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


class APIError(Exception):
    """Base exception for API errors."""


class ConnectionError(APIError):
    """Raised when cannot connect to the API."""


class NotFoundError(APIError):
    """Raised when a resource is not found."""


class APIClient:
    """
    Client for the SpotDL backend API.

    Provides methods to:
    - Resolve URLs to songs
    - Search for songs
    - Find matches (download URLs)
    - Check server health
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the API client.

        Args:
            settings: Settings instance (uses global if not provided)
        """
        self._settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_url,
                timeout=self._settings.api_timeout,
                headers={
                    "User-Agent": "SpotDL-CLI/5.0.0",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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

            return [Song.from_dict(s) for s in data.get("songs", [])]

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
    ) -> list[Song]:
        """
        Search for songs.

        Args:
            query: Search query
            platform: Platform to search on
            limit: Maximum results

        Returns:
            List of matching Song objects
        """
        try:
            client = await self._get_client()
            response = await client.get(
                "/api/v1/songs/search",
                params={
                    "q": query,
                    "platform": platform.value,
                    "limit": limit,
                },
            )

            response.raise_for_status()
            data = response.json()

            return [Song.from_dict(s) for s in data.get("songs", [])]

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
    ) -> UniversalSearchResponse:
        """
        Universal search returning all entity types.

        Args:
            query: Search query or URL
            entity_types: Optional filter for entity types
            limit: Maximum results

        Returns:
            UniversalSearchResponse with artists, albums, tracks, playlists
        """
        try:
            client = await self._get_client()

            body: dict[str, Any] = {
                "query": query,
                "limit": limit,
            }
            if entity_types:
                body["entity_types"] = [et.value for et in entity_types]

            response = await client.post(
                "/api/v1/search",
                json=body,
            )

            response.raise_for_status()
            data = response.json()

            return UniversalSearchResponse.from_dict(data)

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

    async def get_track(self, track_id: str, platform: str = "spotify") -> dict[str, Any]:
        """
        Get detailed information about a track.

        Args:
            track_id: Track ID on the platform
            platform: Platform name (spotify, deezer, etc.)

        Returns:
            Track details including metadata, matches, lyrics, audio features
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Track not found: {track_id}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_album(self, album_id: str, platform: str = "spotify") -> dict[str, Any]:
        """
        Get detailed information about an album.

        Args:
            album_id: Album ID on the platform
            platform: Platform name (spotify, deezer, etc.)

        Returns:
            Album details including tracks, metadata
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/albums/{platform}/{album_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Album not found: {album_id}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_artist(self, artist_id: str, platform: str = "spotify") -> dict[str, Any]:
        """
        Get detailed information about an artist.

        Args:
            artist_id: Artist ID on the platform
            platform: Platform name (spotify, deezer, etc.)

        Returns:
            Artist details including albums, top tracks
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/artists/{platform}/{artist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Artist not found: {artist_id}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_playlist(
        self, playlist_id: str, platform: str = "spotify"
    ) -> dict[str, Any]:
        """
        Get detailed information about a playlist.

        Args:
            playlist_id: Playlist ID on the platform
            platform: Platform name (spotify, deezer, etc.)

        Returns:
            Playlist details including tracks
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/playlists/{platform}/{playlist_id}",
            )

            if response.status_code == 404:
                raise NotFoundError(f"Playlist not found: {playlist_id}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_lyrics(self, track_id: str, platform: str = "spotify") -> dict[str, Any]:
        """
        Get lyrics for a track.

        Args:
            track_id: Track ID on the platform
            platform: Platform name

        Returns:
            Lyrics data including synced and plain text
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}/lyrics",
            )

            if response.status_code == 404:
                return {"lyrics": None, "synced": False}

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to API: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"lyrics": None, "synced": False}
            raise APIError(f"API error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Request failed: {e}") from e

    async def get_audio_features(
        self, track_id: str, platform: str = "spotify"
    ) -> dict[str, Any]:
        """
        Get audio features for a track (BPM, energy, etc.).

        Args:
            track_id: Track ID on the platform
            platform: Platform name

        Returns:
            Audio features data
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/songs/{platform}/{track_id}/audio-features",
            )

            if response.status_code == 404:
                return {}

            response.raise_for_status()
            return response.json()

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
