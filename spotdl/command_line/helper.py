from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.embedders import EmbedderDefault
from spotdl.lyrics.providers import LyricWikia
from spotdl.lyrics.providers import Genius

from spotdl.track import Track

import spotdl.util

import urllib.request
import threading


def search_metadata(track, lyrics=True):
    youtube = ProviderYouTube()
    if spotdl.util.is_spotify(track):
        spotify = ProviderSpotify()
        spotify_metadata = spotify.from_url(track)
        # TODO: CONFIG.YML
        #       Generate string in config.search_format
        search_query = "{} - {}".format(
            spotify_metadata["artists"][0]["name"],
            spotify_metadata["name"]
        )
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


def download_track(metadata, arguments):
    # TODO: CONFIG.YML
    #       Exit here if config.dry_run

    # TODO: CONFIG.YML
    #       Check if test.mp3 already exists here

    # log.info(log_fmt)

    # TODO: CONFIG.YML
    #       Download tracks with name config.file_format

    # TODO: CONFIG.YML
    #       Append config.output_ext to config.file_format

    track = Track(metadata, cache_albumart=True)
    track.download_while_re_encoding("test.mp3")

    # TODO: CONFIG.YML
    #       Skip metadata if config.no_metadata

    track.apply_metadata("test.mp3")


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
        mutable_resource["next_track"] = search_metadata(track)

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
                metadata["current_track"] = search_metadata(current_track)
            if tracks_count > 0:
                next_track = tracks[0]
                next_track_metadata = threading.Thread(
                    target=mutable_assignment,
                    args=(metadata, next_track)
                )
                next_track_metadata.start()

            download_track(metadata["current_track"], log_fmt=(str(current_iteration) + ". {artist} - {track_name}"))
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

