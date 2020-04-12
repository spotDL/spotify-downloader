from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.embedders import EmbedderDefault

from spotdl.encode.encoders import EncoderFFmpeg
from spotdl.encode.encoders import EncoderAvconv

from spotdl.lyrics.providers import LyricWikia
from spotdl.lyrics.providers import Genius

from spotdl.track import Track

import spotdl.util

import os
import urllib.request


def search_metadata(track, lyrics=True, search_format="{artist} - {track-name}"):
    youtube = ProviderYouTube()
    if spotdl.util.is_spotify(track):
        spotify = ProviderSpotify()
        spotify_metadata = spotify.from_url(track)
        search_query = spotdl.util.format_string(search_format, spotify_metadata)
        youtube_metadata = youtube.from_query(search_query)
        metadata = spotdl.util.merge(
            youtube_metadata,
            spotify_metadata
        )
    elif spotdl.util.is_youtube(track):
        metadata = youtube.from_url(track)
    else:
        metadata = youtube.from_query(track)

    return metadata


def download_track(track, arguments):
    metadata = search_metadata(track, search_format=arguments.search_format)
    log_fmt = spotdl.util.format_string(
        arguments.file_format,
        metadata,
        output_extension=arguments.output_ext
    )
    # log.info(log_fmt)
    download_track_from_metadata(metadata, arguments)


def download_track_from_metadata(metadata, arguments):
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

    filename = spotdl.util.format_string(
        arguments.file_format,
        metadata,
        output_extension=output_extension
    )
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
        try:
            track.apply_metadata(filename, encoding=output_extension)
        except TypeError:
            # log.warning("Cannot write metadata to given file")
            pass


def download_tracks_from_file(path, arguments):
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
            args=(next_track, True, arguments.search_format)
        )
    }
    metadata["next_track"].start()
    while tracks_count > 0:
        tracks_count -= 1
        metadata["current_track"] = metadata["next_track"].join()
        metadata["next_track"] = None
        try:
            if tracks_count > 0:
                current_track = next_track
                next_track = tracks.pop(0)
                metadata["next_track"] = spotdl.util.ThreadWithReturnValue(
                    target=search_metadata,
                    args=(next_track, True, arguments.search_format)
                )
                metadata["next_track"].start()

            log_fmt=(str(current_iteration) + ". {artist} - {track-name}")
            # log.info(log_fmt)
            download_track_from_metadata(
                metadata["current_track"],
                arguments
            )
            current_iteration += 1
        except (urllib.request.URLError, TypeError, IOError) as e:
            # log.exception(e.args[0])
            # log.warning("Failed. Will retry after other songs\n")
            tracks.append(current_track)
        else:
            if arguments.write_successful:
                with open(arguments.write_successful, "a") as fout:
                    fout.write(current_track)
        finally:
            with open(path, "w") as fout:
                fout.writelines(tracks)

