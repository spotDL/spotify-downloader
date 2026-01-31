"""Spotify source provider for fetching song metadata."""

from __future__ import annotations

import asyncio
import re
from functools import lru_cache
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from spotdl_core.types.song import Platform, Song, SongList
from spotdl_core.providers.sources.base import (
    InvalidURLError,
    SourceProvider,
    SourceProviderError,
    TrackNotFoundError,
)

# URL patterns for Spotify
SPOTIFY_URL_PATTERNS = [
    re.compile(
        r"https?://open\.spotify\.com/(?:intl-\w+/)?(track|album|playlist|artist)/([a-zA-Z0-9]+)"
    ),
    re.compile(r"spotify:(track|album|playlist|artist):([a-zA-Z0-9]+)"),
]


class SpotifyClientError(SourceProviderError):
    """Raised when Spotify client encounters an error."""


class SpotifyProvider(SourceProvider):
    """
    Spotify source provider.

    Fetches song metadata from Spotify using the Spotify Web API.
    """

    name = "spotify"
    display_name = "Spotify"
    url_patterns = SPOTIFY_URL_PATTERNS

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_auth: bool = False,
        auth_token: str | None = None,
    ) -> None:
        """
        Initialize the Spotify provider.

        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            user_auth: Whether to use user authentication (OAuth)
            auth_token: Pre-existing auth token
        """
        super().__init__()

        self._client: spotipy.Spotify | None = None
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_auth = user_auth
        self._auth_token = auth_token

    def _get_client(self) -> spotipy.Spotify:
        """Get or create the Spotify client."""
        if self._client is not None:
            return self._client

        if self._auth_token:
            self._client = spotipy.Spotify(auth=self._auth_token)
        elif self._user_auth:
            auth_manager = SpotifyOAuth(
                client_id=self._client_id,
                client_secret=self._client_secret,
                redirect_uri="http://127.0.0.1:9900/",
                scope="user-library-read user-follow-read playlist-read-private",
            )
            self._client = spotipy.Spotify(auth_manager=auth_manager)
        else:
            auth_manager = SpotifyClientCredentials(
                client_id=self._client_id,
                client_secret=self._client_secret,
            )
            self._client = spotipy.Spotify(auth_manager=auth_manager)

        return self._client

    @staticmethod
    def _extract_id(url: str) -> tuple[str, str]:
        """
        Extract resource type and ID from Spotify URL.

        Args:
            url: Spotify URL or URI

        Returns:
            Tuple of (resource_type, resource_id)

        Raises:
            InvalidURLError: If URL is invalid
        """
        for pattern in SPOTIFY_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1), match.group(2)

        raise InvalidURLError(f"Invalid Spotify URL: {url}")

    def _track_to_song(
        self,
        track: dict[str, Any],
        artist_data: dict[str, Any] | None = None,
        album_data: dict[str, Any] | None = None,
        list_info: dict[str, Any] | None = None,
    ) -> Song:
        """
        Convert Spotify track data to Song object.

        Args:
            track: Spotify track data
            artist_data: Optional pre-fetched artist data
            album_data: Optional pre-fetched album data
            list_info: Optional list context (playlist/album info)

        Returns:
            Song object
        """
        # Get album info
        album = album_data or track.get("album", {})

        # Get artist info
        artists = [artist["name"] for artist in track.get("artists", [])]
        primary_artist = artists[0] if artists else "Unknown"

        # Get genres (from artist data if available)
        genres: list[str] = []
        if artist_data:
            genres = artist_data.get("genres", [])
        if album:
            genres.extend(album.get("genres", []))

        # Get cover URL (highest resolution)
        cover_url = None
        images = album.get("images", [])
        if images:
            # Sort by resolution and get largest
            sorted_images = sorted(
                images,
                key=lambda x: x.get("width", 0) * x.get("height", 0),
                reverse=True,
            )
            cover_url = sorted_images[0].get("url")

        # Get copyright
        copyright_text = None
        copyrights = album.get("copyrights", [])
        if copyrights:
            copyright_text = copyrights[0].get("text")

        # Parse release date
        release_date = album.get("release_date", "")
        year = 0
        if release_date:
            try:
                year = int(release_date[:4])
            except (ValueError, IndexError):
                pass

        # Build song
        song = Song(
            name=track.get("name", "Unknown"),
            artists=artists,
            artist=primary_artist,
            duration=int(track.get("duration_ms", 0) / 1000),
            platform=Platform.SPOTIFY,
            platform_id=track.get("id", ""),
            url=track.get("external_urls", {}).get("spotify", ""),
            album_name=album.get("name", ""),
            album_artist=album.get("artists", [{}])[0].get("name", "")
            if album.get("artists")
            else "",
            album_id=album.get("id"),
            album_type=album.get("album_type"),
            genres=genres,
            disc_number=track.get("disc_number", 1),
            disc_count=1,  # Will be updated if album data is available
            track_number=track.get("track_number", 1),
            tracks_count=album.get("total_tracks", 1),
            year=year,
            date=release_date,
            isrc=track.get("external_ids", {}).get("isrc"),
            explicit=track.get("explicit", False),
            publisher=album.get("label", ""),
            cover_url=cover_url,
            copyright_text=copyright_text,
            popularity=track.get("popularity"),
            artist_id=track.get("artists", [{}])[0].get("id"),
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
            url: Spotify track URL

        Returns:
            Song object

        Raises:
            InvalidURLError: If URL is invalid
            TrackNotFoundError: If track cannot be found
        """
        resource_type, track_id = self._extract_id(url)

        if resource_type != "track":
            raise InvalidURLError(f"URL is not a track: {url}")

        client = self._get_client()

        # Run sync API calls in executor
        loop = asyncio.get_event_loop()

        try:
            # Fetch track
            track = await loop.run_in_executor(None, client.track, track_id)

            if track is None:
                raise TrackNotFoundError(f"Track not found: {url}")

            # Validate track
            if track.get("duration_ms", 0) == 0 or not track.get("name", "").strip():
                raise TrackNotFoundError(f"Track no longer exists: {url}")

            # Fetch additional metadata
            primary_artist_id = track.get("artists", [{}])[0].get("id")
            album_id = track.get("album", {}).get("id")

            artist_data = None
            album_data = None

            if primary_artist_id:
                artist_data = await loop.run_in_executor(
                    None, client.artist, primary_artist_id
                )

            if album_id:
                album_data = await loop.run_in_executor(None, client.album, album_id)

            return self._track_to_song(track, artist_data, album_data)

        except spotipy.SpotifyException as e:
            raise TrackNotFoundError(f"Failed to fetch track: {e}") from e

    async def get_album(self, url: str) -> SongList:
        """
        Fetch an album by URL.

        Args:
            url: Spotify album URL

        Returns:
            SongList containing album tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If album cannot be found
        """
        resource_type, album_id = self._extract_id(url)

        if resource_type != "album":
            raise InvalidURLError(f"URL is not an album: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            # Fetch album
            album = await loop.run_in_executor(None, client.album, album_id)

            if album is None:
                raise SourceProviderError(f"Album not found: {url}")

            # Get all tracks (handle pagination)
            tracks_data = album.get("tracks", {})
            all_tracks = tracks_data.get("items", [])

            # Paginate through remaining tracks
            while tracks_data.get("next"):
                tracks_data = await loop.run_in_executor(
                    None, client.next, tracks_data
                )
                if tracks_data:
                    all_tracks.extend(tracks_data.get("items", []))

            # Build list info
            list_info = {
                "name": album.get("name", ""),
                "url": album.get("external_urls", {}).get("spotify", ""),
                "length": len(all_tracks),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, track in enumerate(all_tracks):
                if track is None or track.get("is_local", False):
                    continue

                list_info["position"] = i + 1
                song = self._track_to_song(track, album_data=album, list_info=list_info)
                songs.append(song)

            return SongList(
                name=album.get("name", ""),
                url=album.get("external_urls", {}).get("spotify", ""),
                platform=Platform.SPOTIFY,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except spotipy.SpotifyException as e:
            raise SourceProviderError(f"Failed to fetch album: {e}") from e

    async def get_playlist(self, url: str) -> SongList:
        """
        Fetch a playlist by URL.

        Args:
            url: Spotify playlist URL

        Returns:
            SongList containing playlist tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If playlist cannot be found
        """
        resource_type, playlist_id = self._extract_id(url)

        if resource_type != "playlist":
            raise InvalidURLError(f"URL is not a playlist: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            # Fetch playlist
            playlist = await loop.run_in_executor(None, client.playlist, playlist_id)

            if playlist is None:
                raise SourceProviderError(f"Playlist not found: {url}")

            # Get all tracks (handle pagination)
            tracks_data = playlist.get("tracks", {})
            all_items = tracks_data.get("items", [])

            while tracks_data.get("next"):
                tracks_data = await loop.run_in_executor(
                    None, client.next, tracks_data
                )
                if tracks_data:
                    all_items.extend(tracks_data.get("items", []))

            # Build list info
            list_info = {
                "name": playlist.get("name", ""),
                "url": playlist.get("external_urls", {}).get("spotify", ""),
                "length": len(all_items),
            }

            # Convert tracks to songs
            songs: list[Song] = []
            for i, item in enumerate(all_items):
                track = item.get("track")
                if track is None or track.get("is_local", False):
                    continue
                if track.get("type") != "track":
                    continue

                list_info["position"] = i + 1
                song = self._track_to_song(track, list_info=list_info)
                songs.append(song)

            return SongList(
                name=playlist.get("name", ""),
                url=playlist.get("external_urls", {}).get("spotify", ""),
                platform=Platform.SPOTIFY,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except spotipy.SpotifyException as e:
            raise SourceProviderError(f"Failed to fetch playlist: {e}") from e

    async def get_artist(self, url: str) -> SongList:
        """
        Fetch all tracks from an artist by URL.

        Args:
            url: Spotify artist URL

        Returns:
            SongList containing artist's tracks

        Raises:
            InvalidURLError: If URL is invalid
            SourceProviderError: If artist cannot be found
        """
        resource_type, artist_id = self._extract_id(url)

        if resource_type != "artist":
            raise InvalidURLError(f"URL is not an artist: {url}")

        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            # Fetch artist
            artist = await loop.run_in_executor(None, client.artist, artist_id)

            if artist is None:
                raise SourceProviderError(f"Artist not found: {url}")

            # Get all albums
            albums_data = await loop.run_in_executor(
                None,
                lambda: client.artist_albums(
                    artist_id, album_type="album,single,compilation", limit=50
                ),
            )

            all_albums = albums_data.get("items", [])

            while albums_data.get("next"):
                albums_data = await loop.run_in_executor(
                    None, client.next, albums_data
                )
                if albums_data:
                    all_albums.extend(albums_data.get("items", []))

            # Deduplicate albums by name
            seen_names: set[str] = set()
            unique_albums = []
            for album in all_albums:
                name = album.get("name", "").lower().strip()
                if name not in seen_names:
                    seen_names.add(name)
                    unique_albums.append(album)

            # Build list info
            list_info = {
                "name": artist.get("name", ""),
                "url": artist.get("external_urls", {}).get("spotify", ""),
            }

            # Collect all songs from albums
            songs: list[Song] = []
            for album in unique_albums:
                album_url = album.get("external_urls", {}).get("spotify", "")
                if not album_url:
                    continue

                try:
                    album_songs = await self.get_album(album_url)
                    for song in album_songs.songs:
                        # Update list context
                        song.list_name = list_info["name"]
                        song.list_url = list_info["url"]
                        songs.append(song)
                except SourceProviderError:
                    continue

            # Update list length
            for i, song in enumerate(songs):
                song.list_position = i + 1
                song.list_length = len(songs)

            return SongList(
                name=artist.get("name", ""),
                url=artist.get("external_urls", {}).get("spotify", ""),
                platform=Platform.SPOTIFY,
                urls=tuple(song.url for song in songs),
                songs=tuple(songs),
            )

        except spotipy.SpotifyException as e:
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
        client = self._get_client()
        loop = asyncio.get_event_loop()

        try:
            results = await loop.run_in_executor(
                None, lambda: client.search(query, limit=limit, type="track")
            )

            tracks = results.get("tracks", {}).get("items", [])

            songs = []
            for track in tracks:
                song = self._track_to_song(track)
                songs.append(song)

            return songs

        except spotipy.SpotifyException:
            return []
