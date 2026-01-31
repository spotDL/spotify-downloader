"""Tidal source provider for fetching song metadata."""

from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from spotdl_core.types.song import Platform, Song, SongList
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# URL patterns for Tidal
TIDAL_URL_PATTERNS = [
    re.compile(r"https?://(?:www\.)?tidal\.com/(?:browse/)?(track|album|playlist|artist)/(\d+)"),
    re.compile(r"https?://listen\.tidal\.com/(track|album|playlist|artist)/(\d+)"),
]


class TidalProvider(SourceProvider):
    """
    Tidal source provider.

    Fetches song metadata from Tidal using web scraping.
    Note: Tidal API requires OAuth which is complex,
    so we use web scraping for basic metadata extraction.
    """

    name = "tidal"
    display_name = "Tidal"
    url_patterns = TIDAL_URL_PATTERNS

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the Tidal provider.

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
    def _extract_id(url: str) -> tuple[str, str] | None:
        """
        Extract resource type and ID from Tidal URL.

        Args:
            url: Tidal URL

        Returns:
            Tuple of (resource_type, resource_id) or None
        """
        for pattern in TIDAL_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return (match.group(1), match.group(2))
        return None

    async def _fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a Tidal page.

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

    def _extract_json_ld(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        Extract JSON-LD structured data from page.

        Args:
            soup: BeautifulSoup object

        Returns:
            JSON-LD data or empty dict
        """
        import json

        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    return data
                if isinstance(data, list) and data:
                    return data[0]
            except json.JSONDecodeError:
                continue
        return {}

    def _extract_meta_tags(self, soup: BeautifulSoup) -> dict[str, str]:
        """
        Extract Open Graph and other meta tags from page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Dictionary of meta tag values
        """
        meta_data: dict[str, str] = {}

        # Open Graph tags
        for meta in soup.find_all("meta", property=True):
            prop = meta.get("property", "")
            content = meta.get("content", "")
            if prop.startswith("og:") or prop.startswith("music:"):
                key = prop.replace("og:", "").replace("music:", "")
                meta_data[key] = content

        # Standard meta tags
        for meta in soup.find_all("meta", attrs={"name": True}):
            name = meta.get("name", "")
            content = meta.get("content", "")
            if name:
                meta_data[name] = content

        return meta_data

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration to seconds.

        Args:
            duration_str: Duration string (e.g., "PT3M45S")

        Returns:
            Duration in seconds
        """
        if not duration_str:
            return 0

        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds

    def _track_to_song(
        self,
        track_data: dict[str, Any],
        meta_data: dict[str, str] | None = None,
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert Tidal track data to Song object.

        Args:
            track_data: Track data from JSON-LD
            meta_data: Optional meta tag data
            list_info: Optional list context

        Returns:
            Song object
        """
        meta_data = meta_data or {}

        # Get artists
        artist_data = track_data.get("byArtist", {})
        if isinstance(artist_data, dict):
            artist_name = artist_data.get("name", "Unknown")
        elif isinstance(artist_data, list) and artist_data:
            artist_name = artist_data[0].get("name", "Unknown") if isinstance(artist_data[0], dict) else "Unknown"
        else:
            artist_name = meta_data.get("musician", "Unknown")

        artists = [artist_name]

        # Get album info
        album_data = track_data.get("inAlbum", {})
        album_name = album_data.get("name", "") if isinstance(album_data, dict) else meta_data.get("album", "")

        # Get cover URL
        cover_url = None
        image_data = track_data.get("image")
        if isinstance(image_data, str):
            cover_url = image_data
        elif isinstance(image_data, dict):
            cover_url = image_data.get("url")
        if not cover_url:
            cover_url = meta_data.get("image")

        # Parse duration
        duration = self._parse_duration(track_data.get("duration", ""))
        if not duration:
            # Try to parse from meta
            duration_meta = meta_data.get("duration", "")
            duration = self._parse_duration(duration_meta)

        # Parse date
        date_published = track_data.get("datePublished", "")
        year = 0
        if date_published:
            try:
                year = int(date_published[:4])
            except (ValueError, IndexError):
                pass

        # Get URL and ID
        url = track_data.get("url", "")
        platform_id = ""
        extracted = self._extract_id(url)
        if extracted:
            platform_id = extracted[1]

        song = Song(
            name=track_data.get("name", meta_data.get("title", "Unknown")),
            artists=artists,
            artist=artist_name,
            duration=duration,
            platform=Platform.TIDAL,
            platform_id=platform_id,
            url=url,
            album_name=album_name,
            album_artist=artist_name,
            year=year,
            date=date_published,
            isrc=track_data.get("isrcCode"),
            cover_url=cover_url,
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
            url: Tidal track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        extracted = self._extract_id(url)

        if not extracted:
            raise InvalidURLError(f"Invalid Tidal URL: {url}")

        resource_type, track_id = extracted

        if resource_type != "track":
            raise InvalidURLError(f"URL is not a track: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)
            meta_data = self._extract_meta_tags(soup)

            if not json_ld and not meta_data:
                raise TrackNotFoundError(f"Could not extract track data: {url}")

            # Use JSON-LD if available, fall back to meta tags
            if json_ld.get("@type") == "MusicRecording":
                json_ld["url"] = url
                return self._track_to_song(json_ld, meta_data)

            # Build from meta tags
            track_data = {
                "name": meta_data.get("title", "Unknown"),
                "url": url,
            }
            return self._track_to_song(track_data, meta_data)

        except SourceProviderError:
            raise
        except Exception as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Tidal album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        extracted = self._extract_id(url)

        if not extracted:
            raise InvalidURLError(f"Invalid Tidal URL: {url}")

        resource_type, album_id = extracted

        if resource_type != "album":
            raise InvalidURLError(f"URL is not an album: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)
            meta_data = self._extract_meta_tags(soup)

            album_name = ""
            tracks: list[dict[str, Any]] = []

            if json_ld.get("@type") == "MusicAlbum":
                album_name = json_ld.get("name", "")
                tracks = json_ld.get("track", [])
            else:
                album_name = meta_data.get("title", "")

            # Build list info
            list_info = {
                "name": album_name,
                "url": url,
                "length": len(tracks),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, track in enumerate(tracks):
                track["inAlbum"] = {"name": album_name}
                if not track.get("image"):
                    track["image"] = json_ld.get("image")

                list_info["position"] = i + 1
                song = self._track_to_song(track, meta_data, list_info)
                songs.append(song)

            return SongList(
                name=album_name,
                url=url,
                platform=Platform.TIDAL,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError:
            raise
        except Exception as e:
            raise SourceProviderError(f"Failed to fetch album: {e}") from e

    async def get_playlist(self, url: str) -> SongList:
        """
        Fetch a playlist by URL.

        Args:
            url: Tidal playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        extracted = self._extract_id(url)

        if not extracted:
            raise InvalidURLError(f"Invalid Tidal URL: {url}")

        resource_type, playlist_id = extracted

        if resource_type != "playlist":
            raise InvalidURLError(f"URL is not a playlist: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)
            meta_data = self._extract_meta_tags(soup)

            playlist_name = ""
            tracks: list[dict[str, Any]] = []

            if json_ld.get("@type") == "MusicPlaylist":
                playlist_name = json_ld.get("name", "")
                tracks = json_ld.get("track", [])
            else:
                playlist_name = meta_data.get("title", "")

            # Build list info
            list_info = {
                "name": playlist_name,
                "url": url,
                "length": len(tracks),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, track in enumerate(tracks):
                list_info["position"] = i + 1
                song = self._track_to_song(track, meta_data, list_info)
                songs.append(song)

            return SongList(
                name=playlist_name,
                url=url,
                platform=Platform.TIDAL,
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
            url: Tidal artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        extracted = self._extract_id(url)

        if not extracted:
            raise InvalidURLError(f"Invalid Tidal URL: {url}")

        resource_type, artist_id = extracted

        if resource_type != "artist":
            raise InvalidURLError(f"URL is not an artist: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)
            meta_data = self._extract_meta_tags(soup)

            artist_name = json_ld.get("name", meta_data.get("title", "Unknown Artist"))

            # Find album links from the page
            album_links: list[str] = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/album/" in href:
                    # Normalize URL
                    if href.startswith("/"):
                        href = f"https://tidal.com{href}"
                    elif not href.startswith("http"):
                        href = f"https://tidal.com/{href}"
                    if href not in album_links:
                        album_links.append(href)

            # Build list info
            list_info = {
                "name": artist_name,
                "url": url,
            }

            # Collect songs from albums
            songs: list[Song] = []
            for album_url in album_links[:20]:  # Limit to first 20 albums
                try:
                    album_songs = await self.get_album(album_url)
                    for song in album_songs.songs:
                        song.list_name = list_info["name"]
                        song.list_url = list_info["url"]
                        songs.append(song)
                except SourceProviderError:
                    continue

            # Update positions
            for i, song in enumerate(songs):
                song.list_position = i + 1
                song.list_length = len(songs)

            return SongList(
                name=artist_name,
                url=url,
                platform=Platform.TIDAL,
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

        Note:
            Tidal search requires API access which needs OAuth.
            This is a placeholder that returns empty results.
        """
        # Tidal search requires OAuth authentication
        return []
