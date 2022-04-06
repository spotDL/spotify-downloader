"""
Artist module for retrieving artist data from Spotify.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from slugify import slugify

from spotdl.types.song import SongList
from spotdl.types.song import Song
from spotdl.types.album import Album
from spotdl.utils.spotify import SpotifyClient


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

    @classmethod
    def from_url(cls, url: str) -> "Artist":
        """
        Creates an Artist object from a URL.

        ### Arguments
        - url: The URL of the artist.

        ### Returns
        - The Artist object.
        """

        if "open.spotify.com" not in url or "artist" not in url:
            raise ArtistError(f"Invalid URL: {url}")

        metadata = Artist.get_metadata(url)
        album_urls = cls.get_albums(url)

        tracks: List[Song] = []
        albums: List[Album] = []

        # get artist tracks
        # same as above, but for tracks
        known_tracks: Set[str] = set()
        if len(album_urls) < 1:
            raise ArtistError(
                "Couldn't get albums, check if you have passed correct artist id"
            )

        # get all tracks from all albums
        # ignore duplicates
        urls = []
        for album_url in album_urls:
            album = Album.from_url(album_url)
            albums.append(album)
            for track in album.songs:
                track_name = slugify(track.name)  # type: ignore
                if track_name not in known_tracks:
                    tracks.append(track)
                    urls.append(track.url)
                    known_tracks.add(track_name)

        return cls(
            **metadata,
            songs=tracks,
            albums=albums,
            urls=urls,
        )

    @staticmethod
    def get_urls(url: str) -> List[str]:
        """
        Get urls for all songs for artist.

        ### Arguments
        - url: The URL of the artist.

        ### Returns
        - List of urls for all songs for artist.
        """

        albums = Artist.get_albums(url)

        urls = []
        for album in albums:
            urls.extend(Album.get_urls(album))

        return urls

    @classmethod
    def create_basic_list(cls, url: str) -> "Artist":
        """
        Create a basic list with only the required metadata and urls.

        ### Arguments
        - url: The url of the list.

        ### Returns
        - The SongList object.
        """

        metadata = Artist.get_metadata(url)
        urls = Artist.get_urls(url)

        return cls(**metadata, urls=urls, songs=[], albums=[])

    @staticmethod
    def get_albums(url: str) -> List[str]:
        """
        Returns a list with album urls.

        ### Arguments
        - url: The URL of the artist.

        ### Returns
        - List of album urls.
        """

        # query spotify for artist details
        spotify_client = SpotifyClient()

        artist_albums = spotify_client.artist_albums(url, album_type="album,single")

        albums: List[str] = []

        # get artist albums and remove duplicates
        # duplicates can occur if the artist has the same album available in
        # different countries
        known_albums: Set[str] = set()
        if artist_albums is not None:
            for album in artist_albums["items"]:
                albums.append(album["external_urls"]["spotify"])
                known_albums.add(slugify(album["name"]))  # type: ignore

            # Fetch all artist albums
            while artist_albums and artist_albums["next"]:
                artist_albums = spotify_client.next(artist_albums)
                if artist_albums is None:
                    break

                for album in artist_albums["items"]:
                    album_name = slugify(album["name"])  # type: ignore

                    if album_name in known_albums:
                        albums.extend([item["uri"] for item in artist_albums["items"]])

                        known_albums.add(album_name)

        return albums

    @staticmethod
    def get_metadata(url: str) -> Dict[str, Any]:
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

        return {
            "name": raw_artist_meta["name"],
            "genres": raw_artist_meta["genres"],
            "url": url,
        }
