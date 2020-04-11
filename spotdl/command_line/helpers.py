from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.embedders import EmbedderDefault
from spotdl.lyrics.providers import LyricWikia
from spotdl.lyrics.providers import Genius

from spotdl.track import Track

import spotdl.util

import urllib.request
import threading


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
    # log.info(log_fmt)

    filename = spotdl.util.format_string(
        arguments.file_format,
        metadata,
        output_extension=arguments.output_ext
    )

    if arguments.dry_run:
        return

    if os.path.isfile(filename):
        if arguments.overwrite == "skip":
            to_skip = True
        elif arguments.overwrite == "prompt":
            to_skip = not input("overwrite? (y/N)").lower() == "y"

    if to_skip:
        return

    if arguments.no_encode:
        track.download(filename)
    else:
        track.download_while_re_encoding(
            filename,
            target_encoding=arguments.output_ext
        )

    if not arguments.no_metadata:
        track.apply_metadata(filename, encoding=arguments.output_ext)


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
    spotdl.util.remove_duplicates(tracks, condition=lambda x: x, operation=str.strip)

    # Overwrite file
    with open(path, "w") as fout:
        fout.writelines(tracks)

    next_track_metadata = threading.Thread(target=lambda: None)
    next_track_metadata.start()
    tracks_count = len(tracks)
    current_iteration = 1

    def mutable_assignment(mutable_resource, track):
        mutable_resource["next_track"] = search_metadata(
            track,
            search_format=arguments.search_format
        )

    metadata = {
        "current_track": None,
        "next_track": None,
    }
    while tracks_count > 0:
        current_track = tracks.pop(0)
        tracks_count -= 1
        metadata["current_track"] = metadata["next_track"]
        metadata["next_track"] = None
        try:
            if metadata["current_track"] is None:
                metadata["current_track"] = search_metadata(
                    current_track,
                    search_format=arguments.search_format
                )
            if tracks_count > 0:
                next_track = tracks[0]
                next_track_metadata = threading.Thread(
                    target=mutable_assignment,
                    args=(metadata, next_track)
                )
                next_track_metadata.start()

            log_fmt=(str(current_iteration) + ". {artist} - {track-name}")
            # log.info(log_fmt)
            download_track_from_metadata(
                metadata["current_track"],
                arguments
            )
            current_iteration += 1
            next_track_metadata.join()
        except (urllib.request.URLError, TypeError, IOError) as e:
            # log.exception(e.args[0])
            # log.warning("Failed. Will retry after other songs\n")
            tracks.append(current_track)
        else:
            # TODO: CONFIG.YML
            #       Write track to config.write_sucessful
            pass
        finally:
            with open(path, "w") as fout:
                fout.writelines(tracks)

