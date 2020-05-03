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

from spotdl.authorize.services import AuthorizeSpotify

from spotdl.track import Track
import spotdl.util
import spotdl.config

from spotdl.command_line.exceptions import NoYouTubeVideoError

import sys
import os
import urllib.request

import logging
logger = logging.getLogger(name=__name__)

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


def prompt_for_youtube_search_result(videos):
    print("0. Skip downloading this track", file=sys.stderr)
    for index, video in enumerate(videos, 1):
        video_repr = "{index}. {title} ({url}) [{duration}]".format(
            index=index,
            title=video["title"],
            url=video["url"],
            duration=video["duration"],
        )
        print(video_repr, file=sys.stderr)

    selection = spotdl.util.prompt_user_for_selection(range(1, len(videos)+1))

    if selection is None:
        return None
    return videos[selection-1]


def search_metadata(track, search_format="{artist} - {track-name} lyrics", manual=False):
    # TODO: Clean this function
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
        youtube_videos = youtube_searcher.search(search_query)
        if not youtube_videos:
            raise NoYouTubeVideoError(
                'No videos found for the search query: "{}"'.format(search_query)
            )
        if manual:
            youtube_video = prompt_for_youtube_search_result(youtube_videos)
        else:
            youtube_video = youtube_videos.bestmatch()
        if youtube_video is None:
            metadata = spotify_metadata
        else:
            youtube_metadata = youtube.from_url(youtube_video["url"])
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
        youtube_videos = youtube_searcher.search(track)
        if not youtube_videos:
            raise NoYouTubeVideoError(
                'No videos found for the search query: "{}"'.format(track)
            )
        if manual:
            youtube_video = prompt_for_youtube_search_result(youtube_videos)
            if youtube_video is None:
                return
        else:
            youtube_video = youtube_videos.bestmatch()
        if youtube_video is None:
            metadata = spotify_metadata
        else:
            youtube_metadata = youtube.from_url(youtube_video["url"])
            metadata = spotdl.util.merge(
                youtube_metadata,
                spotify_metadata.join()
            )

    logger.debug("Matched with: {title} ({url}) [{duration}]".format(
        title=youtube_video["title"],
        url=youtube_video["url"],
        duration=youtube_video["duration"]
    ))

    metadata["lyrics"] = spotdl.util.ThreadWithReturnValue(
        target=search_lyrics,
        args=(lyric_query,)
    )

    metadata["lyrics"].start()
    return metadata


