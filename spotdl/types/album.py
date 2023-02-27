"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from spotdl.types.song import Song, SongList
from spotdl.utils.spotify import SpotifyClient

__all__ = ["Album", "AlbumError"]


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

    @staticmethod
    def get_metadata(url: str) -> Tuple[Dict[str, Any], List[Song]]:
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

        metadata = {
            "name": album_metadata["name"],
            "artist": album_metadata["artists"][0],
            "url": url,
        }

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

        songs = []
        for track in tracks:
            if not isinstance(track, dict) or track.get("is_local"):
                continue

            release_date = album_metadata["release_date"]
            artists = artists = [artist["name"] for artist in track["artists"]]

            song = Song.from_missing_data(
                name=track["name"],
                artists=artists,
                artist=artists[0],
                album_id=album_metadata["id"],
                album_name=album_metadata["name"],
                album_artist=album_metadata["artists"][0]["name"],
                disc_number=track["disc_number"],
                disc_count=int(album_metadata["tracks"]["items"][-1]["disc_number"]),
                duration=track["duration_ms"],
                year=release_date[:4],
                date=release_date,
                track_number=track["track_number"],
                tracks_count=album_metadata["total_tracks"],
                song_id=track["id"],
                explicit=track["explicit"],
                publisher=album_metadata["label"],
                url=track["external_urls"]["spotify"],
                cover_url=max(
                    album_metadata["images"], key=lambda i: i["width"] * i["height"]
                )["url"]
                if album_metadata["images"]
                else None,
                copyright_text=album_metadata["copyrights"][0]["text"]
                if album_metadata["copyrights"]
                else None,
            )

            songs.append(song)

        return metadata, songs
