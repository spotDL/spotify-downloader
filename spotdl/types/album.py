"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    def get_metadata(
        url: str, album_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Song]]:
        """
        Get metadata for album.

        ### Arguments
        - url: The URL of the album.
        - album_metadata: Full release data from the artist's discography, if available.

        ### Returns
        - A dictionary with metadata.
        """

        spotify_client = SpotifyClient()

        if album_metadata is None:
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

        # SpotipyFree reports total_tracks as the size of its first page.
        total = album_metadata.get("tracksV2", {}).get(
            "totalCount", album_metadata["total_tracks"]
        )
        album_response = album_metadata.get("tracks") or {}
        if "items" not in album_response or (
            not album_response.get("next") and len(album_response["items"]) != total
        ):
            album_response = spotify_client.album_tracks(url)
        if album_response is None:
            raise AlbumError(
                "Couldn't get metadata, check if you have passed correct album id"
            )

        tracks = list(album_response["items"])

        while album_response.get("next"):
            album_response = spotify_client.next(album_response)

            if album_response is None:
                raise AlbumError(f"Failed to get album response: {url}")

            tracks.extend(album_response["items"])

        tracks = [t for t in tracks if isinstance(t, dict) and not t.get("is_local")]
        disc_count = max((int(t["disc_number"]) for t in tracks), default=1)
        release_date = album_metadata["release_date"]
        images = album_metadata["images"]
        cover = (
            max(images, key=lambda image: image["width"] * image["height"])["url"]
            if images
            else None
        )
        songs = []
        for track in tracks:
            artists = [artist["name"] for artist in track["artists"]]

            song = Song.from_missing_data(
                name=track["name"],
                artists=artists,
                artist=artists[0],
                album_id=album_metadata["id"],
                album_name=album_metadata["name"],
                album_artist=album_metadata["artists"][0]["name"],
                album_type=album_metadata["album_type"],
                disc_number=track["disc_number"],
                disc_count=disc_count,
                duration=int(track["duration_ms"] / 1000),
                year=release_date[:4],
                date=release_date,
                track_number=track["track_number"],
                tracks_count=total,
                song_id=track["id"],
                explicit=track["explicit"],
                publisher=album_metadata["label"],
                url=track["external_urls"]["spotify"],
                cover_url=cover,
                copyright_text=(
                    album_metadata["copyrights"][0]["text"]
                    if album_metadata["copyrights"]
                    else None
                ),
            )

            songs.append(song)

        return metadata, songs
