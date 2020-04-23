from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.providers import YouTubeSearch
from spotdl.metadata.embedders import EmbedderDefault
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError
import spotdl.metadata

from spotdl.encode.encoders import EncoderFFmpeg
from spotdl.encode.encoders import EncoderAvconv

from spotdl.lyrics.providers import LyricWikia
from spotdl.lyrics.providers import Genius
from spotdl.lyrics.exceptions import LyricsNotFoundError

from spotdl.command_line.exceptions import NoYouTubeVideoError

from spotdl.track import Track

import spotdl.util

import os
import urllib.request


def search_lyrics(query):
    provider = Genius()
    try:
        lyrics = provider.from_query(query)
    except LyricsNotFoundError:
        lyrics = None
    return lyrics


def search_metadata_on_spotify(query):
    provider = ProviderSpotify()
    try:
        metadata = provider.from_query(query)
    except SpotifyMetadataNotFoundError:
        metadata = {}
    return metadata


def search_metadata(track, search_format="{artist} - {track-name} lyrics", manual=False):
    youtube = ProviderYouTube()
    youtube_searcher = YouTubeSearch()

    if spotdl.util.is_spotify(track):
        spotify = ProviderSpotify()
        spotify_metadata = spotify.from_url(track)
        lyric_query = spotdl.metadata.format_string(
            "{artist} - {track-name}",
            spotify_metadata,
        )
        search_query = spotdl.metadata.format_string(search_format, spotify_metadata)
        youtube_urls = youtube_searcher.search(search_query)
        if not youtube_urls:
            raise NoYouTubeVideoError(
                'No videos found for the search query: "{}"'.format(search_query)
            )
        if manual:
            pass
        else:
            youtube_url = youtube_urls.bestmatch()["url"]
        youtube_metadata = youtube.from_url(youtube_url)
        metadata = spotdl.util.merge(
            youtube_metadata,
            spotify_metadata
        )

    elif spotdl.util.is_youtube(track):
        metadata = youtube.from_url(track)
        lyric_query = spotdl.metadata.format_string(
            "{artist} - {track-name}",
            metadata,
        )

    else:
        lyric_query = track
        spotify_metadata = spotdl.util.ThreadWithReturnValue(
            target=search_metadata_on_spotify,
            args=(track,)
        )
        spotify_metadata.start()
        youtube_urls = youtube_searcher.search(track)
        if not youtube_urls:
        #     raise NoYouTubeVideoError(
        #         'No videos found for the search query: "{}"'.format(track)
        #     )
            return
        if manual:
            pass
        else:
            youtube_url = youtube_urls.bestmatch()["url"]
        youtube_metadata = youtube.from_url(youtube_url)
        metadata = spotdl.util.merge(
            youtube_metadata,
            spotify_metadata.join()
        )

    metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
        target=search_lyrics,
        args=(lyric_query,)
    )

    metadata["lyrics"].start()
    return metadata


def download_track(track, arguments):
    track_splits = track.split(":")
    if len(track_splits) == 2:
        youtube_track, spotify_track = track_splits
    metadata = search_metadata(track, search_format=arguments.search_format)
    log_fmt = spotdl.metadata.format_string(
        arguments.output_file,
        metadata,
        output_extension=arguments.output_ext,
    )
    # log.info(log_fmt)
    download_track_from_metadata(metadata, arguments)


def download_track_from_metadata(metadata, arguments):
    # TODO: Add `-m` flag
    track = Track(metadata, cache_albumart=(not arguments.no_metadata))
    print(metadata["name"])

    stream = metadata["streams"].get(
        quality=arguments.quality,
        preftype=arguments.input_ext,
    )
    # log.info(stream)

    Encoder = {
        "ffmpeg": EncoderFFmpeg,
        "avconv": EncoderAvconv,
    }.get(arguments.encoder)

    if Encoder is None:
        output_extension = stream["encoding"]
    else:
        output_extension = arguments.output_ext

    filename = spotdl.metadata.format_string(
        arguments.output_file,
        metadata,
        output_extension=output_extension,
        sanitizer=lambda s: spotdl.util.sanitize(
            s, spaces_to_underscores=arguments.no_spaces
        )
    )
    print(filename)
    # log.info(filename)

    to_skip = arguments.dry_run
    if not to_skip and os.path.isfile(filename):
        if arguments.overwrite == "force":
            to_skip = False
        elif arguments.overwrite == "prompt":
            to_skip = not input("overwrite? (y/N)").lower() == "y"
        else:
            to_skip = True

    if to_skip:
        return

    if Encoder is None:
        track.download(stream, filename)
    else:
        track.download_while_re_encoding(
            stream,
            filename,
            target_encoding=output_extension,
            encoder=Encoder()
        )

    if not arguments.no_metadata:
        track.metadata["lyrics"] = track.metadata["lyrics"].join()
        try:
            track.apply_metadata(filename, encoding=output_extension)
        except TypeError:
            # log.warning("Cannot write metadata to given file")
            pass


