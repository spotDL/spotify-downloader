from typing import List
from pathlib import Path

from spotdl.search import SongObject, song_gatherer
from spotdl.providers import lyrics_providers, metadata_provider


def parse_query(
    query: List[str],
    format,
    use_youtube,
    generate_m3u,
    lyrics_provider,
    threads,
    path_template,
) -> List[SongObject]:
    """
    Parse query and return list containing song object
    """

    songs_list = []

    # Iterate over all search queries and add them to songs_list
    for request in query:
        if request.endswith(".spotdlTrackingFile"):
            continue

        songs_list.extend(
            parse_request(
                request,
                format,
                use_youtube,
                generate_m3u,
                lyrics_provider,
                threads,
                path_template,
            )
        )

        # linefeed to visually separate output for each query
        print()

    # remove duplicates
    seen_songs = set()
    songs = []
    for song in songs_list:
        if song.file_name not in seen_songs:
            songs.append(song)
            seen_songs.add(song.file_name)

    return songs


def parse_request(
    request: str,
    output_format: str = None,
    use_youtube: bool = False,
    generate_m3u: bool = False,
    lyrics_provider: str = None,
    threads: int = 1,
    path_template: str = None,
) -> List[SongObject]:
    song_list: List[SongObject] = []
    if (
        ("youtube.com/watch?v=" in request or "youtu.be/" in request)
        and "open.spotify.com" in request
        and "track" in request
        and "|" in request
    ):
        urls = request.split("|")

        if len(urls) <= 1 or "youtu" not in urls[0] or "spotify" not in urls[1]:
            print("Incorrect format used, please use YouTubeURL|SpotifyURL")
        else:
            print("Fetching YouTube video with spotify metadata")
            song_list = [
                song
                for song in [
                    get_youtube_meta_track(
                        urls[0], urls[1], output_format, lyrics_provider
                    )
                ]
                if song is not None
            ]
    elif "open.spotify.com" in request and "track" in request:
        print("Fetching Song...")
        song = song_gatherer.from_spotify_url(
            request, output_format, use_youtube, lyrics_provider
        )
        try:
            song_list = [song] if song.youtube_link is not None else []
        except (OSError, ValueError, LookupError):
            song_list = []
    elif "open.spotify.com" in request and "album" in request:
        print("Fetching Album...")
        song_list = song_gatherer.from_album(
            request,
            output_format,
            use_youtube,
            lyrics_provider,
            generate_m3u,
            threads,
            path_template,
        )
    elif "open.spotify.com" in request and "playlist" in request:
        print("Fetching Playlist...")
        song_list = song_gatherer.from_playlist(
            request,
            output_format,
            use_youtube,
            lyrics_provider,
            generate_m3u,
            threads,
            path_template,
        )
    elif "open.spotify.com" in request and "artist" in request:
        print("Fetching artist...")
        song_list = song_gatherer.from_artist(
            request, output_format, use_youtube, lyrics_provider, threads
        )
    elif request == "saved":
        print("Fetching Saved Songs...")
        song_list = song_gatherer.from_saved_tracks(
            output_format, use_youtube, lyrics_provider, threads
        )
    else:
        print('Searching Spotify for song named "%s"...' % request)
        try:
            song_list = song_gatherer.from_search_term(
                request, output_format, use_youtube, lyrics_provider
            )
        except Exception as e:
            print(e)

    # filter out NONE songObj items (already downloaded)
    song_list = [song_object for song_object in song_list if song_object is not None]

    return song_list


def get_youtube_meta_track(
    youtube_url: str,
    spotify_url: str,
    output_format: str = None,
    lyrics_provider: str = None,
):
    # check if URL is a playlist, user, artist or album, if yes raise an Exception,
    # else procede

    # Get the Song Metadata
    raw_track_meta, raw_artist_meta, raw_album_meta = metadata_provider.from_url(
        spotify_url
    )

    song_name = raw_track_meta["name"]
    contributing_artist = [artist["name"] for artist in raw_track_meta["artists"]]
    converted_file_name = SongObject.create_file_name(
        song_name, [artist["name"] for artist in raw_track_meta["artists"]]
    )

    if output_format is None:
        output_format = "mp3"

    converted_file_path = Path(".", f"{converted_file_name}.{output_format}")

    # if a song is already downloaded skip it
    if converted_file_path.is_file():
        print(f'Skipping "{converted_file_name}" as it\'s already downloaded')
        return None

    # (try to) Get lyrics from musixmatch/genius
    # use musixmatch as the default provider
    if lyrics_provider == "genius":
        lyrics = lyrics_providers.get_lyrics_genius(song_name, contributing_artist)
    else:
        lyrics = lyrics_providers.get_lyrics_musixmatch(song_name, contributing_artist)

    return SongObject(
        raw_track_meta, raw_album_meta, raw_artist_meta, youtube_url, lyrics, None
    )
