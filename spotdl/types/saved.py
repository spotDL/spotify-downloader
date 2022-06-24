"""
Saved module for handing the saved tracks from user library
"""

from dataclasses import dataclass
from typing import Any, Dict, List
from spotdl.types.song import SongList
from spotdl.types.song import Song
from spotdl.utils.spotify import SpotifyClient


class SavedError(Exception):
    """
    Base class for all exceptions related to saved tracks.
    """


@dataclass(frozen=True)
class Saved(SongList):
    """
    Saved class for handling the saved tracks from user library.
    """

    @classmethod
    def from_url(cls, url: str = "saved") -> "Saved":
        """
        Loads saved tracks from Spotify.
        Will throw an exception if users is not logged in.
        """

        metadata = Saved.get_metadata(url)

        urls = cls.get_urls(url)

        # Remove songs without id
        # and create Song objects
        tracks = [Song.from_url(url) for url in urls]

        return cls(
            **metadata,
            songs=tracks,
            urls=urls,
        )

    @staticmethod
    def get_urls(_: str = "saved") -> List[str]:
        """
        Returns a list of urls of all saved tracks.

        ### Arguments
        - _: not required, but used to match the signature of the other get_urls methods.

        ### Returns
        - A list of urls.
        """

        spotify_client = SpotifyClient()
        if spotify_client.user_auth is False:  # type: ignore
            raise SavedError("You must be logged in to use this function.")

        saved_tracks_response = spotify_client.current_user_saved_tracks()
        if saved_tracks_response is None:
            raise Exception("Couldn't get saved tracks")

        saved_tracks = saved_tracks_response["items"]

        # Fetch all saved tracks
        while saved_tracks_response and saved_tracks_response["next"]:
            response = spotify_client.next(saved_tracks_response)
            # response is wrong, break
            if response is None:
                break

            saved_tracks_response = response
            saved_tracks.extend(saved_tracks_response["items"])

        # Remove songs without id
        # and return urls
        return [
            "https://open.spotify.com/track/" + track["track"]["id"]
            for track in saved_tracks
            if track and track.get("track", {}).get("id")
        ]

    @classmethod
    def create_basic_list(cls, url: str = "saved") -> "Saved":
        """
        Create a basic list with only the required metadata and urls.

        ### Returns
        - The Saved object.
        """

        metadata = cls.get_metadata(url)
        urls = cls.get_urls(url)

        return cls(**metadata, urls=urls, songs=[])

    @staticmethod
    def get_metadata(url: str = "saved") -> Dict[str, Any]:
        """
        Returns metadata for a saved list.

        ### Arguments
        - url: Not required, but used to match the signature of the other get_metadata methods.
        """

        return {"name": "Saved tracks", "url": url}
