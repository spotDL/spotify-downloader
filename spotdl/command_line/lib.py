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

from spotdl.command_line.exceptions import NoYouTubeVideoFoundError
from spotdl.command_line.exceptions import NoYouTubeVideoMatchError

from spotdl.helpers.spotify import SpotifyHelpers

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
    max_index_length = len(str(len(videos)))
    max_title_length = max(len(v["title"]) for v in videos)
    print(" 0. Skip downloading this track", file=sys.stderr)
    for index, video in enumerate(videos, 1):
        vid_details = "{index:>{max_index}}. {title:<{max_title}} {url} [{duration}]".format(
            index=index,
            max_index=max_index_length,
            title=video["title"],
            max_title=max_title_length,
            url=video["url"],
            duration=video["duration"],
        )
        print(vid_details, file=sys.stderr)
    print("", file=sys.stderr)

    selection = spotdl.util.prompt_user_for_selection(range(1, len(videos)+1))

    if selection is None:
        return None
    return videos[selection-1]


def search_metadata(track, search_format="{artist} - {track-name} lyrics", manual=False):
    # TODO: Clean this function
    youtube = ProviderYouTube()
    youtube_searcher = YouTubeSearch()

    if spotdl.util.is_spotify(track):
        logger.debug("Input track is a Spotify URL.")
        spotify = ProviderSpotify()
        spotify_metadata = spotify.from_url(track)
        lyric_query = spotdl.metadata.format_string(
            "{artist} - {track-name}",
            spotify_metadata,
        )
        search_query = spotdl.metadata.format_string(search_format, spotify_metadata)
        youtube_videos = youtube_searcher.search(search_query)
        if not youtube_videos:
            raise NoYouTubeVideoFoundError(
                'YouTube returned no videos for the search query "{}".'.format(search_query)
            )
        if manual:
            youtube_video = prompt_for_youtube_search_result(youtube_videos)
        else:
            youtube_video = youtube_videos.bestmatch()

        if youtube_video is None:
            raise NoYouTubeVideoMatchError(
                'No matching videos found on YouTube for the search query "{}".'.format(
                    search_query
                )
            )

        youtube_metadata = youtube.from_url(youtube_video["url"])
        metadata = spotdl.util.merge(
            youtube_metadata,
            spotify_metadata
        )

    elif spotdl.util.is_youtube(track):
        logger.debug("Input track is a YouTube URL.")
        metadata = youtube.from_url(track)
        lyric_query = spotdl.metadata.format_string(
            "{artist} - {track-name}",
            metadata,
        )

    else:
        logger.debug("Input track is a search query.")
        search_query = track
        lyric_query = search_query
        spotify_metadata = spotdl.util.ThreadWithReturnValue(
            target=search_metadata_on_spotify,
            args=(search_query,)
        )
        spotify_metadata.start()
        youtube_videos = youtube_searcher.search(search_query)
        if not youtube_videos:
            raise NoYouTubeVideoFoundError(
                'YouTube returned no videos for the search query "{}".'.format(search_query)
            )
        if manual:
            youtube_video = prompt_for_youtube_search_result(youtube_videos)
        else:
            youtube_video = youtube_videos.bestmatch()

        if youtube_video is None:
            raise NoYouTubeVideoMatchError(
                'No apparent matching videos found on YouTube for the search query "{}"'.format(
                    search_query
                )
            )

        youtube_metadata = youtube.from_url(youtube_video["url"])
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
        spotify_tools = SpotifyHelpers()
        # youtube_tools.set_api_key()
        logger.debug("Received arguments:\n{}".format(self.arguments))

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
            playlist = spotify_tools.fetch_playlist(self.arguments["playlist"])
            spotify_tools.write_playlist_tracks(playlist, self.arguments["write_to"])
        elif self.arguments["album"]:
            album = spotify_tools.fetch_album(self.arguments["album"])
            spotify_tools.write_album_tracks(album, self.arguments["write_to"])
        elif self.arguments["all_albums"]:
            albums = spotify_tools.fetch_albums_from_artist(self.arguments["all_albums"])
            spotify_tools.write_all_albums(albums, self.arguments["write_to"])
        elif self.arguments["username"]:
            playlist_url = spotify_tools.prompt_for_user_playlist(self.arguments["username"])
            playlist = spotify_tools.fetch_playlist(playlist_url)
            spotify_tools.write_playlist_tracks(playlist, self.arguments["write_to"])

    def download_track(self, track):
        logger.info('Downloading "{}"'.format(track))
        try:
            metadata = search_metadata(
                track,
                search_format=self.arguments["search_format"],
                manual=self.arguments["manual"],
            )
        except (NoYouTubeVideoFoundError, NoYouTubeVideoMatchError) as e:
            logger.error(e.args[0])
        else:
            self.download_track_from_metadata(metadata)

    def should_we_overwrite_existing_file(self):
        if self.arguments["overwrite"] == "force":
            logger.info("Forcing overwrite on existing file.")
            to_overwrite = True
        elif self.arguments["overwrite"] == "prompt":
            to_overwrite = input("Overwrite? (y/N): ").lower() == "y"
        else:
            logger.info("Not overwriting existing file.")
            to_overwrite = False

        return to_overwrite

    def download_track_from_metadata(self, metadata):
        track = Track(metadata, cache_albumart=(not self.arguments["no_metadata"]))
        stream = metadata["streams"].get(
            quality=self.arguments["quality"],
            preftype=self.arguments["input_ext"],
        )

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

        to_skip_download = self.arguments["dry_run"]
        if os.path.isfile(filename):
            logger.info('A file with name "{filename}" already exists.'.format(
                filename=filename
            ))
            to_skip_download = to_skip_download \
                or not self.should_we_overwrite_existing_file()

        if to_skip_download:
            logger.debug("Skip track download.")
            return

        logger.info('Downloading to "{filename}"'.format(filename=filename))
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
            self.apply_metadata(track, filename, output_extension)

    def apply_metadata(self, track, filename, encoding):
        track.metadata["lyrics"] = track.metadata["lyrics"].join()
        logger.info("Applying metadata")
        try:
            track.apply_metadata(filename, encoding=encoding)
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

        print("", file=sys.stderr)

        for number, track in enumerate(tracks, 1):
            try:
                log_track_query = '{position}. Downloading "{track}"'.format(
                    position=number,
                    track=track
                )
                logger.info(log_track_query)
                metadata = search_metadata(track, self.arguments["search_format"])
                self.download_track_from_metadata(metadata)
            except (urllib.request.URLError, TypeError, IOError) as e:
                logger.exception(e.args[0])
                logger.warning(
                    "Failed to download current track due to possible network issue. "
                    "Will retry after other songs."
                )
                tracks.append(track)
            except (NoYouTubeVideoFoundError, NoYouTubeVideoMatchError) as e:
                logger.error(e.args[0])
            else:
                if self.arguments["write_successful"]:
                    with open(self.arguments["write_successful"], "a") as fout:
                        fout.write(track)
            finally:
                with open(path, "w") as fout:
                    fout.writelines(tracks[number-1:])
                print("", file=sys.stderr)

    def download_tracks_from_file_threaded(self, path):
        # FIXME: Can we make this function cleaner?

        logger.info(
            "Checking and removing any duplicate tracks in {}.\n".format(path)
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
                print("", file=sys.stderr)
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

