"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from spotdl.types.album import Album
from spotdl.types.song import Song, SongList
from spotdl.utils.spotify import SpotifyClient

__all__ = ["Artist", "ArtistError"]


class ArtistError(Exception):
    """
    Base class for all exceptions related to artists.
    """


@dataclass(frozen=True)
class Artist(SongList):
    """
    Artist class.
    Contains all the information about an artist.
    Frozen to prevent accidental modification.
    """

    genres: List[str]
    albums: List[Album]

    @staticmethod
    def get_metadata(url: str) -> Tuple[Dict[str, Any], List[Song]]:
        """
        Get metadata for artist.

        ### Arguments
        - url: The URL of the artist.

        ### Returns
        - Dict with metadata for artist.
        """

        # query spotify for artist details
        spotify_client = SpotifyClient()

        # get artist info
        raw_artist_meta = spotify_client.artist(url)

        if raw_artist_meta is None:
            raise ArtistError(
                "Couldn't get metadata, check if you have passed correct artist id"
            )

        # include_groups used to be called album_type
        artist_albums = spotify_client.artist_albums(
            url, include_groups="album,single,compilation"
        )
        # check if there is response
        if not artist_albums:
            raise ArtistError(
                "Couldn't get albums, check if you have passed correct artist id"
            )

        releases: Dict[str, Dict[str, Any]] = {}
        while artist_albums:
            for album in artist_albums["items"]:
                album_url = album["external_urls"]["spotify"]
                releases.setdefault(album_url, album)

            if not artist_albums.get("next"):
                break
            artist_albums = spotify_client.next(artist_albums)
            if artist_albums is None:
                raise ArtistError(f"Failed to get artist releases: {url}")

        songs: Dict[str, Song] = {}
        for album_url, release in releases.items():
            # SpotipyFree returns full albums here. Spotipy returns summaries.
            _, tracks = Album.get_metadata(
                album_url, release if "tracks" in release else None
            )
            for song in tracks:
                songs.setdefault(song.song_id, song)

        metadata = {
            "name": raw_artist_meta["name"],
            "genres": raw_artist_meta["genres"],
            "url": url,
            "albums": list(releases),
        }

        return metadata, list(songs.values())
