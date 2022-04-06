"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
from spotdl.types.song import SongList
from spotdl.utils.spotify import SpotifyClient
from spotdl.types.song import Song


class AlbumError(Exception):
    """
    Base class for all exceptions related to albums.
    """


@dataclass(frozen=True)
class Album(SongList):
    """
    Album class for retrieving album data from Spotify.
    """

    artist: Dict[str, Any]

    @classmethod
    def from_url(cls, url: str) -> "Album":
        """
        Parse an album from a Spotify URL.

        ### Arguments
        - url: The URL of the album.

        ### Returns
        - The Album object.
        """

        metadata = Album.get_metadata(url)

        urls = cls.get_urls(url)

        # Remove songs without id (country restricted/local tracks)
        # And create song object for each track
        songs: List[Song] = [Song.from_url(url) for url in urls]

        return cls(
            **metadata,
            songs=songs,
            urls=urls,
        )

    @staticmethod
    def get_urls(url: str) -> List[str]:
        """
        Get urls for all songs in album.

        ### Arguments
        - url: The URL of the album.

        ### Returns
        - A list of urls.
        """

        spotify_client = SpotifyClient()

        album_response = spotify_client.album_tracks(url)
        if album_response is None:
            raise AlbumError(
                "Couldn't get metadata, check if you have passed correct album id"
            )

        tracks = album_response["items"]

        # Get all tracks from album
        while album_response["next"]:
            album_response = spotify_client.next(album_response)

            # Failed to get response, break the loop
            if album_response is None:
                break

            tracks.extend(album_response["items"])

        if album_response is None:
            raise AlbumError(f"Failed to get album response: {url}")

        return [
            track["external_urls"]["spotify"]
            for track in tracks
            if track and track.get("id")
        ]

    @staticmethod
    def get_metadata(url: str) -> Dict[str, Any]:
        """
        Get metadata for album.

        ### Arguments
        - url: The URL of the album.

        ### Returns
        - A dictionary with metadata.
        """

        spotify_client = SpotifyClient()

        album_metadata = spotify_client.album(url)
        if album_metadata is None:
            raise AlbumError(
                "Couldn't get metadata, check if you have passed correct album id"
            )

        return {
            "name": album_metadata["name"],
            "artist": album_metadata["artists"][0],
            "url": url,
        }
