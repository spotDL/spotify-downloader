import concurrent.futures

from pathlib import Path
from typing import Dict, List
import platform

from spotdl.providers import (
    metadata_provider,
    yt_provider,
    ytm_provider,
    provider_utils,
    lyrics_providers,
)
from spotdl.search import SongObject, SpotifyClient
from spotdl.utils.song_name_utils import format_name
from spotdl.providers.provider_utils import (
    _get_converted_file_path,
    _parse_path_template,
)


def from_spotify_url(
    spotify_url: str,
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
    playlist: dict = None,
) -> SongObject:
    """
    Creates song object using spotfy url

    `str` `spotify_url` : spotify url used to create song object
    `str` `output_format` : output format of the song

    returns a `SongObject`
    """

    # Set default ouput format to mp3
    if output_format is None:
        output_format = "mp3"

    # Get the Song Metadata
    raw_track_meta, raw_artist_meta, raw_album_meta = metadata_provider.from_url(
        spotify_url
    )

    if raw_track_meta is None:
        raise ValueError("Couldn't get metadata from url")

    song_name = raw_track_meta["name"]
    album_name = raw_track_meta["album"]["name"]
    isrc = raw_track_meta.get("external_ids", {}).get("isrc")
    duration = round(raw_track_meta["duration_ms"] / 1000, ndigits=3)
    contributing_artists = [artist["name"] for artist in raw_track_meta["artists"]]
    display_name = ", ".join(contributing_artists) + " - " + song_name

    # Create file name
    converted_file_name = SongObject.create_file_name(
        song_name, [artist["name"] for artist in raw_track_meta["artists"]]
    )

    # Ensure file name doesnt contain forbidden characters
    filesystem_display_name = display_name  # Create copy of display_name for filesystem use
    if platform.system() == 'Windows':
        for forbidden_letter in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            converted_file_name = converted_file_name.replace(forbidden_letter, '')
            filesystem_display_name = filesystem_display_name.replace(forbidden_letter, '')
    else:  # Linux or MacOS
        converted_file_name = converted_file_name.replace('/', '')
        filesystem_display_name = filesystem_display_name.replace('/', '')

    # If song name is too long use only first artist
    if len(converted_file_name) > 250:
        converted_file_name = SongObject.create_file_name(
            song_name, [raw_track_meta["artists"][0]["name"]]
        )

    converted_file_path = Path(".", f"{converted_file_name}.{output_format}")

    # Alternate file path.
    alternate_file_path = Path(".", f"{filesystem_display_name}.{output_format}")

    # if a song is already downloaded skip it
    if converted_file_path.is_file() or alternate_file_path.is_file():
        print(f'Skipping "{converted_file_name}" as it\'s already downloaded')
        raise OSError(f"{converted_file_name} already downloaded")

    # Get the song's downloadable audio link
    if use_youtube:
        print(f'Searching YouTube for "{display_name}"', end="\r")
        youtube_link = yt_provider.search_and_get_best_match(
            song_name, contributing_artists, duration, isrc
        )
    else:
        print(f'Searching YouTube Music for "{display_name}"', end="\r")
        youtube_link = ytm_provider.search_and_get_best_match(
            song_name, contributing_artists, album_name, duration, isrc
        )

    # Check if we found youtube url
    if youtube_link is None:
        print(
            f'Could not match any of the results on YouTube for "{display_name}". Skipping'
        )
        raise LookupError("Could not match any of the results on YouTube for")
    else:
        print(" " * (len(display_name) + 25), end="\r")
        print(f'Found YouTube URL for "{display_name}" : {youtube_link}')

    # (try to) Get lyrics from musixmatch/genius
    # use musixmatch as the default provider
    if lyrics_provider == "genius":
        lyrics = lyrics_providers.get_lyrics_genius(song_name, contributing_artists)
    else:
        lyrics = lyrics_providers.get_lyrics_musixmatch(song_name, contributing_artists)

    return SongObject(
        raw_track_meta, raw_album_meta, raw_artist_meta, youtube_link, lyrics, playlist
    )


def from_search_term(
    query: str,
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
) -> List[SongObject]:
    """
    Queries Spotify for a song and returns the best match

    `str` `query` : what you'd type into Spotify's search box
    `str` `output_format` : output format of the song

    returns a `list<SongObject>` containing Url's of each track in the given album
    """

    # get a spotify client
    spotify_client = SpotifyClient()

    # get possible matches from spotify
    result = spotify_client.search(query, type="track")

    # return first result link or if no matches are found, raise Exception
    if result is None or len(result.get("tracks", {}).get("items", [])) == 0:
        raise Exception("No song matches found on Spotify")
    song_url = "http://open.spotify.com/track/" + result["tracks"]["items"][0]["id"]
    try:
        song = from_spotify_url(
            song_url, output_format, use_youtube, lyrics_provider, None
        )
        return [song] if song.youtube_link is not None else []
    except (LookupError, OSError, ValueError):
        return []


