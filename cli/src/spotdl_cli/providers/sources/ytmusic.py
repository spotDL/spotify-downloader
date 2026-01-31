"""YouTube Music source provider for fetching song metadata."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from spotdl_cli.core.types import Platform, Song
from spotdl_cli.providers.base import (
    InvalidURLError,
    SongList,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# URL patterns for YouTube Music
YTMUSIC_URL_PATTERNS = [
    re.compile(r"https?://music\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"),
    re.compile(r"https?://music\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"),
    re.compile(r"https?://music\.youtube\.com/channel/([a-zA-Z0-9_-]+)"),
    re.compile(r"https?://music\.youtube\.com/browse/([a-zA-Z0-9_-]+)"),
]


class YouTubeMusicSourceProvider(SourceProvider):
    """
    YouTube Music source provider.

    Fetches song metadata from YouTube Music using ytmusicapi.
    """

    name = "youtube_music"
    display_name = "YouTube Music"
    url_patterns = YTMUSIC_URL_PATTERNS

    def __init__(self, auth_file: str | None = None) -> None:
        """Initialize the YouTube Music provider."""
        super().__init__()
        self._auth_file = auth_file
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the YTMusic client."""
        if self._client is None:
            from ytmusicapi import YTMusic

            if self._auth_file:
                self._client = YTMusic(self._auth_file)
            else:
                self._client = YTMusic()
        return self._client

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extract video ID from YouTube Music URL."""
        match = re.search(r"[?&]v=([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_playlist_id(url: str) -> str | None:
        """Extract playlist ID from YouTube Music URL."""
        match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_channel_id(url: str) -> str | None:
        """Extract channel/browse ID from YouTube Music URL."""
        match = re.search(r"/(channel|browse)/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(2)
        return None

    def _song_to_song(
        self,
        song_data: dict[str, Any],
    ) -> Song:
        """Convert YouTube Music song data to Song object."""
        # Extract artists
        artists_data = song_data.get("artists", [])
        artists = [a.get("name", "") for a in artists_data if a.get("name")]
        if not artists:
            artists = [song_data.get("author", "Unknown")]

        primary_artist = artists[0] if artists else "Unknown"

        # Get video ID
        video_id = song_data.get("videoId", "")

        # Get duration (may be in different formats)
        duration = 0
        duration_str = song_data.get("duration", "")
        duration_seconds = song_data.get("duration_seconds")

        if duration_seconds:
            duration = int(duration_seconds)
        elif duration_str:
            parts = duration_str.split(":")
            try:
                if len(parts) == 2:
                    duration = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except ValueError:
                pass

        # Get album info
        album_data = song_data.get("album", {}) or {}
        album_name = album_data.get("name", "") if isinstance(album_data, dict) else ""

        # Get thumbnail
        thumbnails = song_data.get("thumbnails", [])
        cover_url = None
        if thumbnails:
            sorted_thumbs = sorted(
                thumbnails,
                key=lambda x: x.get("width", 0) * x.get("height", 0),
                reverse=True,
            )
            cover_url = sorted_thumbs[0].get("url")

        # Get year
        year = 0
        year_str = song_data.get("year", "")
        if year_str:
            try:
                year = int(year_str)
            except ValueError:
                pass

        return Song(
            name=song_data.get("title", "Unknown"),
            artists=artists,
            artist=primary_artist,
            duration=duration,
            platform=Platform.YOUTUBE_MUSIC,
            platform_id=video_id,
            url=f"https://music.youtube.com/watch?v={video_id}",
            album_name=album_name,
            album_artist=primary_artist,
            year=year,
            explicit=song_data.get("isExplicit", False),
            cover_url=cover_url,
        )

    async def get_track(self, url: str) -> Song:
        """Fetch a single track by URL."""
        video_id = self._extract_video_id(url)

        if not video_id:
            raise InvalidURLError(f"Invalid YouTube Music track URL: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            # Get song info
            song_data = await loop.run_in_executor(None, client.get_song, video_id)

            if song_data is None:
                raise TrackNotFoundError(f"Track not found: {url}")

            # ytmusicapi returns video details in a specific structure
            video_details = song_data.get("videoDetails", {})

            # Build a unified song data structure
            unified_data = {
                "videoId": video_id,
                "title": video_details.get("title", ""),
                "author": video_details.get("author", ""),
                "duration_seconds": video_details.get("lengthSeconds"),
                "thumbnails": video_details.get("thumbnail", {}).get("thumbnails", []),
            }

            # Try to get more metadata from music info
            music_info = song_data.get("microformat", {}).get(
                "microformatDataRenderer", {}
            )
            if music_info:
                unified_data["artists"] = [{"name": music_info.get("artistNames", "")}]

            return self._song_to_song(unified_data)

        except Exception as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """Fetch an album by URL."""
        browse_id = self._extract_channel_id(url) or self._extract_playlist_id(url)

        if not browse_id:
            raise InvalidURLError(f"Invalid YouTube Music album URL: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            album_data = await loop.run_in_executor(None, client.get_album, browse_id)

            if album_data is None:
                raise SourceProviderError(f"Album not found: {url}")

            album_name = album_data.get("title", "")
            tracks = album_data.get("tracks", [])

            # Convert tracks to songs
            songs: list[Song] = []
            for track in tracks:
                song = self._song_to_song(track)
                songs.append(song)

            return SongList(
                name=album_name,
                url=url,
                platform=Platform.YOUTUBE_MUSIC,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except Exception as e:
            raise SourceProviderError(f"Failed to fetch album: {e}") from e

    async def get_playlist(self, url: str) -> SongList:
        """Fetch a playlist by URL."""
        playlist_id = self._extract_playlist_id(url)

        if not playlist_id:
            raise InvalidURLError(f"Invalid YouTube Music playlist URL: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            playlist_data = await loop.run_in_executor(
                None, lambda: client.get_playlist(playlist_id, limit=None)
            )

            if playlist_data is None:
                raise SourceProviderError(f"Playlist not found: {url}")

            playlist_name = playlist_data.get("title", "")
            tracks = playlist_data.get("tracks", [])

            # Convert tracks to songs
            songs: list[Song] = []
            for track in tracks:
                if not track.get("videoId"):
                    continue
                song = self._song_to_song(track)
                songs.append(song)

            return SongList(
                name=playlist_name,
                url=url,
                platform=Platform.YOUTUBE_MUSIC,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except Exception as e:
            raise SourceProviderError(f"Failed to fetch playlist: {e}") from e

    async def get_artist(self, url: str) -> SongList:
        """Fetch all tracks from an artist by URL."""
        channel_id = self._extract_channel_id(url)

        if not channel_id:
            raise InvalidURLError(f"Invalid YouTube Music artist URL: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            artist_data = await loop.run_in_executor(
                None, client.get_artist, channel_id
            )

            if artist_data is None:
                raise SourceProviderError(f"Artist not found: {url}")

            artist_name = artist_data.get("name", "")

            # Collect songs from artist's top songs
            songs: list[Song] = []
            top_songs = artist_data.get("songs", {}).get("results", [])
            for track in top_songs:
                if track.get("videoId"):
                    song = self._song_to_song(track)
                    songs.append(song)

            return SongList(
                name=artist_name,
                url=url,
                platform=Platform.YOUTUBE_MUSIC,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except Exception as e:
            raise SourceProviderError(f"Failed to fetch artist: {e}") from e

    async def search(self, query: str, limit: int = 10) -> list[Song]:
        """Search for tracks by query."""
        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            results = await loop.run_in_executor(
                None,
                lambda: client.search(query, filter="songs", limit=limit),
            )

            songs = []
            for result in results:
                if result.get("videoId"):
                    song = self._song_to_song(result)
                    songs.append(song)

            return songs

        except Exception:
            return []
