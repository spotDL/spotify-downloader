"""
Module for creating Song objects by interacting with Spotify API
or by parsing a query.

To use this module you must first initialize the SpotifyClient.
"""

import json
import concurrent.futures

from typing import List, Optional

from spotdl.utils.spotify import SpotifyClient
from spotdl.types import Playlist, Album, Artist, Saved
from spotdl.types.song import SongList, SongError, Song


class QueryError(Exception):
    """
    Base class for all exceptions related to query.
    """


def get_search_results(search_term: str) -> List[Song]:
    """
    Creates a list of Song objects from a search term.

    ### Arguments
    - search_term: the search term to use

    ### Returns
    - a list of Song objects
    """

    spotify_client = SpotifyClient()
    raw_search_results = spotify_client.search(search_term)

    if (
        raw_search_results is None
        or len(raw_search_results.get("tracks", {}).get("items", [])) == 0
    ):
        raise SongError("No songs matches found on spotify")

    songs = []
    for index, _ in enumerate(raw_search_results["tracks"]["items"]):
        songs.append(
            Song.from_url(
                "http://open.spotify.com/track/"
                + raw_search_results["tracks"]["items"][index]["id"]
            )
        )

    return songs


def parse_query(
    query: List[str],
    threads: int = 1,
) -> List[Song]:
    """
    Parse query and return list containing song object

    ### Arguments
    - query: List of strings containing query
    - threads: Number of threads to use

    ### Returns
    - List of song objects
    """

    urls: List[str] = []
    songs: List[Song] = []
    for request in query:
        if (
            "youtube.com/watch?v=" in request
            or "youtu.be/" in request
            and "open.spotify.com" in request
            and "track" in request
            and "|" in request
        ):
            split_urls = request.split("|")
            if (
                len(split_urls) <= 1
                or "youtube" not in split_urls[0]
                and "youtu.be" not in split_urls[0]
                or "spotify" not in split_urls[1]
            ):
                raise QueryError(
                    "Incorrect format used, please use YouTubeURL|SpotifyURL"
                )

            songs.append(
                Song.from_dict(
                    {
                        **Song.from_url(split_urls[1]).json,
                        "download_url": split_urls[0],
                    }
                )
            )
        elif "open.spotify.com" in request and "track" in request:
            urls.append(request)
        elif "open.spotify.com" in request and "playlist" in request:
            urls.extend(Playlist.get_urls(request))
        elif "open.spotify.com" in request and "album" in request:
            urls.extend(Album.get_urls(request))
        elif "open.spotify.com" in request and "artist" in request:
            for album_url in Artist.get_albums(request):
                urls.extend(Album.get_urls(album_url))
        elif request == "saved":
            urls.extend(Saved.get_urls("saved"))
        elif request.endswith(".spotdl"):
            with open(request, "r", encoding="utf-8") as m3u_file:
                for track in json.load(m3u_file):
                    # Append to songs
                    songs.append(Song.from_dict(track))
        else:
            songs.append(Song.from_search_term(request))

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        for song in executor.map(Song.from_url, urls):
            songs.append(song)

    return songs


def create_empty_song(
    name: Optional[str] = None,
    artists: Optional[List[str]] = None,
    album_name: Optional[str] = None,
    album_artist: Optional[str] = None,
    genres: Optional[List[str]] = None,
    disc_number: Optional[int] = None,
    disc_count: Optional[int] = None,
    duration: Optional[int] = None,
    year: Optional[int] = None,
    date: Optional[str] = None,
    track_number: Optional[int] = None,
    tracks_count: Optional[int] = None,
    isrc: Optional[str] = None,
    song_id: Optional[str] = None,
    cover_url: Optional[str] = None,
    explicit: Optional[bool] = None,
    publisher: Optional[str] = None,
    url: Optional[str] = None,
    copyright_text: Optional[str] = None,
    download_url: Optional[str] = None,
    song_list: Optional["SongList"] = None,
) -> Song:
    """
    Create an empty song.

    ### Arguments
    - name: Name of the song
    - artists: List of artists
    - album_name: Name of the album
    - album_artist: Name of the album artist
    - genres: List of genres
    - disc_number: Disc number
    - disc_count: Disc count
    - duration: Duration of the song in seconds
    - year: Year of release
    - date: Date of release
    - track_number: Track number
    - tracks_count: Number of tracks
    - isrc: ISRC code
    - song_id: Spotify song ID
    - cover_url: URL of the cover art
    - explicit: Explicit flag
    - publisher: Publisher
    - url: URL of the song
    - copyright_text: Copyright text
    - download_url: Download URL
    - song_list: Song list

    ### Returns
    - Song object
    """

    return Song(
        name=name,  # type: ignore
        artists=artists,  # type: ignore
        artist=None if artists is None else artists[0],  # type: ignore
        album_name=album_name,  # type: ignore
        album_artist=album_artist,  # type: ignore
        genres=genres,  # type: ignore
        disc_number=disc_number,  # type: ignore
        disc_count=disc_count,  # type: ignore
        duration=duration,  # type: ignore
        year=year,  # type: ignore
        date=date,  # type: ignore
        track_number=track_number,  # type: ignore
        tracks_count=tracks_count,  # type: ignore
        isrc=isrc,  # type: ignore
        song_id=song_id,  # type: ignore
        cover_url=cover_url,  # type: ignore
        explicit=explicit,  # type: ignore
        publisher=publisher,  # type: ignore
        url=url,  # type: ignore
        copyright_text=copyright_text,
        download_url=download_url,
        song_list=song_list,
    )


def get_simple_songs(
    query: List[str],
) -> List[Song]:
    """
    Parse query and return list containing simple song objects

    ### Arguments
    - query: List of strings containing query

    ### Returns
    - List of simple song objects
    """

    songs: List[Song] = []
    lists: List[SongList] = []
    for request in query:
        if (
            "youtube.com/watch?v=" in request
            or "youtu.be/" in request
            and "open.spotify.com" in request
            and "track" in request
            and "|" in request
        ):
            split_urls = request.split("|")
            if (
                len(split_urls) <= 1
                or "youtube" not in split_urls[0]
                and "youtu.be" not in split_urls[0]
                or "spotify" not in split_urls[1]
            ):
                raise QueryError(
                    'Incorrect format used, please use "YouTubeURL|SpotifyURL"'
                )

            songs.append(
                create_empty_song(url=split_urls[1], download_url=split_urls[0])
            )
        elif "open.spotify.com" in request and "track" in request:
            songs.append(create_empty_song(url=request))  # type: ignore
        elif "open.spotify.com" in request and "playlist" in request:
            lists.append(Playlist.create_basic_list(request))
        elif "open.spotify.com" in request and "album" in request:
            lists.append(Album.create_basic_list(request))
        elif "open.spotify.com" in request and "artist" in request:
            lists.append(Artist.create_basic_list(request))
        elif request == "saved":
            lists.append(Saved.create_basic_list())
        elif request.endswith(".spotdl"):
            with open(request, "r", encoding="utf-8") as save_file:
                for track in json.load(save_file):
                    # Append to songs
                    songs.append(Song.from_dict(track))
        else:
            songs.append(Song.from_search_term(request))

    for song_list in lists:
        songs.extend(
            [create_empty_song(url=url, song_list=song_list) for url in song_list.urls]
        )  # type: ignore

    return songs
