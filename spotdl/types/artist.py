"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from spotdl.types.album import Album
from spotdl.types.song import Song, SongList
from spotdl.utils.formatter import slugify
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

        artist_albums = spotify_client.artist_albums(url, album_type="album,single")
        # check if there is response
        if not artist_albums:
            raise ArtistError(
                "Couldn't get albums, check if you have passed correct artist id"
            )

        # get artist albums and remove duplicates
        # duplicates can occur if the artist has the same album available in
        # different countries
        albums: List[str] = []
        known_albums: Set[str] = set()
        for album in artist_albums["items"]:
            albums.append(album["external_urls"]["spotify"])
            known_albums.add(slugify(album["name"]))

        # Fetch all artist albums
        while artist_albums and artist_albums["next"]:
            artist_albums = spotify_client.next(artist_albums)
            if artist_albums is None:
                break

            for album in artist_albums["items"]:
                album_name = slugify(album["name"])

                if album_name not in known_albums:
                    albums.append(album["external_urls"]["spotify"])
                    known_albums.add(album_name)

        songs = []
        for album in albums:
            album_obj = Album.from_url(album, fetch_songs=False)
            songs.extend(album_obj.songs)

        # Very aggressive deduplication
        songs_list = []
        songs_names = set()
        for song in songs:
            slug_name = slugify(song.name)
            if song.name not in songs_names:
                songs_list.append(song)
                songs_names.add(slug_name)

        metadata = {
            "name": raw_artist_meta["name"],
            "genres": raw_artist_meta["genres"],
            "url": url,
            "albums": albums,
        }

        return metadata, songs_list
