"""SoundCloud source provider for fetching song metadata."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

import httpx
from bs4 import BeautifulSoup

from spotdl.core.types.song import Platform, Song, SongList
from spotdl.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# URL patterns for SoundCloud
SOUNDCLOUD_URL_PATTERNS = [
    re.compile(r"https?://(?:www\.)?soundcloud\.com/([^/]+)/([^/]+)(?:/([^/]+))?"),
    re.compile(r"https?://(?:www\.)?soundcloud\.com/([^/]+)/sets/([^/]+)"),
]


class SoundCloudProvider(SourceProvider):
    """
    SoundCloud source provider.

    Fetches song metadata from SoundCloud using web scraping.
    """

    name = "soundcloud"
    display_name = "SoundCloud"
    url_patterns = SOUNDCLOUD_URL_PATTERNS

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the SoundCloud provider.

        Args:
            timeout: Request timeout in seconds
        """
        super().__init__()
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._client_id: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _extract_url_info(url: str) -> dict[str, str | None]:
        """
        Extract information from SoundCloud URL.

        Args:
            url: SoundCloud URL

        Returns:
            Dictionary with user, slug, and type
        """
        # Set URL pattern: /user/sets/playlist-name
        sets_match = re.search(r"soundcloud\.com/([^/]+)/sets/([^/?]+)", url)
        if sets_match:
            return {
                "user": sets_match.group(1),
                "slug": sets_match.group(2),
                "type": "playlist",
            }

        # Track pattern: /user/track-name
        track_match = re.search(r"soundcloud\.com/([^/]+)/([^/?]+)", url)
        if track_match:
            user = track_match.group(1)
            slug = track_match.group(2)

            # Check if it's a user page (no slug or special slugs)
            if slug in ("tracks", "albums", "sets", "reposts", "likes", "followers", "following"):
                return {"user": user, "slug": None, "type": "artist"}
            if not slug or slug == user:
                return {"user": user, "slug": None, "type": "artist"}

            return {"user": user, "slug": slug, "type": "track"}

        # User page: /user
        user_match = re.search(r"soundcloud\.com/([^/?]+)$", url)
        if user_match:
            return {"user": user_match.group(1), "slug": None, "type": "artist"}

        return {"user": None, "slug": None, "type": None}

    async def _fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a SoundCloud page.

        Args:
            url: Page URL

        Returns:
            BeautifulSoup object

        Raises:
            SourceProviderError: If fetch fails
        """
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SourceProviderError(f"Page not found: {url}") from e
            raise SourceProviderError(f"Failed to fetch page: {e}") from e
        except httpx.HTTPError as e:
            raise SourceProviderError(f"Failed to fetch page: {e}") from e

    def _extract_hydration_data(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        Extract hydration data from SoundCloud page.

        SoundCloud uses __sc_hydration for initial page data.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of hydration data objects
        """
        for script in soup.find_all("script"):
            text = script.string or ""
            if "__sc_hydration" in text:
                # Extract the JSON array
                match = re.search(r"__sc_hydration\s*=\s*(\[.*?\]);", text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except json.JSONDecodeError as e:
                        logger.debug("Failed to parse hydration data: %s", e)
        return []

    def _find_hydration_by_hydratable(
        self, hydration_data: list[dict[str, Any]], hydratable: str
    ) -> dict[str, Any] | None:
        """
        Find hydration data by hydratable type.

        Args:
            hydration_data: List of hydration objects
            hydratable: Hydratable type (e.g., "sound", "playlist", "user")

        Returns:
            Matching hydration data or None
        """
        for item in hydration_data:
            if item.get("hydratable") == hydratable:
                return item.get("data", {})
        return None

    def _track_to_song(
        self,
        track: dict[str, Any],
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert SoundCloud track data to Song object.

        Args:
            track: SoundCloud track data
            list_info: Optional list context

        Returns:
            Song object
        """
        # Get artist info
        user = track.get("user", {})
        artist_name = user.get("username", "Unknown")

        # Get cover URL
        cover_url = track.get("artwork_url")
        if cover_url:
            # Get higher resolution
            cover_url = cover_url.replace("-large.", "-t500x500.")
        elif user.get("avatar_url"):
            cover_url = user.get("avatar_url")

        # Parse duration (in milliseconds)
        duration_ms = track.get("duration", 0)
        duration = duration_ms // 1000 if duration_ms else 0

        # Parse date
        created_at = track.get("created_at", "")
        year = 0
        if created_at:
            try:
                year = int(created_at[:4])
            except (ValueError, IndexError):
                pass

        # Get genres
        genres: list[str] = []
        genre = track.get("genre")
        if genre:
            genres.append(genre)
        tag_list = track.get("tag_list", "")
        if tag_list:
            # SoundCloud tags are space-separated, quoted phrases
            tags = re.findall(r'"([^"]+)"|(\S+)', tag_list)
            for quoted, unquoted in tags:
                tag = quoted or unquoted
                if tag and tag not in genres:
                    genres.append(tag)

        song = Song(
            name=track.get("title", "Unknown"),
            artists=[artist_name],
            artist=artist_name,
            duration=duration,
            platform=Platform.SOUNDCLOUD,
            platform_id=str(track.get("id", "")),
            url=track.get("permalink_url", ""),
            genres=genres,
            year=year,
            date=created_at[:10] if created_at else "",
            cover_url=cover_url,
            artist_id=str(user.get("id", "")),
        )

        # Add list context if provided
        if list_info:
            song.list_name = list_info.get("name")
            song.list_url = list_info.get("url")
            song.list_position = list_info.get("position")
            song.list_length = list_info.get("length")

        return song

    async def get_track(self, url: str) -> Song:
        """
        Fetch a single track by URL.

        Args:
            url: SoundCloud track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("user") or not url_info.get("slug"):
            raise InvalidURLError(f"Invalid SoundCloud track URL: {url}")

        if url_info.get("type") != "track":
            raise InvalidURLError(f"URL is not a track: {url}")

        try:
            soup = await self._fetch_page(url)
            hydration_data = self._extract_hydration_data(soup)

            track_data = self._find_hydration_by_hydratable(hydration_data, "sound")

            if not track_data:
                raise TrackNotFoundError(f"Could not extract track data: {url}")

            return self._track_to_song(track_data)

        except SourceProviderError:
            raise
        except Exception as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        SoundCloud doesn't have albums in the traditional sense.
        This method is implemented to satisfy the interface but
        redirects to get_playlist for sets.

        Args:
            url: SoundCloud URL

        Returns:
            SongList containing tracks

        Raises:
            InvalidURLError: If URL is invalid
        """
        # SoundCloud doesn't have albums, treat as playlist
        return await self.get_playlist(url)

    async def get_playlist(self, url: str) -> SongList:
        """
        Fetch a playlist (set) by URL.

        Args:
            url: SoundCloud playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("user"):
            raise InvalidURLError(f"Invalid SoundCloud URL: {url}")

        if url_info.get("type") != "playlist":
            raise InvalidURLError(f"URL is not a playlist: {url}")

        try:
            soup = await self._fetch_page(url)
            hydration_data = self._extract_hydration_data(soup)

            playlist_data = self._find_hydration_by_hydratable(hydration_data, "playlist")

            if not playlist_data:
                raise SourceProviderError(f"Could not extract playlist data: {url}")

            playlist_name = playlist_data.get("title", "")
            tracks = playlist_data.get("tracks", [])

            # Build list info
            list_info = {
                "name": playlist_name,
                "url": playlist_data.get("permalink_url", url),
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
                url=playlist_data.get("permalink_url", url),
                platform=Platform.SOUNDCLOUD,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError:
            raise
        except Exception as e:
            raise SourceProviderError(f"Failed to fetch playlist: {e}") from e

    async def get_artist(self, url: str) -> SongList:
        """
        Fetch all tracks from an artist by URL.

        Args:
            url: SoundCloud artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("user"):
            raise InvalidURLError(f"Invalid SoundCloud URL: {url}")

        try:
            # Fetch the artist's tracks page
            tracks_url = f"https://soundcloud.com/{url_info['user']}/tracks"
            soup = await self._fetch_page(tracks_url)
            hydration_data = self._extract_hydration_data(soup)

            user_data = self._find_hydration_by_hydratable(hydration_data, "user")

            if not user_data:
                raise SourceProviderError(f"Could not extract artist data: {url}")

            artist_name = user_data.get("username", "Unknown Artist")

            # Get tracks from hydration data
            # SoundCloud's hydration includes a "soundStreamOrPlaylists" for tracks
            tracks: list[dict[str, Any]] = []

            for item in hydration_data:
                data = item.get("data", {})
                if isinstance(data, dict) and data.get("collection"):
                    for track in data.get("collection", []):
                        if track.get("kind") == "track":
                            tracks.append(track)

            # Build list info
            list_info = {
                "name": artist_name,
                "url": user_data.get("permalink_url", url),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for track in tracks:
                if not track.get("id"):
                    continue

                song = self._track_to_song(track, list_info)
                songs.append(song)

            # Update positions
            for i, song in enumerate(songs):
                song.list_position = i + 1
                song.list_length = len(songs)

            return SongList(
                name=artist_name,
                url=user_data.get("permalink_url", url),
                platform=Platform.SOUNDCLOUD,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError:
            raise
        except Exception as e:
            raise SourceProviderError(f"Failed to fetch artist: {e}") from e

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
            import urllib.parse

            encoded_query = urllib.parse.quote(query)
            search_url = f"https://soundcloud.com/search/sounds?q={encoded_query}"

            soup = await self._fetch_page(search_url)
            hydration_data = self._extract_hydration_data(soup)

            # Find search results in hydration data
            tracks: list[dict[str, Any]] = []
            for item in hydration_data:
                data = item.get("data", {})
                if isinstance(data, dict) and data.get("collection"):
                    for track in data.get("collection", []):
                        if track.get("kind") == "track":
                            tracks.append(track)
                            if len(tracks) >= limit:
                                break
                if len(tracks) >= limit:
                    break

            songs = []
            for track in tracks[:limit]:
                if track.get("id"):
                    song = self._track_to_song(track)
                    songs.append(song)

            return songs

        except Exception as e:
            logger.warning(f"SoundCloud search failed for '{query}': {e}")
            return []
