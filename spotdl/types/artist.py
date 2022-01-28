from dataclasses import dataclass
from typing import List, Set
from slugify import slugify
from spotdl.types.song import Song
from spotdl.types.album import Album
from spotdl.utils.spotify import SpotifyClient


class ArtistError(Exception):
    """
    Base class for all exceptions related to artists.
    """


@dataclass(frozen=True)
class Artist:
    """
    Artist class.
    Contains all the information about an artist.
    Frozen to prevent accidental modification.
    """

    name: str
    artist_id: str
    genres: List[str]
    tracks: List[Song]
    albums: List[Album]

    @classmethod
    def from_url(cls, url: str) -> "Artist":
        """
        Creates an Artist object from a URL.
        """

        if "open.spotify.com" not in url or "artist" not in url:
            raise ArtistError(f"Invalid URL: {url}")

        # query spotify for artist details
        spotify_client = SpotifyClient()

        # get artist info
        raw_artist_meta = spotify_client.artist(url)

        if raw_artist_meta is None:
            raise ArtistError(
                "Couldn't get metadata, check if you have passed correct artist id"
            )

        urls = cls.get_albums(url)

        tracks: List[Song] = []
        albums: List[Album] = []

        # get artist tracks
        # same as above, but for tracks
        known_tracks: Set[str] = set()
        if len(urls) < 1:
            raise ArtistError(
                "Couldn't get albums, check if you have passed correct artist id"
            )

        # get all tracks from all albums
        # ignore duplicates
        for album_url in urls:
            album = Album.from_url(album_url)
            albums.append(album)
            for track in album.tracks:
                track_name = slugify(track.name, to_lower=True)  # type: ignore
                if track_name not in known_tracks:
                    tracks.append(track)
                    known_tracks.add(track_name)

        return cls(
            name=raw_artist_meta["name"],
            artist_id=raw_artist_meta["id"],
            genres=raw_artist_meta["genres"],
            tracks=tracks,
            albums=albums,
        )

    @staticmethod
    def get_albums(url: str) -> List[str]:
        """
        Returns a list with album urls.
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
                known_albums.add(slugify(album["name"], to_lower=True))  # type: ignore

            # Fetch all artist albums
            while artist_albums and artist_albums["next"]:
                artist_albums = spotify_client.next(artist_albums)
                if artist_albums is None:
                    break

                for album in artist_albums["items"]:
                    album_name = slugify(album["name"], to_lower=True)  # type: ignore

                    if album_name in known_albums:
                        albums.extend([item["uri"] for item in artist_albums["items"]])

                        known_albums.add(album_name)

        return albums