def from_album(
    album_url: str,
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
    generate_m3u: bool = False,
    threads: int = 1,
    path_template: str = None,
) -> List[SongObject]:
    """
    Create and return list containing SongObject for every song in the album

    `str` `album_url` : Spotify Url of the album whose tracks are to be retrieved
    `str` `output_format` : output format of the song

    returns a `list<SongObject>` containing Url's of each track in the given album
    """

    spotify_client = SpotifyClient()
    tracks = []

    album_response = spotify_client.album_tracks(album_url)
    if album_response is None:
        raise ValueError("Wrong album id")

    album_tracks = album_response["items"]

    # Get all tracks from album
    while album_response["next"]:
        album_response = spotify_client.next(album_response)

        # Failed to get response, break the loop
        if album_response is None:
            break

        album_tracks.extend(album_response["items"])

    # Remove songs  without id
    album_tracks = [
        track
        for track in album_tracks
        if track is not None and track.get("id") is not None
    ]

    def get_tracks(track):
        try:
            song = from_spotify_url(
                "https://open.spotify.com/track/" + track["id"],
                output_format,
                use_youtube,
                lyrics_provider,
                None,
            )

            if generate_m3u:
                if path_template:
                    file_path = _parse_path_template(path_template, song, output_format)
                else:
                    file_path = _get_converted_file_path(song, output_format)

                return song, f"{file_path}\n"

            return song, None
        except (LookupError, ValueError):
            return None, None
        except OSError:
            if generate_m3u:
                song_obj = SongObject(track, album_response, {}, None, "", None)
                if path_template:
                    file_path = _parse_path_template(
                        path_template, song_obj, output_format
                    )
                else:
                    file_path = _get_converted_file_path(song_obj, output_format)

                return None, f"{file_path}\n"

            return None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(get_tracks, album_tracks)

    album_text = ""
    for result in results:
        if result[1] is not None:
            album_text += result[1]

        if result[0] is not None and result[0].youtube_link is not None:
            tracks.append(result[0])

    if album_response and generate_m3u is True:
        album_data = spotify_client.album(album_url)

        if album_data is not None:
            album_name = album_data["name"]
        else:
            album_name = album_tracks[0]["name"]

        album_name = format_name(album_name)

        album_file = Path(f"{album_name}.m3u")

        with open(album_file, "w", encoding="utf-8") as file:
            file.write(album_text)

    return tracks


def from_playlist(
    playlist_url: str,
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
    generate_m3u: bool = False,
    threads: int = 1,
    path_template: str = None,
) -> List[SongObject]:
    """
    Create and return list containing SongObject for every song in the playlist

    `str` `album_url` : Spotify Url of the album whose tracks are to be retrieved
    `str` `output_format` : output format of the song

    returns a `list<SongObject>` containing Url's of each track in the given album
    """

    spotify_client = SpotifyClient()
    tracks = []

    playlist_response = spotify_client.playlist_tracks(playlist_url)
    playlist = spotify_client.playlist(playlist_url)
    if playlist_response is None:
        raise ValueError("Wrong playlist id")

    playlist_tracks = [
        track
        for track in playlist_response["items"]
        # check if track has id
        if track is not None
        and track.get("track") is not None
        and track["track"].get("id") is not None
    ]

    # Get all tracks from playlist
    while playlist_response["next"]:
        playlist_response = spotify_client.next(playlist_response)

        # Failed to get response, break the loop
        if playlist_response is None:
            break

        playlist_tracks.extend(playlist_response["items"])

    # Remove songs  without id
    playlist_tracks = [
        track
        for track in playlist_tracks
        if track is not None
        and track.get("track") is not None
        and track["track"].get("id") is not None
    ]

    def get_song(track):
        try:
            song = from_spotify_url(
                "https://open.spotify.com/track/" + track["track"]["id"],
                output_format,
                use_youtube,
                lyrics_provider,
                playlist,
            )

            if generate_m3u:
                if path_template:
                    file_path = _parse_path_template(path_template, song, output_format)
                else:
                    file_path = _get_converted_file_path(song, output_format)

                return song, f"{file_path}\n"

            return song, None
        except (LookupError, ValueError):
            return None, None
        except OSError:
            if generate_m3u:
                song_obj = SongObject(
                    track["track"], {}, {}, None, "", playlist_response
                )
                if path_template:
                    file_path = _parse_path_template(
                        path_template, song_obj, output_format
                    )
                else:
                    file_path = _get_converted_file_path(song_obj, output_format)

                return None, f"{file_path}\n"

            return None, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(get_song, playlist_tracks)

    playlist_text = ""
    for result in results:
        if result[1] is not None:
            playlist_text += result[1]

        if result[0] is not None and result[0].youtube_link is not None:
            tracks.append(result[0])

    if playlist_response and generate_m3u is True:
        playlist_data = spotify_client.playlist(playlist_url)

        if playlist_data is not None:
            playlist_name = playlist_data["name"]
        else:
            playlist_name = playlist_tracks[0]["track"]["name"]

        playlist_name = format_name(playlist_name)

        playlist_file = Path(f"{playlist_name}.m3u")

        with open(playlist_file, "w", encoding="utf-8") as file:
            file.write(playlist_text)

    return tracks


