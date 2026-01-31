"""Bandcamp source provider for fetching song metadata."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from spotdl_core.core.types.song import Platform, Song, SongList
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# URL patterns for Bandcamp
BANDCAMP_URL_PATTERNS = [
    re.compile(r"https?://([^.]+)\.bandcamp\.com/(track|album)/([^/?]+)"),
    re.compile(r"https?://([^.]+)\.bandcamp\.com/?$"),  # Artist page
]


class BandcampProvider(SourceProvider):
    """
    Bandcamp source provider.

    Fetches song metadata from Bandcamp using web scraping.
    """

    name = "bandcamp"
    display_name = "Bandcamp"
    url_patterns = BANDCAMP_URL_PATTERNS

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize the Bandcamp provider.

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
        Extract information from Bandcamp URL.

        Args:
            url: Bandcamp URL

        Returns:
            Dictionary with subdomain, type, and slug
        """
        # Track or album pattern
        match = re.search(r"https?://([^.]+)\.bandcamp\.com/(track|album)/([^/?]+)", url)
        if match:
            return {
                "subdomain": match.group(1),
                "type": match.group(2),
                "slug": match.group(3),
            }

        # Artist page pattern
        match = re.search(r"https?://([^.]+)\.bandcamp\.com/?$", url)
        if match:
            return {
                "subdomain": match.group(1),
                "type": "artist",
                "slug": None,
            }

        return {"subdomain": None, "type": None, "slug": None}

    async def _fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse a Bandcamp page.

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

    def _extract_tralbum_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        Extract TralbumData from Bandcamp page.

        Bandcamp uses TralbumData for track/album information.

        Args:
            soup: BeautifulSoup object

        Returns:
            TralbumData dictionary
        """
        for script in soup.find_all("script"):
            text = script.string or ""
            if "TralbumData" in text:
                # Extract the JSON object
                match = re.search(r"TralbumData\s*=\s*(\{.*?\});", text, re.DOTALL)
                if match:
                    try:
                        # Clean up the JSON (remove comments, trailing commas)
                        json_str = match.group(1)
                        # Remove JavaScript comments
                        json_str = re.sub(r"//.*?\n", "\n", json_str)
                        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

        # Try data-tralbum attribute
        tralbum_elem = soup.find(attrs={"data-tralbum": True})
        if tralbum_elem:
            try:
                return json.loads(tralbum_elem["data-tralbum"])
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        return {}

    def _extract_band_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        Extract BandData from Bandcamp page.

        Args:
            soup: BeautifulSoup object

        Returns:
            BandData dictionary
        """
        for script in soup.find_all("script"):
            text = script.string or ""
            if "BandData" in text:
                match = re.search(r"BandData\s*=\s*(\{.*?\});", text, re.DOTALL)
                if match:
                    try:
                        json_str = match.group(1)
                        json_str = re.sub(r"//.*?\n", "\n", json_str)
                        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
        return {}

    def _extract_json_ld(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        Extract JSON-LD structured data from page.

        Args:
            soup: BeautifulSoup object

        Returns:
            JSON-LD data or empty dict
        """
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

    def _track_to_song(
        self,
        track: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert Bandcamp track data to Song object.

        Args:
            track: Bandcamp track data
            album_data: Optional album context
            list_info: Optional list context

        Returns:
            Song object
        """
        album_data = album_data or {}

        # Get artist name
        artist_name = (
            track.get("artist")
            or album_data.get("artist")
            or track.get("band_name")
            or "Unknown"
        )

        # Get album name
        album_name = album_data.get("title", "") or album_data.get("album_title", "")

        # Get cover URL
        cover_url = track.get("art_url") or album_data.get("art_url")
        if cover_url:
            # Get higher resolution
            cover_url = re.sub(r"_\d+\.jpg$", "_10.jpg", cover_url)

        # Parse duration
        duration = 0
        duration_val = track.get("duration")
        if duration_val:
            if isinstance(duration_val, (int, float)):
                duration = int(duration_val)
            elif isinstance(duration_val, str):
                # Parse MM:SS or HH:MM:SS format
                parts = duration_val.split(":")
                try:
                    if len(parts) == 2:
                        duration = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                except ValueError:
                    pass

        # Get release date
        release_date = album_data.get("release_date", "") or track.get("release_date", "")
        year = 0
        if release_date:
            try:
                # Bandcamp dates can be in various formats
                date_match = re.search(r"(\d{4})", str(release_date))
                if date_match:
                    year = int(date_match.group(1))
            except ValueError:
                pass

        # Get URL
        url = track.get("url") or track.get("link_url", "")
        if not url and track.get("title_link"):
            # Build URL from title_link
            base_url = album_data.get("url", "").rsplit("/", 2)[0]
            url = f"{base_url}{track['title_link']}"

        # Get platform ID
        platform_id = str(track.get("id", "") or track.get("track_id", ""))

        # Get tags/genres
        genres: list[str] = []
        tags = album_data.get("tags", []) or track.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                else:
                    tag_name = str(tag)
                if tag_name and tag_name not in genres:
                    genres.append(tag_name)

        song = Song(
            name=track.get("title", track.get("name", "Unknown")),
            artists=[artist_name],
            artist=artist_name,
            duration=duration,
            platform=Platform.BANDCAMP,
            platform_id=platform_id,
            url=url,
            album_name=album_name,
            album_artist=artist_name,
            track_number=track.get("track_num", 1),
            year=year,
            date=str(release_date)[:10] if release_date else "",
            genres=genres,
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
            url: Bandcamp track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("subdomain"):
            raise InvalidURLError(f"Invalid Bandcamp URL: {url}")

        if url_info.get("type") != "track":
            raise InvalidURLError(f"URL is not a track: {url}")

        try:
            soup = await self._fetch_page(url)
            tralbum_data = self._extract_tralbum_data(soup)
            json_ld = self._extract_json_ld(soup)

            if not tralbum_data and not json_ld:
                raise TrackNotFoundError(f"Could not extract track data: {url}")

            # Get track from trackinfo
            trackinfo = tralbum_data.get("trackinfo", [])
            if trackinfo and len(trackinfo) > 0:
                track = trackinfo[0]
                track["url"] = url
                return self._track_to_song(track, tralbum_data)

            # Fall back to JSON-LD
            if json_ld.get("@type") == "MusicRecording":
                track_data = {
                    "title": json_ld.get("name", ""),
                    "url": url,
                    "duration": json_ld.get("duration", ""),
                }
                album_data = {
                    "artist": json_ld.get("byArtist", {}).get("name", ""),
                    "art_url": json_ld.get("image"),
                }
                return self._track_to_song(track_data, album_data)

            raise TrackNotFoundError(f"Track data not found: {url}")

        except SourceProviderError:
            raise
        except Exception as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Bandcamp album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("subdomain"):
            raise InvalidURLError(f"Invalid Bandcamp URL: {url}")

        if url_info.get("type") != "album":
            raise InvalidURLError(f"URL is not an album: {url}")

        try:
            soup = await self._fetch_page(url)
            tralbum_data = self._extract_tralbum_data(soup)

            if not tralbum_data:
                raise SourceProviderError(f"Could not extract album data: {url}")

            album_name = tralbum_data.get("current", {}).get("title", "")
            trackinfo = tralbum_data.get("trackinfo", [])

            # Build album data for context
            album_data = {
                "title": album_name,
                "artist": tralbum_data.get("artist", ""),
                "art_url": tralbum_data.get("art_id"),
                "release_date": tralbum_data.get("current", {}).get("release_date"),
                "tags": tralbum_data.get("tags", []),
                "url": url,
            }

            # Get art URL
            art_id = tralbum_data.get("art_id")
            if art_id:
                album_data["art_url"] = f"https://f4.bcbits.com/img/a{art_id}_10.jpg"

            # Build list info
            list_info = {
                "name": album_name,
                "url": url,
                "length": len(trackinfo),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, track in enumerate(trackinfo):
                # Build track URL
                if track.get("title_link"):
                    base_url = url.rsplit("/", 2)[0]
                    track["url"] = f"{base_url}{track['title_link']}"

                list_info["position"] = i + 1
                song = self._track_to_song(track, album_data, list_info)
                songs.append(song)

            return SongList(
                name=album_name,
                url=url,
                platform=Platform.BANDCAMP,
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

        Bandcamp doesn't have playlists in the traditional sense.
        This redirects to get_album.

        Args:
            url: Bandcamp URL

        Returns:
            SongList containing tracks
        """
        # Bandcamp doesn't have playlists, treat as album
        return await self.get_album(url)

    async def get_artist(self, url: str) -> SongList:
        """
        Fetch all tracks from an artist by URL.

        Args:
            url: Bandcamp artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        url_info = self._extract_url_info(url)

        if not url_info.get("subdomain"):
            raise InvalidURLError(f"Invalid Bandcamp URL: {url}")

        try:
            # Normalize URL to artist page
            if url_info.get("type") != "artist":
                url = f"https://{url_info['subdomain']}.bandcamp.com"

            soup = await self._fetch_page(url)
            band_data = self._extract_band_data(soup)

            artist_name = band_data.get("name", url_info.get("subdomain", "Unknown Artist"))

            # Find album links from the page
            album_links: list[str] = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/album/" in href:
                    # Normalize URL
                    if href.startswith("/"):
                        href = f"https://{url_info['subdomain']}.bandcamp.com{href}"
                    elif not href.startswith("http"):
                        href = f"https://{url_info['subdomain']}.bandcamp.com/{href}"
                    if href not in album_links:
                        album_links.append(href)

            # Also find track links
            track_links: list[str] = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "/track/" in href:
                    if href.startswith("/"):
                        href = f"https://{url_info['subdomain']}.bandcamp.com{href}"
                    elif not href.startswith("http"):
                        href = f"https://{url_info['subdomain']}.bandcamp.com/{href}"
                    if href not in track_links:
                        track_links.append(href)

            # Build list info
            list_info = {
                "name": artist_name,
                "url": url,
            }

            # Collect songs from albums
            songs: list[Song] = []
            seen_ids: set[str] = set()

            for album_url in album_links[:20]:  # Limit to first 20 albums
                try:
                    album_songs = await self.get_album(album_url)
                    for song in album_songs.songs:
                        if song.platform_id not in seen_ids:
                            seen_ids.add(song.platform_id)
                            song.list_name = list_info["name"]
                            song.list_url = list_info["url"]
                            songs.append(song)
                except SourceProviderError:
                    continue

            # Add individual tracks not in albums
            for track_url in track_links[:50]:
                try:
                    track = await self.get_track(track_url)
                    if track.platform_id not in seen_ids:
                        seen_ids.add(track.platform_id)
                        track.list_name = list_info["name"]
                        track.list_url = list_info["url"]
                        songs.append(track)
                except SourceProviderError:
                    continue

            # Update positions
            for i, song in enumerate(songs):
                song.list_position = i + 1
                song.list_length = len(songs)

            return SongList(
                name=artist_name,
                url=url,
                platform=Platform.BANDCAMP,
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
            search_url = f"https://bandcamp.com/search?q={encoded_query}&item_type=t"

            soup = await self._fetch_page(search_url)

            # Find search results
            songs: list[Song] = []
            results = soup.find_all("li", class_="searchresult")

            for result in results[:limit]:
                try:
                    # Get track URL
                    link = result.find("a", class_="artcont")
                    if not link:
                        continue
                    track_url = link.get("href", "")
                    if not track_url or "/track/" not in track_url:
                        continue

                    # Get basic info from search result
                    heading = result.find("div", class_="heading")
                    subhead = result.find("div", class_="subhead")

                    name = heading.get_text(strip=True) if heading else ""
                    artist_album = subhead.get_text(strip=True) if subhead else ""

                    # Parse "by Artist from Album"
                    artist_name = "Unknown"
                    if " by " in artist_album:
                        parts = artist_album.split(" by ", 1)
                        if len(parts) > 1:
                            artist_part = parts[1]
                            if " from " in artist_part:
                                artist_name = artist_part.split(" from ")[0].strip()
                            else:
                                artist_name = artist_part.strip()

                    # Get cover
                    img = result.find("img")
                    cover_url = img.get("src") if img else None

                    song = Song(
                        name=name,
                        artists=[artist_name],
                        artist=artist_name,
                        duration=0,
                        platform=Platform.BANDCAMP,
                        platform_id="",
                        url=track_url,
                        cover_url=cover_url,
                    )
                    songs.append(song)

                except Exception:
                    continue

            return songs

        except Exception:
            return []
