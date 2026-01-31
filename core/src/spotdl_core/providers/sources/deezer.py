"""Deezer source provider for fetching song metadata."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from spotdl_core.types.song import Platform, Song, SongList
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# Deezer API base URL
DEEZER_API_URL = "https://api.deezer.com"

# URL patterns for Deezer
DEEZER_URL_PATTERNS = [
    re.compile(r"https?://(?:www\.)?deezer\.com/(?:\w+/)?(track|album|playlist|artist)/(\d+)"),
    re.compile(r"deezer\.(page\.link|app\.link)/(\w+)"),  # Short links
]


class DeezerProvider(SourceProvider):
    """
    Deezer source provider.

    Fetches song metadata from Deezer using the public API.
    """

    name = "deezer"
    display_name = "Deezer"
    url_patterns = DEEZER_URL_PATTERNS

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the Deezer provider.

        Args:
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=DEEZER_API_URL,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _extract_id(url: str) -> tuple[str, str] | None:
        """
        Extract resource type and ID from Deezer URL.

        Args:
            url: Deezer URL

        Returns:
            Tuple of (resource_type, resource_id) or None
        """
        # Handle short links first
        short_link_match = re.search(r"deezer\.(page\.link|app\.link)/(\w+)", url)
        if short_link_match:
            # Short links need to be resolved
            return ("short", short_link_match.group(2))

        # Standard URL pattern
        match = re.search(
            r"deezer\.com/(?:\w+/)?(track|album|playlist|artist)/(\d+)", url
        )
        if match:
            return (match.group(1), match.group(2))

        return None

    async def _resolve_short_link(self, url: str) -> str:
        """
        Resolve a Deezer short link to the full URL.

        Args:
            url: Short link URL

        Returns:
            Resolved full URL

        Raises:
            InvalidURLError: If short link cannot be resolved
        """
        client = await self._get_client()

        try:
            # Follow redirects to get the full URL
            response = await client.head(url, follow_redirects=True)
            return str(response.url)
        except httpx.HTTPError as e:
            raise InvalidURLError(f"Failed to resolve short link: {e}") from e

    def _track_to_song(
        self,
        track: dict[str, Any],
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert Deezer track data to Song object.

        Args:
            track: Deezer track data
            list_info: Optional list context

        Returns:
            Song object
        """
        # Get artists
        artist_name = track.get("artist", {}).get("name", "Unknown")
        contributors = track.get("contributors", [])
        artists = [c.get("name", "") for c in contributors if c.get("name")]
        if not artists:
            artists = [artist_name]

        # Get album info
        album = track.get("album", {})
        album_name = album.get("title", "")

        # Get cover URL (highest resolution)
        cover_url = album.get("cover_xl") or album.get("cover_big") or album.get("cover_medium")
        if not cover_url:
            # Try artist picture if no album cover
            cover_url = track.get("artist", {}).get("picture_xl")

        # Parse release date
        release_date = album.get("release_date", "") or track.get("release_date", "")
        year = 0
        if release_date:
            try:
                year = int(release_date[:4])
            except (ValueError, IndexError):
                pass

        # Build song
        song = Song(
            name=track.get("title", "Unknown"),
            artists=artists,
            artist=artist_name,
            duration=track.get("duration", 0),
            platform=Platform.DEEZER,
            platform_id=str(track.get("id", "")),
            url=track.get("link", f"https://www.deezer.com/track/{track.get('id', '')}"),
            album_name=album_name,
            album_artist=album.get("artist", {}).get("name", "") if isinstance(album.get("artist"), dict) else artist_name,
            album_id=str(album.get("id", "")) if album.get("id") else None,
            album_type=album.get("record_type"),
            disc_number=track.get("disk_number", 1),
            track_number=track.get("track_position", 1),
            tracks_count=album.get("nb_tracks", 1),
            year=year,
            date=release_date,
            isrc=track.get("isrc"),
            explicit=track.get("explicit_lyrics", False),
            cover_url=cover_url,
            artist_id=str(track.get("artist", {}).get("id", "")),
        )

        # Add list context if provided
        if list_info:
            song.list_name = list_info.get("name")
            song.list_url = list_info.get("url")
            song.list_position = list_info.get("position")
            song.list_length = list_info.get("length")

        return song

    async def _api_request(self, endpoint: str) -> dict[str, Any]:
        """
        Make a request to the Deezer API.

        Args:
            endpoint: API endpoint (e.g., "/track/123")

        Returns:
            JSON response data

        Raises:
            SourceProviderError: If request fails
        """
        client = await self._get_client()

        try:
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()

            # Check for API error response
            if "error" in data:
                error = data["error"]
                raise SourceProviderError(
                    f"Deezer API error: {error.get('message', 'Unknown error')}"
                )

            return data

        except httpx.HTTPStatusError as e:
            raise SourceProviderError(f"Deezer API request failed: {e}") from e
        except httpx.HTTPError as e:
            raise SourceProviderError(f"Deezer API request failed: {e}") from e

    async def get_track(self, url: str) -> Song:
        """
        Fetch a single track by URL.

        Args:
            url: Deezer track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        # Handle short links
        if "deezer.page.link" in url or "deezer.app.link" in url:
            url = await self._resolve_short_link(url)

        extracted = self._extract_id(url)
        if not extracted:
            raise InvalidURLError(f"Invalid Deezer URL: {url}")

        resource_type, track_id = extracted

        if resource_type != "track":
            raise InvalidURLError(f"URL is not a track: {url}")

        try:
            track = await self._api_request(f"/track/{track_id}")

            if not track.get("id"):
                raise TrackNotFoundError(f"Track not found: {url}")

            return self._track_to_song(track)

        except SourceProviderError as e:
            if "Data not found" in str(e):
                raise TrackNotFoundError(f"Track not found: {url}") from e
            raise

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Deezer album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        # Handle short links
        if "deezer.page.link" in url or "deezer.app.link" in url:
            url = await self._resolve_short_link(url)

        extracted = self._extract_id(url)
        if not extracted:
            raise InvalidURLError(f"Invalid Deezer URL: {url}")

        resource_type, album_id = extracted

        if resource_type != "album":
            raise InvalidURLError(f"URL is not an album: {url}")

        try:
            album = await self._api_request(f"/album/{album_id}")

            if not album.get("id"):
                raise SourceProviderError(f"Album not found: {url}")

            album_name = album.get("title", "")
            tracks = album.get("tracks", {}).get("data", [])

            # Build list info
            list_info = {
                "name": album_name,
                "url": album.get("link", url),
                "length": len(tracks),
            }

            # Fetch full track details for each track
            songs: list[Song] = []
            for i, track_data in enumerate(tracks):
                track_id = track_data.get("id")
                if not track_id:
                    continue

                try:
                    # Get full track details
                    full_track = await self._api_request(f"/track/{track_id}")
                    # Merge album data
                    full_track["album"] = album

                    list_info["position"] = i + 1
                    song = self._track_to_song(full_track, list_info)
                    songs.append(song)
                except SourceProviderError:
                    continue

            return SongList(
                name=album_name,
                url=album.get("link", url),
                platform=Platform.DEEZER,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError as e:
            if "Data not found" in str(e):
                raise SourceProviderError(f"Album not found: {url}") from e
            raise

    async def get_playlist(self, url: str) -> SongList:
        """
        Fetch a playlist by URL.

        Args:
            url: Deezer playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        # Handle short links
        if "deezer.page.link" in url or "deezer.app.link" in url:
            url = await self._resolve_short_link(url)

        extracted = self._extract_id(url)
        if not extracted:
            raise InvalidURLError(f"Invalid Deezer URL: {url}")

        resource_type, playlist_id = extracted

        if resource_type != "playlist":
            raise InvalidURLError(f"URL is not a playlist: {url}")

        try:
            playlist = await self._api_request(f"/playlist/{playlist_id}")

            if not playlist.get("id"):
                raise SourceProviderError(f"Playlist not found: {url}")

            playlist_name = playlist.get("title", "")
            tracks = playlist.get("tracks", {}).get("data", [])

            # Build list info
            list_info = {
                "name": playlist_name,
                "url": playlist.get("link", url),
                "length": len(tracks),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, track in enumerate(tracks):
                if not track.get("id"):
                    continue

                list_info["position"] = i + 1
                song = self._track_to_song(track, list_info)
                songs.append(song)

            return SongList(
                name=playlist_name,
                url=playlist.get("link", url),
                platform=Platform.DEEZER,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError as e:
            if "Data not found" in str(e):
                raise SourceProviderError(f"Playlist not found: {url}") from e
            raise

    async def get_artist(self, url: str) -> SongList:
        """
        Fetch all tracks from an artist by URL.

        Args:
            url: Deezer artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        # Handle short links
        if "deezer.page.link" in url or "deezer.app.link" in url:
            url = await self._resolve_short_link(url)

        extracted = self._extract_id(url)
        if not extracted:
            raise InvalidURLError(f"Invalid Deezer URL: {url}")

        resource_type, artist_id = extracted

        if resource_type != "artist":
            raise InvalidURLError(f"URL is not an artist: {url}")

        try:
            artist = await self._api_request(f"/artist/{artist_id}")

            if not artist.get("id"):
                raise SourceProviderError(f"Artist not found: {url}")

            artist_name = artist.get("name", "")

            # Get artist's top tracks
            top_tracks = await self._api_request(f"/artist/{artist_id}/top?limit=100")
            tracks = top_tracks.get("data", [])

            # Get artist's albums and their tracks
            albums_data = await self._api_request(f"/artist/{artist_id}/albums?limit=100")
            albums = albums_data.get("data", [])

            # Collect songs from albums
            for album in albums:
                album_id = album.get("id")
                if not album_id:
                    continue

                try:
                    album_url = f"https://www.deezer.com/album/{album_id}"
                    album_songs = await self.get_album(album_url)
                    # Add album songs (will dedupe later)
                    for song in album_songs.songs:
                        tracks.append({
                            "id": song.platform_id,
                            "title": song.name,
                            "duration": song.duration,
                            "artist": {"id": artist_id, "name": artist_name},
                            "album": {"id": song.album_id, "title": song.album_name},
                            "link": song.url,
                        })
                except SourceProviderError:
                    continue

            # Build list info
            list_info = {
                "name": artist_name,
                "url": artist.get("link", url),
            }

            # Deduplicate by track ID and convert to songs
            seen_ids: set[str] = set()
            songs: list[Song] = []
            for track in tracks:
                track_id = str(track.get("id", ""))
                if track_id in seen_ids:
                    continue
                seen_ids.add(track_id)

                song = self._track_to_song(track, list_info)
                songs.append(song)

            # Update positions
            for i, song in enumerate(songs):
                song.list_position = i + 1
                song.list_length = len(songs)

            return SongList(
                name=artist_name,
                url=artist.get("link", url),
                platform=Platform.DEEZER,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError as e:
            if "Data not found" in str(e):
                raise SourceProviderError(f"Artist not found: {url}") from e
            raise

    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """
        Search for tracks by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching Song objects
        """
        try:
            # URL encode the query
            import urllib.parse
            encoded_query = urllib.parse.quote(query)

            results = await self._api_request(f"/search/track?q={encoded_query}&limit={limit}")

            tracks = results.get("data", [])

            songs = []
            for track in tracks:
                if track.get("id"):
                    song = self._track_to_song(track)
                    songs.append(song)

            return songs

        except SourceProviderError:
            return []
