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
    Frozen to prevent accidental modification.
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
    isrc: str
    song_id: str
    cover_url: str
    explicit: bool
    publisher: str
    url: str
    copyright: Optional[str]
    download_url: Optional[str] = None

    @classmethod
    def from_url(cls, url: str) -> "Song":
        """
        Creates a Song object from a URL.
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
            copyright=raw_album_meta["copyrights"][0]["text"]
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
            isrc=raw_track_meta["external_ids"]["isrc"],
            song_id=raw_track_meta["id"],
            explicit=raw_track_meta["explicit"],
            publisher=raw_album_meta["label"],
            url=raw_track_meta["external_urls"]["spotify"],
            cover_url=raw_album_meta["images"][0]["url"],
        )

    @classmethod
    def from_search_term(cls, search_term: str) -> "Song":
        """
        Creates a list of Song objects from a search term.
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
        """

        # Create dict from json string
        data_dict = json.loads(data)

        # Return product object
        return cls(**data_dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Song":
        """
        Create a Song object from a dictionary.
        """

        # Return product object
        return cls(**data)

    @property
    def display_name(self) -> str:
        """
        Returns a display name for the song.
        """

        return f"{self.name} - {self.artist}"

    @property
    def json(self) -> Dict[str, Any]:
        """
        Returns a dictionary of the song's data.
        """

        return asdict(self)
