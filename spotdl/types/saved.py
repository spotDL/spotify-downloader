"""
Saved module for handing the saved tracks from user library
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from spotdl.types.song import Song, SongList
from spotdl.utils.spotify import SpotifyClient

__all__ = ["Saved", "SavedError"]


class SavedError(Exception):
    """
    Base class for all exceptions related to saved tracks.
    """


@dataclass(frozen=True)
class Saved(SongList):
    """
    Saved class for handling the saved tracks from user library.
    """

    @staticmethod
    def get_metadata(url: str = "saved") -> Tuple[Dict[str, Any], List[Song]]:
        """
        Returns metadata for a saved list.

        ### Arguments
        - url: Not required, but used to match the signature of the other get_metadata methods.

        ### Returns
        - metadata: A dictionary containing the metadata for the saved list.
        - songs: A list of Song objects.
        """

        metadata = {"name": "Saved tracks", "url": url}

        spotify_client = SpotifyClient()
        if spotify_client.user_auth is False:  # type: ignore
            raise SavedError("You must be logged in to use this function")

        saved_tracks_response = spotify_client.current_user_saved_tracks()
        if saved_tracks_response is None:
            raise SavedError("Couldn't get saved tracks")

        saved_tracks = saved_tracks_response["items"]

        # Fetch all saved tracks
        while saved_tracks_response and saved_tracks_response["next"]:
            response = spotify_client.next(saved_tracks_response)
            if response is None:
                break

            saved_tracks_response = response
            saved_tracks.extend(saved_tracks_response["items"])

        songs = []
        for track in saved_tracks:
            if not isinstance(track, dict) or track.get("track", {}).get("is_local"):
                continue

            track_meta = track["track"]
            album_meta = track_meta["album"]

            release_date = album_meta["release_date"]
            artists = artists = [artist["name"] for artist in track_meta["artists"]]

            song = Song.from_missing_data(
                name=track_meta["name"],
                artists=artists,
                artist=artists[0],
                album_id=album_meta["id"],
                album_name=album_meta["name"],
                album_artist=album_meta["artists"][0]["name"],
                album_type=album_meta["album_type"],
                disc_number=track_meta["disc_number"],
                duration=int(track_meta["duration_ms"] / 1000),
                year=release_date[:4],
                date=release_date,
                track_number=track_meta["track_number"],
                tracks_count=album_meta["total_tracks"],
                song_id=track_meta["id"],
                explicit=track_meta["explicit"],
                url=track_meta["external_urls"]["spotify"],
                isrc=track_meta.get("external_ids", {}).get("isrc"),
                cover_url=(
                    max(album_meta["images"], key=lambda i: i["width"] * i["height"])[
                        "url"
                    ]
                    if album_meta["images"]
                    else None
                ),
            )

            songs.append(song)

        return metadata, songs
