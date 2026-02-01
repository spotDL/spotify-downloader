"""Apple Music source provider for fetching song metadata."""

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

# URL patterns for Apple Music
APPLE_MUSIC_URL_PATTERNS = [
    re.compile(
        r"https?://music\.apple\.com/(\w+)/(album|playlist|artist)/([^/]+)/(\d+)(?:\?i=(\d+))?"
    ),
    re.compile(r"https?://music\.apple\.com/(\w+)/album/([^/]+)/(\d+)\?i=(\d+)"),  # Track in album
]


class AppleMusicProvider(SourceProvider):
    """
    Apple Music source provider.

    Fetches song metadata from Apple Music using web scraping.
    Note: Apple Music API requires developer token which is complex to obtain,
    so we use web scraping for basic metadata extraction.
    """

    name = "apple_music"
    display_name = "Apple Music"
    url_patterns = APPLE_MUSIC_URL_PATTERNS

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the Apple Music provider.

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
    def _extract_url_info(url: str) -> dict[str, str | None]:
        """
        Extract information from Apple Music URL.

        Args:
            url: Apple Music URL

        Returns:
            Dictionary with country, type, name, id, and track_id
        """
        # Track in album pattern: /album/name/id?i=track_id
        track_match = re.search(
            r"music\.apple\.com/(\w+)/album/([^/]+)/(\d+)\?i=(\d+)", url
        )
        if track_match:
            return {
                "country": track_match.group(1),
                "type": "track",
                "name": track_match.group(2),
                "id": track_match.group(3),
                "track_id": track_match.group(4),
            }

        # Standard pattern: /type/name/id
        standard_match = re.search(
            r"music\.apple\.com/(\w+)/(album|playlist|artist)/([^/]+)/(\d+)", url
        )
        if standard_match:
            return {
                "country": standard_match.group(1),
                "type": standard_match.group(2),
                "name": standard_match.group(3),
                "id": standard_match.group(4),
                "track_id": None,
            }

        return {"country": None, "type": None, "name": None, "id": None, "track_id": None}

    async def _fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse an Apple Music page.

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
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert Apple Music track data to Song object.

        Args:
            track_data: Track data from JSON-LD or scraping
            list_info: Optional list context

        Returns:
            Song object
        """
        # Get artists
        artist_name = track_data.get("byArtist", {})
        if isinstance(artist_name, dict):
            artist_name = artist_name.get("name", "Unknown")
        elif isinstance(artist_name, list) and artist_name:
            artist_name = artist_name[0].get("name", "Unknown") if isinstance(artist_name[0], dict) else "Unknown"
        else:
            artist_name = str(artist_name) if artist_name else "Unknown"

        artists = [artist_name]

        # Get album info
        album_data = track_data.get("inAlbum", {})
        album_name = album_data.get("name", "") if isinstance(album_data, dict) else ""

        # Get cover URL
        cover_url = None
        image_data = track_data.get("image")
        if isinstance(image_data, str):
            cover_url = image_data
        elif isinstance(image_data, dict):
            cover_url = image_data.get("url")

        # Parse duration
        duration = self._parse_duration(track_data.get("duration", ""))

        # Parse date
        date_published = track_data.get("datePublished", "")
        year = 0
        if date_published:
            try:
                year = int(date_published[:4])
            except (ValueError, IndexError):
                pass

        # Get URL
        url = track_data.get("url", "")

        # Extract ID from URL
        platform_id = ""
        url_info = self._extract_url_info(url)
        if url_info.get("track_id"):
            platform_id = url_info["track_id"]
        elif url_info.get("id"):
            platform_id = url_info["id"]

        song = Song(
            name=track_data.get("name", "Unknown"),
            artists=artists,
            artist=artist_name,
            duration=duration,
            platform=Platform.APPLE_MUSIC,
            platform_id=platform_id,
            url=url,
            album_name=album_name,
            album_artist=artist_name,
            year=year,
            date=date_published,
            explicit=track_data.get("contentRating") == "explicit",
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
            url: Apple Music track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("id"):
            raise InvalidURLError(f"Invalid Apple Music URL: {url}")

        if url_info.get("type") not in ("track", "album") or (
            url_info.get("type") == "album" and not url_info.get("track_id")
        ):
            raise InvalidURLError(f"URL is not a track: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)

            if not json_ld:
                raise TrackNotFoundError(f"Could not extract track data: {url}")

            # For track URLs, JSON-LD should contain the track
            if json_ld.get("@type") == "MusicRecording":
                json_ld["url"] = url
                return self._track_to_song(json_ld)

            # For album URLs with track ID, find the track in the album
            if json_ld.get("@type") == "MusicAlbum":
                tracks = json_ld.get("track", [])
                track_id = url_info.get("track_id")

                for track in tracks:
                    track_url = track.get("url", "")
                    if track_id and track_id in track_url:
                        track["url"] = track_url
                        track["inAlbum"] = {"name": json_ld.get("name", "")}
                        track["image"] = json_ld.get("image")
                        return self._track_to_song(track)

            raise TrackNotFoundError(f"Track not found: {url}")

        except SourceProviderError:
            raise
        except Exception as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Apple Music album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("id"):
            raise InvalidURLError(f"Invalid Apple Music URL: {url}")

        if url_info.get("type") != "album":
            raise InvalidURLError(f"URL is not an album: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)

            if not json_ld or json_ld.get("@type") != "MusicAlbum":
                raise SourceProviderError(f"Could not extract album data: {url}")

            album_name = json_ld.get("name", "")
            tracks = json_ld.get("track", [])

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
                track["image"] = json_ld.get("image")

                list_info["position"] = i + 1
                song = self._track_to_song(track, list_info)
                songs.append(song)

            return SongList(
                name=album_name,
                url=url,
                platform=Platform.APPLE_MUSIC,
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
            url: Apple Music playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("id"):
            raise InvalidURLError(f"Invalid Apple Music URL: {url}")

        if url_info.get("type") != "playlist":
            raise InvalidURLError(f"URL is not a playlist: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)

            if not json_ld or json_ld.get("@type") != "MusicPlaylist":
                raise SourceProviderError(f"Could not extract playlist data: {url}")

            playlist_name = json_ld.get("name", "")
            tracks = json_ld.get("track", [])

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
                song = self._track_to_song(track, list_info)
                songs.append(song)

            return SongList(
                name=playlist_name,
                url=url,
                platform=Platform.APPLE_MUSIC,
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
            url: Apple Music artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("id"):
            raise InvalidURLError(f"Invalid Apple Music URL: {url}")

        if url_info.get("type") != "artist":
            raise InvalidURLError(f"URL is not an artist: {url}")

        try:
            soup = await self._fetch_page(url)
            json_ld = self._extract_json_ld(soup)

            artist_name = json_ld.get("name", "Unknown Artist")

            # Apple Music artist pages don't include full discography in JSON-LD
            # We need to find album links from the page
            album_links: list[str] = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/album/" in href and "music.apple.com" in href:
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
                platform=Platform.APPLE_MUSIC,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except SourceProviderError:
            raise
        except Exception as e:
            raise SourceProviderError(f"Failed to fetch artist: {e}") from e

    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """
        Search for tracks by query using iTunes Search API.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching Song objects

        Note:
            Uses iTunes Search API which is free and doesn't require authentication.
            Results are for Apple Music tracks available in the iTunes Store.
        """
        from urllib.parse import quote_plus

        client = await self._get_client()

        # iTunes Search API endpoint
        search_url = (
            f"https://itunes.apple.com/search?"
            f"term={quote_plus(query)}&"
            f"media=music&"
            f"entity=song&"
            f"limit={limit}"
        )

        try:
            response = await client.get(search_url)
            response.raise_for_status()
            data = response.json()

            songs: list[Song] = []
            results = data.get("results", [])

            for track in results:
                try:
                    # Extract artist info
                    artist = track.get("artistName", "Unknown")
                    artists = [artist]

                    # Extract album info
                    album_name = track.get("collectionName", "")
                    album_artist = track.get("artistName", artist)

                    # Get cover URL (use higher resolution)
                    cover_url = track.get("artworkUrl100", "")
                    if cover_url:
                        # Replace 100x100 with 600x600 for higher resolution
                        cover_url = cover_url.replace("100x100", "600x600")

                    # Build Apple Music URL
                    track_id = str(track.get("trackId", ""))
                    collection_id = str(track.get("collectionId", ""))
                    # Apple Music URL format: /album/{album-slug}/{collection_id}?i={track_id}
                    track_url = track.get("trackViewUrl", "")
                    if not track_url and track_id:
                        track_url = f"https://music.apple.com/us/album/{collection_id}?i={track_id}"

                    # Parse release date for year
                    release_date = track.get("releaseDate", "")
                    year = 0
                    if release_date:
                        try:
                            year = int(release_date[:4])
                        except (ValueError, IndexError):
                            pass

                    # Duration is in milliseconds from iTunes API
                    duration_ms = track.get("trackTimeMillis", 0)
                    duration = duration_ms // 1000 if duration_ms else 0

                    song = Song(
                        name=track.get("trackName", "Unknown"),
                        artists=artists,
                        artist=artist,
                        duration=duration,
                        platform=Platform.APPLE_MUSIC,
                        platform_id=track_id,
                        url=track_url,
                        album_name=album_name,
                        album_artist=album_artist,
                        year=year,
                        date=release_date[:10] if release_date else None,
                        cover_url=cover_url,
                        explicit=track.get("trackExplicitness") == "explicit",
                        genres=[track.get("primaryGenreName")] if track.get("primaryGenreName") else [],
                    )
                    songs.append(song)

                except (KeyError, TypeError):
                    continue

            return songs

        except httpx.HTTPError:
            # Return empty list on error rather than raising
            return []
        except Exception:
            return []
