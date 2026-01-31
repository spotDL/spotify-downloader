"""
Song module that hold the Song and SongList classes.
"""

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from spotdl.utils.spotify import SpotifyClient

__all__ = ["Song", "SongList", "SongError"]


class SongError(Exception):
    """
    Base class for all exceptions related to songs.
    """


class SongListError(Exception):
    """
    Base class for all exceptions related to song lists.
    """


@dataclass
class Song:
    """
    Song class. Contains all the information about a song.
    """

    name: str
    artists: List[str]
    artist: str
    genres: List[str]
    disc_number: int
    disc_count: int
    album_name: str
    album_artist: str
    duration: int
    year: int
    date: str
    track_number: int
    tracks_count: int
    song_id: str
    explicit: bool
    publisher: str
    url: str
    isrc: Optional[str]
    cover_url: Optional[str]
    copyright_text: Optional[str]
    download_url: Optional[str] = None
    lyrics: Optional[str] = None
    popularity: Optional[int] = None
    album_id: Optional[str] = None
    list_name: Optional[str] = None
    list_url: Optional[str] = None
    list_position: Optional[int] = None
    list_length: Optional[int] = None
    artist_id: Optional[str] = None
    album_type: Optional[str] = None

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

        if raw_track_meta["duration_ms"] == 0 or raw_track_meta["name"].strip() == "":
            raise SongError(f"Track no longer exists: {url}")

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
            artist_id=primary_artist_id,
            album_id=album_id,
            album_name=raw_album_meta["name"],
            album_artist=raw_album_meta["artists"][0]["name"],
            album_type=raw_album_meta.get("album_type"),
            copyright_text=(
                raw_album_meta["copyrights"][0]["text"]
                if raw_album_meta["copyrights"]
                else None
            ),
            genres=raw_album_meta["genres"] + raw_artist_meta["genres"],
            disc_number=raw_track_meta["disc_number"],
            disc_count=int(raw_album_meta["tracks"]["items"][-1]["disc_number"]),
            duration=int(raw_track_meta["duration_ms"] / 1000),
            year=int(raw_album_meta["release_date"][:4]),
            date=raw_album_meta["release_date"],
            track_number=raw_track_meta["track_number"],
            tracks_count=raw_album_meta["total_tracks"],
            isrc=raw_track_meta.get("external_ids", {}).get("isrc"),
            song_id=raw_track_meta["id"],
            explicit=raw_track_meta["explicit"],
            publisher=raw_album_meta["label"],
            url=raw_track_meta["external_urls"]["spotify"],
            popularity=raw_track_meta["popularity"],
            cover_url=(
                max(raw_album_meta["images"], key=lambda i: i["width"] * i["height"])[
                    "url"
                ]
                if raw_album_meta["images"]
                else None
            ),
        )

    @staticmethod
    def search(search_term: str):
        """
        Searches for Songs from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The raw search results
        """
        spotify_client = SpotifyClient()
        raw_search_results = spotify_client.search(search_term)

        if raw_search_results is None:
            raise SongError(f"Spotipy error, no response: {search_term}")

        return raw_search_results

    @classmethod
    def from_search_term(cls, search_term: str) -> "Song":
        """
        Creates a list of Song objects from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The Song object.
        """

        raw_search_results = Song.search(search_term)

        if len(raw_search_results["tracks"]["items"]) == 0:
            raise SongError(f"No results found for: {search_term}")

        return Song.from_url(
            "http://open.spotify.com/track/"
            + raw_search_results["tracks"]["items"][0]["id"]
        )

    @classmethod
    def list_from_search_term(cls, search_term: str) -> "List[Song]":
        """
        Creates a list of Song objects from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The list of Song objects.
        """

        raw_search_results = Song.search(search_term)

        songs = []
        for idx, _ in enumerate(raw_search_results.get("tracks", []).get("items", [])):
            songs.append(
                Song.from_url(
                    "http://open.spotify.com/track/"
                    + raw_search_results["tracks"]["items"][idx]["id"]
                )
            )

        return songs

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

    @classmethod
    def from_missing_data(cls, **kwargs) -> "Song":
        """
        Create a Song object from a dictionary with missing data.
        For example, data dict doesn't contain all the required
        attributes for the Song class.

        ### Arguments
        - data: The dictionary.

        ### Returns
        - The Song object.
        """

        song_data: Dict[str, Any] = {}
        for key in cls.__dataclass_fields__:  # pylint: disable=E1101
            song_data.setdefault(key, kwargs.get(key))

        return cls(**song_data)

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

    @classmethod
    def from_url(cls, url: str, fetch_songs: bool = True):
        """
        Create a SongList object from a url.

        ### Arguments
        - url: The url of the list.
        - fetch_songs: Whether to fetch missing metadata for songs.

        ### Returns
        - The SongList object.
        """

        metadata, songs = cls.get_metadata(url)
        urls = [song.url for song in songs]

        if fetch_songs:
            songs = [Song.from_url(song.url) for song in songs]

        return cls(**metadata, urls=urls, songs=songs)

    @classmethod
    def from_search_term(cls, search_term: str, fetch_songs: bool = True):
        """
        Creates a SongList object from a search term.

        ### Arguments
        - search_term: The search term to use.

        ### Returns
        - The SongList object.
        """

        list_type = cls.__name__.lower()
        spotify_client = SpotifyClient()
        raw_search_results = spotify_client.search(search_term, type=list_type)

        if (
            raw_search_results is None
            or len(raw_search_results.get(f"{list_type}s", {}).get("items", [])) == 0
        ):
            raise SongListError(
                f"No {list_type} matches found on spotify for '{search_term}'"
            )

        matches = {}
        for result in raw_search_results[f"{list_type}s"]["items"]:
            score = fuzz.ratio(search_term.split(":", 1)[1].strip(), result["name"])
            matches[result["id"]] = score

        best_match = max(matches, key=matches.get)  # type: ignore

        return cls.from_url(
            f"http://open.spotify.com/{list_type}/{best_match}",
            fetch_songs,
        )

    @property
    def length(self) -> int:
        """
        Get list length (number of songs).

        ### Returns
        - The list length.
        """

        return max(len(self.urls), len(self.songs))

    @property
    def json(self) -> Dict[str, Any]:
        """
        Returns a dictionary of the song list's data.

        ### Returns
        - The dictionary.
        """

        return asdict(self)

    @staticmethod
    def get_metadata(url: str) -> Tuple[Dict[str, Any], List[Song]]:
        """
        Get metadata for a song list.

        ### Arguments
        - url: The url of the song list.

        ### Returns
        - The metadata.
        """

        raise NotImplementedError
