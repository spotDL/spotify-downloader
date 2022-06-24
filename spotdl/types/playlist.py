"""
Playlist module for retrieving playlist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from spotdl.types.song import SongList
from spotdl.utils.spotify import SpotifyClient
from spotdl.types.song import Song


class PlaylistError(Exception):
    """
    Base class for all exceptions related to playlists.
    """


@dataclass(frozen=True)
class Playlist(SongList):
    """
    Playlist class for retrieving playlist data from Spotify.
    """

    description: str
    author_url: str
    author_name: str

    @classmethod
    def from_url(cls, url: str) -> "Playlist":
        """
        Load playlist info and tracks from a Spotify playlist URL.

        ### Arguments
        - url: The URL of the playlist.

        ### Returns
        - The Playlist object.
        """

        metadata = Playlist.get_metadata(url)

        # Get urls
        urls = cls.get_urls(url)

        # Remove songs without id (country restricted/local tracks)
        # And create song object for each track
        tracks = [Song.from_url(url) for url in urls]

        return cls(
            **metadata,
            songs=tracks,
            urls=urls,
        )

    @staticmethod
    def get_urls(url: str) -> List[str]:
        """
        Get URLs of all tracks in a playlist.

        ### Arguments
        - url: The URL of the playlist.

        ### Returns
        - A list of urls.
        """

        spotify_client = SpotifyClient()
        tracks = []

        playlist_response = spotify_client.playlist_items(url)
        if playlist_response is None:
            raise PlaylistError(f"Wrong playlist id: {url}")

        tracks = playlist_response["items"]

        # Get all tracks from playlist
        while playlist_response["next"]:
            playlist_response = spotify_client.next(playlist_response)

            # Failed to get response, break the loop
            if playlist_response is None:
                break

            # Add tracks to the list
            tracks.extend(playlist_response["items"])

        return [
            track["track"]["external_urls"]["spotify"]
            for track in tracks
            if track is not None
            and track.get("track") is not None
            and track.get("track").get("id")
        ]

    @staticmethod
    def get_metadata(url: str) -> Dict[str, Any]:
        """
        Get metadata for a playlist.

        ### Arguments
        - url: The URL of the playlist.

        ### Returns
        - A dictionary with metadata.
        """

        spotify_client = SpotifyClient()

        playlist = spotify_client.playlist(url)
        if playlist is None:
            raise PlaylistError("Invalid playlist URL.")

        return {
            "name": playlist["name"],
            "url": url,
            "description": playlist["description"],
            "author_url": playlist["external_urls"]["spotify"],
            "author_name": playlist["owner"]["display_name"],
        }