def from_artist(
    artist_url: str,
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
    threads: int = 1,
) -> List[SongObject]:
    """
    `str` `artist_url` : Spotify Url of the artist whose tracks are to be
    retrieved
    returns a `list<songObj>` containing Url's of each track in the artist profile
    """

    spotify_client = SpotifyClient()

    artist_tracks = []

    artist_response = spotify_client.artist_albums(
        artist_url, album_type="album,single"
    )
    if artist_response is None:
        raise ValueError("Wrong artist id")

    albums_list = artist_response["items"]
    albums_object: Dict[str, str] = {}

    # Fetch all artist albums
    while artist_response and artist_response["next"]:
        response = spotify_client.next(artist_response)
        if response is None:
            break

        artist_response = response
        albums_list.extend(artist_response["items"])

    # Remove duplicate albums
    for album in albums_list:
        # return an iterable containing the string's alphanumeric characters
        alpha_numeric_filter = filter(str.isalnum, album["name"].lower())

        # join all characters into one string
        album_name = "".join(alpha_numeric_filter)

        if albums_object.get(album_name) is None:
            albums_object[album_name] = album["uri"]

    tracks_list = []
    tracks_object: Dict[str, str] = {}

    # Fetch all tracks from all albums
    for album_uri in albums_object.values():
        response = spotify_client.album_tracks(album_uri)
        if response is None:
            continue

        album_response = response
        album_tracks = album_response["items"]

        while album_response["next"]:
            album_response = spotify_client.next(album_response)
            if album_response is None:
                break

            album_tracks.extend(album_response["items"])

        tracks_list.extend(album_tracks)

    # Filter tracks to remove duplicates and songs without our artist
    for track in tracks_list:
        # ignore None tracks or tracks without uri
        if track is not None and track.get("uri") is None:
            continue

        # return an iterable containing the string's alphanumeric characters
        alphaNumericFilter = filter(str.isalnum, track["name"].lower())

        # join all characters into one string
        trackName = "".join(alphaNumericFilter)

        if tracks_object.get(trackName) is None:
            for artist in track["artists"]:
                # get artist id from url
                # https://api.spotify.com/v1/artists/1fZAAHNWdSM5gqbi9o5iEA/albums
                #
                # split string
                #  ['https:', '', 'api.spotify.com', 'v1', 'artists',
                #  '1fZAAHNWdSM5gqbi9o5iEA', 'albums']
                #
                # get second element from the end
                # '1fZAAHNWdSM5gqbi9o5iEA'
                artistId = artist_response["href"].split("/")[-2]

                # ignore tracks that are not from our artist by checking
                # the id
                if artist["id"] == artistId:
                    tracks_object[trackName] = track["uri"]

    # Create song objects from track ids
    def get_song(track_uri):
        try:
            return from_spotify_url(
                f"https://open.spotify.com/track/{track_uri.split(':')[-1]}",
                output_format,
                use_youtube,
                lyrics_provider,
                None,
            )
        except (LookupError, ValueError, OSError):
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(get_song, tracks_object.values())

    for result in results:
        if result is not None and result.youtube_link is not None:
            artist_tracks.append(result)

    return artist_tracks


def from_saved_tracks(
    output_format: str = None,
    use_youtube: bool = False,
    lyrics_provider: str = None,
    threads: int = 1,
) -> List[SongObject]:
    """
    Create and return list containing SongObject for every song that user has saved

    `str` `output_format` : output format of the song

    returns a `list<songObj>` containing Url's of each track in the user's saved tracks
    """

    spotify_client = SpotifyClient()

    saved_tracks_response = spotify_client.current_user_saved_tracks()
    if saved_tracks_response is None:
        raise Exception("Couldn't get saved tracks")

    saved_tracks = saved_tracks_response["items"]
    tracks = []

    # Fetch all saved tracks
    while saved_tracks_response and saved_tracks_response["next"]:
        response = spotify_client.next(saved_tracks_response)
        # response is wrong, break
        if response is None:
            break

        saved_tracks_response = response
        saved_tracks.extend(saved_tracks_response["items"])

    # Remove songs  without id
    saved_tracks = [
        track
        for track in saved_tracks
        if track is not None
        and track.get("track") is not None
        and track.get("track", {}).get("id") is not None
    ]

    def get_song(track):
        try:
            return from_spotify_url(
                "https://open.spotify.com/track/" + track["track"]["id"],
                output_format,
                use_youtube,
                lyrics_provider,
                None,
            )
        except (LookupError, ValueError, OSError):
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        results = executor.map(get_song, saved_tracks)

    for result in results:
        if result is not None and result.youtube_link is not None:
            tracks.append(result)

    return tracks


def from_dump(data_dump: dict) -> SongObject:
    """
    Creates song object from data dump

    `dict` `data_dump` : data dump used to create song object

    returns `SongObject`
    """

    raw_track_meta = data_dump["raw_track_meta"]
    raw_album_meta = data_dump["raw_album_meta"]
    raw_artist_meta = data_dump["raw_artist_meta"]
    youtube_link = data_dump["youtube_link"]
    lyrics = data_dump["lyrics"]

    return SongObject(
        raw_track_meta, raw_album_meta, raw_artist_meta, youtube_link, lyrics, None
    )
