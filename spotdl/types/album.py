"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from spotdl.types.song import SongList
from spotdl.utils.spotify import SpotifyClient


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
    def search(cls, search_term: str):
        """
        Searches for Album from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The raw search results
        """

        spotify_client = SpotifyClient()
        raw_search_results = spotify_client.search(search_term, type="album")

        if (
            raw_search_results is None
            or len(raw_search_results.get("albums", {}).get("items", [])) == 0
        ):
            raise AlbumError("No album matches found on spotify")

        return raw_search_results

    @classmethod
    def from_search_term(cls, search_term: str) -> "Album":
        """
        Creates an Album object from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The Album object.
        """

        raw_search_results = Album.search(search_term)

        return Album.create_basic_list(
            "http://open.spotify.com/album/"
            + raw_search_results["albums"]["items"][0]["id"]
        )

    @classmethod
    def list_from_search_term(cls, search_term: str) -> "List[Album]":
        """
        Creates a list of Album objects from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The list of Album objects.
        """

        raw_search_results = Album.search(search_term)

        albums = []
        for idx, _ in enumerate(raw_search_results["albums"]["items"]):
            albums.append(
                Album.create_basic_object(
                    "http://open.spotify.com/album/"
                    + raw_search_results["albums"]["items"][idx]["id"]
                )
            )

        return albums

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