def download_tracks_from_file(path, arguments):
    # log.info(
    #     "Checking and removing any duplicate tracks "
    #     "in reading {}".format(path)
    # )
    with open(path, "r") as fin:
        # Read tracks into a list and remove any duplicates
        tracks = fin.read().splitlines()

    # Remove duplicates and empty elements
    # Also strip whitespaces from elements (if any)
    spotdl.util.remove_duplicates(
        tracks,
        condition=lambda x: x,
        operation=str.strip
    )

    # Overwrite file
    with open(path, "w") as fout:
        fout.writelines(tracks)

    for number, track in enumerate(tracks, 1):
        try:
            metadata = search_metadata(next_track, arguments.search_format)
            log_fmt=(str(number) + ". {artist} - {track-name}")
            # log.info(log_fmt)
            download_track_from_metadata(metadata, arguments)
        except (urllib.request.URLError, TypeError, IOError) as e:
            # log.exception(e.args[0])
            # log.warning("Failed. Will retry after other songs\n")
            tracks.append(track)
        else:
            if arguments.write_sucessful:
                with open(arguments.write_successful, "a") as fout:
                    fout.write(track)
        finally:
            with open(path, "w") as fout:
                fout.writelines(tracks[number-1:])


def download_tracks_from_file_threaded(path, arguments):
    # FIXME: Can we make this function cleaner?

    # log.info(
    #     "Checking and removing any duplicate tracks "
    #     "in reading {}".format(path)
    # )
    with open(path, "r") as fin:
        # Read tracks into a list and remove any duplicates
        tracks = fin.read().splitlines()

    # Remove duplicates and empty elements
    # Also strip whitespaces from elements (if any)
    spotdl.util.remove_duplicates(
        tracks,
        condition=lambda x: x,
        operation=str.strip
    )

    # Overwrite file
    with open(path, "w") as fout:
        fout.writelines(tracks)

    tracks_count = len(tracks)
    current_iteration = 1

    next_track = tracks.pop(0)
    metadata = {
        "current_track": None,
        "next_track": spotdl.util.ThreadWithReturnValue(
            target=search_metadata,
            args=(next_track, arguments.search_format)
        )
    }
    metadata["next_track"].start()
    while tracks_count > 0:
        metadata["current_track"] = metadata["next_track"].join()
        metadata["next_track"] = None
        try:
            print(tracks_count)
            print(tracks)
            if tracks_count > 1:
                current_track = next_track
                next_track = tracks.pop(0)
                metadata["next_track"] = spotdl.util.ThreadWithReturnValue(
                    target=search_metadata,
                    args=(next_track, arguments.search_format)
                )
                metadata["next_track"].start()

            log_fmt=(str(current_iteration) + ". {artist} - {track-name}")
            # log.info(log_fmt)
            if metadata["current_track"] is None:
                # log.warning("Something went wrong. Will retry after downloading remaining tracks")
                pass
            print(metadata["current_track"]["name"])
            # download_track_from_metadata(
            #     metadata["current_track"],
            #     arguments
            # )
        except (urllib.request.URLError, TypeError, IOError) as e:
            # log.exception(e.args[0])
            # log.warning("Failed. Will retry after other songs\n")
            tracks.append(current_track)
        else:
            tracks_count -= 1
            if arguments.write_successful:
                with open(arguments.write_successful, "a") as fout:
                    fout.write(current_track)
        finally:
            current_iteration += 1
            with open(path, "w") as fout:
                fout.writelines(tracks)

