"""
Module for creating Song objects by interacting with Spotify API
or by parsing a query.

To use this module you must first initialize the SpotifyClient.
"""

import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ytmusicapi import YTMusic

from spotdl.types.album import Album
from spotdl.types.artist import Artist
from spotdl.types.playlist import Playlist
from spotdl.types.saved import Saved
from spotdl.types.song import Song, SongList
from spotdl.utils.metadata import get_file_metadata

__all__ = [
    "QueryError",
    "get_search_results",
    "parse_query",
    "get_simple_songs",
    "reinit_song",
    "get_song_from_file_metadata",
    "gather_known_songs",
    "create_ytm_album",
    "create_ytm_playlist",
]

logger = logging.getLogger(__name__)
client = YTMusic()


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

    return Song.list_from_search_term(search_term)


def parse_query(
    query: List[str],
    threads: int = 1,
    use_ytm_data: bool = False,
) -> List[Song]:
    """
    Parse query and return list containing song object

    ### Arguments
    - query: List of strings containing query
    - threads: Number of threads to use

    ### Returns
    - List of song objects
    """

    songs: List[Song] = get_simple_songs(query, use_ytm_data=use_ytm_data)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        for song in executor.map(reinit_song, songs):
            results.append(song)

    return results


def get_simple_songs(
    query: List[str],
    use_ytm_data: bool = False,
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
        logger.info("Processing query: %s", request)

        if (
            ("youtube.com/watch?v=" in request or "youtu.be/" in request)
            and "open.spotify.com" in request
            and "track" in request
            and "|" in request
        ):
            split_urls = request.split("|")
            if (
                len(split_urls) <= 1
                or not ("youtube" in split_urls[0] or "youtu.be" in split_urls[0])
                or "spotify" not in split_urls[1]
            ):
                raise QueryError(
                    'Incorrect format used, please use "YouTubeURL|SpotifyURL"'
                )

            songs.append(
                Song.from_missing_data(url=split_urls[1], download_url=split_urls[0])
            )
        elif (
            "https://music.youtube.com/playlist?list=" in request
            or "https://music.youtube.com/browse/VLPL" in request
        ):
            split_urls = request.split("|")
            if len(split_urls) == 1:
                if "?list=OLAK5uy_" in request:
                    lists.append(create_ytm_album(request, fetch_songs=False))
                elif "?list=PL" in request or "browse/VLPL" in request:
                    lists.append(create_ytm_playlist(request, fetch_songs=False))
            else:
                if ("spotify" not in split_urls[1]) or not any(
                    x in split_urls[0]
                    for x in ["?list=PL", "?list=OLAK5uy_", "browse/VLPL"]
                ):
                    raise QueryError(
                        'Incorrect format used, please use "YouTubeMusicURL|SpotifyURL". '
                        "Currently only supports YouTube Music playlists and albums."
                    )

                if ("open.spotify.com" in request and "album" in request) and (
                    "?list=OLAK5uy_" in request
                ):
                    ytm_list: SongList = create_ytm_album(
                        split_urls[0], fetch_songs=False
                    )
                    spot_list = Album.from_url(split_urls[1], fetch_songs=False)
                elif ("open.spotify.com" in request and "playlist" in request) and (
                    "?list=PL" in request or "browse/VLPL" in request
                ):
                    ytm_list = create_ytm_playlist(split_urls[0], fetch_songs=False)
                    spot_list = Playlist.from_url(split_urls[1], fetch_songs=False)
                else:
                    raise QueryError(
                        f"URLs are not of the same type, {split_urls[0]} is not "
                        f"the same type as {split_urls[1]}."
                    )

                if ytm_list.length != spot_list.length:
                    raise QueryError(
                        f"The YouTube Music ({ytm_list.length}) "
                        f"and Spotify ({spot_list.length}) lists have different lengths. "
                    )

                if use_ytm_data:
                    for index, song in enumerate(ytm_list.songs):
                        song.url = spot_list.songs[index].url

                    lists.append(ytm_list)
                else:
                    for index, song in enumerate(spot_list.songs):
                        song.download_url = ytm_list.songs[index].download_url

                    lists.append(spot_list)
        elif "open.spotify.com" in request and "track" in request:
            songs.append(Song.from_url(url=request))
        elif "open.spotify.com" in request and "playlist" in request:
            lists.append(Playlist.from_url(request, fetch_songs=False))
        elif "open.spotify.com" in request and "album" in request:
            lists.append(Album.from_url(request, fetch_songs=False))
        elif "open.spotify.com" in request and "artist" in request:
            lists.append(Artist.from_url(request, fetch_songs=False))
        elif "album:" in request:
            lists.append(Album.from_search_term(request, fetch_songs=False))
        elif "playlist:" in request:
            lists.append(Playlist.from_search_term(request, fetch_songs=False))
        elif "artist:" in request:
            lists.append(Artist.from_search_term(request, fetch_songs=False))
        elif request == "saved":
            lists.append(Saved.from_url(request, fetch_songs=False))
        elif request.endswith(".spotdl"):
            with open(request, "r", encoding="utf-8") as save_file:
                for track in json.load(save_file):
                    # Append to songs
                    songs.append(Song.from_dict(track))
        else:
            songs.append(Song.from_search_term(request))

    for song_list in lists:
        logger.info(
            "Found %s songs in %s (%s)",
            len(song_list.urls),
            song_list.name,
            song_list.__class__.__name__,
        )

        for song in song_list.songs:
            if song.song_list:
                song_data = song.json
            else:
                song_data = song.json
                song_data["song_list"] = song_list

            songs.append(Song.from_dict(song_data))

    logger.debug("Found %s songs in %s lists", len(songs), len(lists))

    return songs


def songs_from_albums(albums: List[str]):
    """
    Get all songs from albums ids/urls/etc.

    ### Arguments
    - albums: List of albums ids

    ### Returns
    - List of songs
    """

    songs = []
    for album_id in albums:
        album = Album.from_url(album_id, fetch_songs=False)

        for song in album.songs:
            if song.song_list:
                songs.append(Song.from_missing_data(**song.json))
            else:
                song_data = song.json
                song_data["song_list"] = album
                songs.append(Song.from_missing_data(**song_data))

    return songs


def reinit_song(song: Song, playlist_numbering: bool = False) -> Song:
    """
    Update song object with new data
    from Spotify

    ### Arguments
    - song: Song object
    - playlist_numbering: bool, default value is False

    ### Returns
    - Updated song object
    """

    data = song.json
    if data.get("url"):
        new_data = Song.from_url(data["url"]).json
    elif data.get("name") and data.get("artist"):
        new_data = Song.from_search_term(data["name"]).json
    else:
        raise QueryError("Song object is missing required data to be reinitialized")

    for key in Song.__dataclass_fields__:  # type: ignore # pylint: disable=E1101
        val = data.get(key)
        new_val = new_data.get(key)
        if new_val is not None and val is None:
            data[key] = new_val
        elif new_val is not None and val is not None:
            data[key] = val

    if data.get("song_list"):
        # Reinitialize the correct song list object
        if song.song_list:
            song_list = song.song_list.__class__(**data["song_list"])
            data["song_list"] = song_list
            data["list_position"] = song_list.urls.index(song.url)
            if playlist_numbering:
                data["track_number"] = data["list_position"] + 1
                data["tracks_count"] = len(song_list.urls)
                data["album_name"] = song_list.name
                if isinstance(song_list, Playlist):
                    data["album_artist"] = song_list.author_name
                    data["cover_url"] = song_list.cover_url
                data["disc_number"] = 1
                data["disc_count"] = 1

    # return reinitialized song object
    return Song(**data)


def get_song_from_file_metadata(file: Path) -> Optional[Song]:
    """
    Get song based on the file metadata or file name

    ### Arguments
    - file: Path to file

    ### Returns
    - Song object
    """

    file_metadata = get_file_metadata(file)

    if file_metadata is None:
        return None

    return Song.from_missing_data(**file_metadata)


def gather_known_songs(output: str, output_format: str) -> Dict[str, List[Path]]:
    """
    Gather all known songs from the output directory

    ### Arguments
    - output: Output path template
    - output_format: Output format

    ### Returns
    - Dictionary containing all known songs and their paths
    """

    # Get the base directory from the path template
    # Path("/Music/test/{artist}/{artists} - {title}.{output-ext}") -> "/Music/test"
    base_dir = output.split("{", 1)[0]
    paths = Path(base_dir).glob(f"**/*.{output_format}")

    known_songs: Dict[str, List[Path]] = {}
    for path in paths:
        # Try to get the song from the metadata
        song = get_song_from_file_metadata(path)

        # If the songs doesn't have metadata, try to get it from the filename
        if song is None or song.url is None:
            search_results = get_search_results(path.stem)
            if len(search_results) == 0:
                continue

            song = search_results[0]

        known_paths = known_songs.get(song.url)
        if known_paths is None:
            known_songs[song.url] = [path]
        else:
            known_songs[song.url].append(path)

    return known_songs


def create_ytm_album(url: str, fetch_songs: bool = True) -> Album:
    """
    Creates a list of Song objects from an album query.

    ### Arguments
    - album_query: the url of the album

    ### Returns
    - a list of Song objects
    """

    if "?list=" not in url or not url.startswith("https://music.youtube.com/"):
        raise ValueError(f"Invalid album url: {url}")

    browse_id = client.get_album_browse_id(url.split("?list=")[1].split("&")[0])
    if browse_id is None:
        raise ValueError(f"Invalid album url: {url}")

    album = client.get_album(browse_id)

    if album is None:
        raise ValueError(f"Couldn't fetch album: {url}")

    metadata = {
        "artist": album["artists"][0]["name"],
        "name": album["title"],
        "url": url,
    }

    songs = []
    for track in album["tracks"]:
        artists = [artist["name"] for artist in track["artists"]]
        song = Song.from_missing_data(
            name=track["title"],
            artists=artists,
            artist=artists[0],
            album_name=metadata["name"],
            album_artist=metadata["artist"],
            duration=track["duration_seconds"],
            download_url=f"https://music.youtube.com/watch?v={track['videoId']}",
        )

        if fetch_songs:
            song = Song.from_search_term(f"{song.artist} - {song.name}")

        songs.append(song)

    return Album(**metadata, songs=songs, urls=[song.url for song in songs])


def create_ytm_playlist(url: str, fetch_songs: bool = True) -> Playlist:
    """
    Returns a playlist object from a youtube playlist url

    ### Arguments
    - url: the url of the playlist

    ### Returns
    - a Playlist object
    """

    if not ("?list=" in url or "/browse/VLPL" in url) or not url.startswith(
        "https://music.youtube.com/"
    ):
        raise ValueError(f"Invalid playlist url: {url}")

    if "/browse/VLPL" in url:
        playlist_id = url.split("/browse/")[1]
    else:
        playlist_id = url.split("?list=")[1]
    playlist = client.get_playlist(playlist_id, None)  # type: ignore

    if playlist is None:
        raise ValueError(f"Couldn't fetch playlist: {url}")

    metadata = {
        "description": playlist["description"]
        if playlist["description"] is not None
        else "",
        "author_url": f"https://music.youtube.com/channel/{playlist['author']['id']}",
        "author_name": playlist["author"]["name"],
        "cover_url": playlist["thumbnails"][0]["url"],
        "name": playlist["title"],
        "url": url,
    }

    songs = []
    for track in playlist["tracks"]:
        if track["videoId"] is None:
            continue

        song = Song.from_missing_data(
            name=track["title"],
            artists=[artist["name"] for artist in track["artists"]],
            artist=track["artists"][0]["name"],
            album_name=track.get("album", {}).get("name")
            if track.get("album") is not None
            else None,
            duration=track["duration_seconds"],
            explicit=track["isExplicit"],
            download_url=f"https://music.youtube.com/watch?v={track['videoId']}",
        )

        if fetch_songs:
            song = reinit_song(song)

        songs.append(song)

    return Playlist(**metadata, songs=songs, urls=[song.url for song in songs])