class Spotdl:
    def __init__(self, arguments):
        if "config" in arguments:
            # Make sure we set the base configuration from the config file if
            # the config file has been passed.
            config = spotdl.util.merge(
                spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"],
                spotdl.config.get_config(arguments["config"])
            )
        else:
            # If config file has not been passed, set the base configuration
            # to the default confguration.
            config = spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"]

        self.arguments = spotdl.util.merge(config, arguments)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def match_arguments(self):
        AuthorizeSpotify(
            client_id=self.arguments["spotify_client_id"],
            client_secret=self.arguments["spotify_client_secret"]
        )
        logger.debug("Received arguments: {}".format(self.arguments))

        # youtube_tools.set_api_key()
        if self.arguments["song"]:
            for track in self.arguments["song"]:
                if track == "-":
                    for line in sys.stdin:
                        self.download_track(
                            line,
                            self.arguments
                        )
                else:
                    self.download_track(track)
        elif self.arguments["list"]:
            if self.arguments["write_m3u"]:
                youtube_tools.generate_m3u(
                    track_file=self.arguments["list"]
                )
            else:
                list_download = {
                    "synchronous": self.download_tracks_from_file,
                    "threaded"  : self.download_tracks_from_file_threaded,
                }[self.arguments["processor"]]

                list_download(
                    self.arguments["list"],
                )
        elif self.arguments["playlist"]:
            spotify_tools.write_playlist(
                playlist_url=self.arguments["playlist"], text_file=self.arguments["write_to"]
            )
        elif self.arguments["album"]:
            spotify_tools.write_album(
                album_url=self.arguments["album"], text_file=self.arguments["write_to"]
            )
        elif self.arguments["all_albums"]:
            spotify_tools.write_all_albums_from_artist(
                artist_url=self.arguments["all_albums"], text_file=self.arguments["write_to"]
            )
        elif self.arguments["username"]:
            spotify_tools.write_user_playlist(
                username=self.arguments["username"], text_file=self.arguments["write_to"]
            )

    def download_track(self, track):
        track_splits = track.split(":")
        if len(track_splits) == 2:
            youtube_track, spotify_track = track_splits
        metadata = search_metadata(
            track,
            search_format=self.arguments["search_format"],
            manual=self.arguments["manual"],
        )
        if "streams" in metadata:
            self.download_track_from_metadata(metadata)

    def download_track_from_metadata(self, metadata):
        # TODO: Add `-m` flag
        track = Track(metadata, cache_albumart=(not self.arguments["no_metadata"]))
        stream = metadata["streams"].get(
            quality=self.arguments["quality"],
            preftype=self.arguments["input_ext"],
        )
        logger.debug("Stream information: {}".format(stream))

        Encoder = {
            "ffmpeg": EncoderFFmpeg,
            "avconv": EncoderAvconv,
        }.get(self.arguments["encoder"])

        if Encoder is None:
            output_extension = stream["encoding"]
        else:
            output_extension = self.arguments["output_ext"]

        filename = spotdl.metadata.format_string(
            self.arguments["output_file"],
            metadata,
            output_extension=output_extension,
            sanitizer=lambda s: spotdl.util.sanitize(
                s, spaces_to_underscores=self.arguments["no_spaces"]
            )
        )
        logger.info('Downloading to "{filename}"'.format(filename=filename))

        to_skip = self.arguments["dry_run"]
        if not to_skip and os.path.isfile(filename):
            if self.arguments["overwrite"] == "force":
                to_skip = False
                logger.info("A file with target filename already exists. Forcing overwrite.")
            elif self.arguments["overwrite"] == "prompt":
                overwrite_msg = "A file with target filename already exists. Overwrite? (y/N): "
                to_skip = not input(overwrite_msg).lower() == "y"
            else:
                logger.info("A file with target filename already exists. Skipping download.")
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

        if not self.arguments["no_metadata"]:
            track.metadata["lyrics"] = track.metadata["lyrics"].join()
            try:
                logger.info("Applying metadata")
                track.apply_metadata(filename, encoding=output_extension)
            except TypeError:
                logger.warning("Cannot apply metadata on provided output format.")

    def download_tracks_from_file(self, path):
        logger.info(
            "Checking and removing any duplicate tracks in {}.".format(path)
        )
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
                metadata = search_metadata(track, self.arguments["search_format"])
                log_track_query = str(number) + ". {artist} - {track-name}"
                logger.info(log_track_query)
                self.download_track_from_metadata(metadata)
            except (urllib.request.URLError, TypeError, IOError) as e:
                logger.exception(e.args[0])
                logger.warning("Failed. Will retry after other songs\n")
                tracks.append(track)
            except NoYouTubeVideoError:
                logger.warning("Failed. No YouTube video found.\n")
                pass
            else:
                if self.arguments["write_successful"]:
                    with open(self.arguments["write_successful"], "a") as fout:
                        fout.write(track)
            finally:
                with open(path, "w") as fout:
                    fout.writelines(tracks[number-1:])

    def download_tracks_from_file_threaded(self, path):
        # FIXME: Can we make this function cleaner?

        logger.info(
            "Checking and removing any duplicate tracks in {}.".format(path)
        )
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
                args=(next_track, self.arguments["search_format"])
            )
        }
        metadata["next_track"].start()
        while tracks_count > 0:
            metadata["current_track"] = metadata["next_track"].join()
            metadata["next_track"] = None
            try:
                print(tracks_count, file=sys.stderr)
                print(tracks, file=sys.stderr)
                if tracks_count > 1:
                    current_track = next_track
                    next_track = tracks.pop(0)
                    metadata["next_track"] = spotdl.util.ThreadWithReturnValue(
                        target=search_metadata,
                        args=(next_track, self.arguments["search_format"])
                    )
                    metadata["next_track"].start()

                log_track_query = str(current_iteration) + ". {artist} - {track-name}"
                logger.info(log_track_query)
                if metadata["current_track"] is None:
                    logger.warning("Something went wrong. Will retry after downloading remaining tracks.")
                    pass
                print(metadata["current_track"]["name"], file=sys.stderr)
                # self.download_track_from_metadata(metadata["current_track"])
            except (urllib.request.URLError, TypeError, IOError) as e:
                logger.exception(e.args[0])
                logger.warning("Failed. Will retry after other songs\n")
                tracks.append(current_track)
            else:
                tracks_count -= 1
                if self.arguments["write_successful"]:
                    with open(self.arguments["write_successful"], "a") as fout:
                        fout.write(current_track)
            finally:
                current_iteration += 1
                with open(path, "w") as fout:
                    fout.writelines(tracks)

