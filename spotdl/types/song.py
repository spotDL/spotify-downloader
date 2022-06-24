"""
Song module that hold the Song and SongList classes.
"""

import json

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from spotdl.utils.spotify import SpotifyClient


class SongError(Exception):
    """
    Base class for all exceptions related to songs.
    """


@dataclass()
class Song:
    """
    Song class. Contains all the information about a song.
    """

    name: str
    artists: List[str]
    artist: str
    album_name: str
    album_artist: str
    genres: List[str]
    disc_number: int
    disc_count: int
    duration: int
    year: int
    date: str
    track_number: int
    tracks_count: int
    song_id: str
    cover_url: Optional[str]
    explicit: bool
    publisher: str
    url: str
    isrc: Optional[str]
    copyright_text: Optional[str]
    download_url: Optional[str] = None
    song_list: Optional["SongList"] = None
    lyrics: Optional[str] = None

    @classmethod
    def from_url(cls, url: str) -> "Song":
        """
        Creates a Song object from a URL.

        ### Arguments
        - url: The URL of the song.

        ### Returns
        - The Song object.
        """

        if "open.spotify.com" not in url or "track" not in url:
            raise SongError(f"Invalid URL: {url}")

        # query spotify for song, artist, album details
        spotify_client = SpotifyClient()

        # get track info
        raw_track_meta = spotify_client.track(url)

        if raw_track_meta is None:
            raise SongError(
                "Couldn't get metadata, check if you have passed correct track id"
            )

        # get artist info
        primary_artist_id = raw_track_meta["artists"][0]["id"]
        raw_artist_meta: Dict[str, Any] = spotify_client.artist(primary_artist_id)  # type: ignore

        # get album info
        album_id = raw_track_meta["album"]["id"]
        raw_album_meta: Dict[str, Any] = spotify_client.album(album_id)  # type: ignore

        # create song object
        return cls(
            name=raw_track_meta["name"],
            artists=[artist["name"] for artist in raw_track_meta["artists"]],
            artist=raw_track_meta["artists"][0]["name"],
            album_name=raw_album_meta["name"],
            album_artist=raw_album_meta["artists"][0]["name"],
            copyright_text=raw_album_meta["copyrights"][0]["text"]
            if raw_album_meta["copyrights"]
            else None,
            genres=raw_album_meta["genres"] + raw_artist_meta["genres"],
            disc_number=raw_track_meta["disc_number"],
            disc_count=int(raw_album_meta["tracks"]["items"][-1]["disc_number"]),
            duration=raw_track_meta["duration_ms"] / 1000,
            year=int(raw_album_meta["release_date"][:4]),
            date=raw_album_meta["release_date"],
            track_number=raw_track_meta["track_number"],
            tracks_count=raw_album_meta["total_tracks"],
            isrc=raw_track_meta.get("external_ids", {}).get("isrc"),
            song_id=raw_track_meta["id"],
            explicit=raw_track_meta["explicit"],
            publisher=raw_album_meta["label"],
            url=raw_track_meta["external_urls"]["spotify"],
            cover_url=raw_album_meta["images"][0]["url"]
            if raw_album_meta["images"]
            else None,
        )

    @classmethod
    def from_search_term(cls, search_term: str) -> "Song":
        """
        Creates a list of Song objects from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The Song object.
        """

        spotify_client = SpotifyClient()
        raw_search_results = spotify_client.search(search_term)

        if (
            raw_search_results is None
            or len(raw_search_results.get("tracks", {}).get("items", [])) == 0
        ):
            raise SongError("No songs matches found on spotify")

        return Song.from_url(
            "http://open.spotify.com/track/"
            + raw_search_results["tracks"]["items"][0]["id"]
        )

    @classmethod
    def from_data_dump(cls, data: str) -> "Song":
        """
        Create a Song object from a data dump.

        ### Arguments
        - data: The data dump.

        ### Returns
        - The Song object.
        """

        # Create dict from json string
        data_dict = json.loads(data)

        # Return product object
        return cls(**data_dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Song":
        """
        Create a Song object from a dictionary.

        ### Arguments
        - data: The dictionary.

        ### Returns
        - The Song object.
        """

        # Return product object
        return cls(**data)

    @property
    def display_name(self) -> str:
        """
        Returns a display name for the song.

        ### Returns
        - The display name.
        """

        return f"{self.artist} - {self.name}"

    @property
    def json(self) -> Dict[str, Any]:
        """
        Returns a dictionary of the song's data.

        ### Returns
        - The dictionary.
        """

        return asdict(self)


@dataclass(frozen=True)
class SongList:
    """
    SongList class. Base class for all other song lists subclasses.
    """

    name: str
    url: str
    urls: List[str]
    songs: List[Song]

    @property
    def length(self) -> int:
        """
        Get list length (number of songs).

        ### Returns
        - The list length.
        """

        return len(self.songs)

    @classmethod
    def create_basic_list(cls, url: str):
        """
        Create a basic list with only the required metadata and urls.

        ### Arguments
        - url: The url of the list.

        ### Returns
        - The SongList object.
        """

        metadata = cls.get_metadata(url)
        urls = cls.get_urls(url)

        return cls(**metadata, urls=urls, songs=[])

    @classmethod
    def from_url(cls, url: str) -> "SongList":
        """
        Initialize a SongList object from a URL.

        ### Arguments
        - url: The URL of the list.
        """

        raise NotImplementedError

    @staticmethod
    def get_urls(url: str) -> List[str]:
        """
        Get urls for all songs in url.

        ### Arguments
        - url: The URL of the list.

        ### Returns
        - The list of urls.
        """

        raise NotImplementedError

    @staticmethod
    def get_metadata(url: str) -> Dict[str, Any]:
        """
        Get metadata for list.

        ### Arguments
        - url: The URL of the list.

        ### Returns
        - The metadata.
        """

        raise NotImplementedError
