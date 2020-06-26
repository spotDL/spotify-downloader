from spotdl.metadata.providers import ProviderSpotify
from spotdl.metadata.providers import ProviderYouTube
from spotdl.metadata.providers import YouTubeSearch
from spotdl.metadata.embedders import EmbedderDefault
from spotdl.metadata.exceptions import SpotifyMetadataNotFoundError
from spotdl.metadata.exceptions import BadMediaFileError
import spotdl.metadata

from spotdl.lyrics.providers import LyricWikia
from spotdl.lyrics.providers import Genius
from spotdl.lyrics.exceptions import LyricsNotFoundError

from spotdl.encode.encoders import EncoderFFmpeg

from spotdl.authorize.services import AuthorizeSpotify

from spotdl.track import Track
import spotdl.util
import spotdl.config

from spotdl.command_line.exceptions import NoYouTubeVideoFoundError
from spotdl.command_line.exceptions import NoYouTubeVideoMatchError
from spotdl.metadata_search import MetadataSearch

from spotdl.helpers.spotify import SpotifyHelpers
from spotdl.command_line.arguments import ArgumentHandler
import spotdl.helpers.exceptions

import sys
import os
import urllib.request

import logging
logger = logging.getLogger(__name__)

class Spotdl:
    """
    This class is directly involved with the command-line interface
    of the tool. It allows downloading of tracks, writing M3U
    playlists, and providers other useful methods.

    Parameters
    ----------
    args: `dict`
        A dictionary containing arguments. These passed arguments will
        override the default arguments used by the tool. In case an
        invalid combination of arguments is passed, an `ArgumentError`
        will be raised indicating the reason.

    Examples
    --------
    + To download a track:

        >>> from spotdl.command_line.core import Spotdl
        >>> args = {
        ...     "song": ["https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l",],
        ... }
        >>> with Spotdl(args) as spotdl_handler:
        ...     spotdl_handler.match_arguments()

    + To download tracks without metadata:

        >>> from spotdl.command_line.core import Spotdl
        >>> args = {
        ...     "song": [
        ...         "https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l",
        ...         "ncs spectre"
        ...     ],
        ...     "no_metadata": True,
        ... }
        >>> with Spotdl(args) as spotdl_handler:
        ...     spotdl_handler.match_arguments()

    Similary, you can pass additional arguments (refer to the config fiile
    to know what all arguments are supported).

    + To download tracks from file:

        >>> from spotdl.command_line.core import Spotdl
        >>> args = {
        ...     "list": "file_with_tracks.txt",
        ... }
        >>> with Spotdl(args) as spotdl_handler:
        ...     spotdl_handler.match_arguments()

    + You can also the call the download methods later on as per need:

        >>> from spotdl.command_line.core import Spotdl
        >>> args = {
        ...     "no_encode": True,
        ... }
        >>> with Spotdl(args) as spotdl_handler:
        ...     spotdl_handler.download_track("https://open.spotify.com/track/2lfPecqFbH8X4lHSpTxt8l")
        ...     print("Downloading 2nd track.")
        ...     spotdl_handler.download_track("ncs spectre")
        ...     print("Downloading from file.")
        ...     spotdl_handler.download_tracks_from_file("file_full_of_tracks.txt")

    Using `with` is optional. You can also directly create :class:`Spotdl` objects:

        >>> from spotdl.command_line.core import Spotdl
        >>> args = {
        ...     "no_encode": True,
        ... }
        >>> spotdl_handler = Spotdl(args)
        >>> spotdl_handler.download_track("ncs spectre")
    """

    def __init__(self, args={}):
        argument_handler = ArgumentHandler(args)
        arguments = argument_handler.run_errands()
        AuthorizeSpotify(
            client_id=arguments["spotify_client_id"],
            client_secret=arguments["spotify_client_secret"]
        )
        self.arguments = arguments

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def match_arguments(self):
        """
        This is the main entry method that performs relevant work based
        on whatever arguments have been passed.
        """

        logger.debug("Received arguments:\n{}".format(self.arguments))

        if self.arguments.get("remove_config"):
            self.remove_saved_config()
            return 0
        self.save_default_config()

        spotify_tools = SpotifyHelpers()
        if self.arguments["song"]:
            for track in self.arguments["song"]:
                logger.info('Downloading "{}"'.format(track))
                if track == "-":
                    for line in sys.stdin:
                        self.download_track(
                            line.strip(),
                        )
                else:
                    self.download_track(track)
        elif self.arguments["list"]:
            if self.arguments["write_m3u"]:
                self.write_m3u(
                    self.arguments["list"],
                    self.arguments["write_to"]
                )
            else:
                list_download = {
                    "synchronous": self.download_tracks_from_file,
                    # "threaded"  : self.download_tracks_from_file_threaded,
                }[self.arguments["processor"]]

                list_download(
                    self.arguments["list"],
                )
        elif self.arguments["playlist"]:
            try:
                playlist = spotify_tools.fetch_playlist(self.arguments["playlist"])
            except spotdl.helpers.exceptions.PlaylistNotFoundError:
                return spotdl.command_line.exitcodes.URI_NOT_FOUND_ERROR
            else:
                spotify_tools.write_playlist_tracks(playlist, self.arguments["write_to"])
        elif self.arguments["album"]:
            try:
                album = spotify_tools.fetch_album(self.arguments["album"])
            except spotdl.helpers.exceptions.AlbumNotFoundError:
                return spotdl.command_line.exitcodes.URI_NOT_FOUND_ERROR
            else:
                spotify_tools.write_album_tracks(album, self.arguments["write_to"])
        elif self.arguments["all_albums"]:
            try:
                albums = spotify_tools.fetch_albums_from_artist(self.arguments["all_albums"])
            except spotdl.helpers.exceptions.ArtistNotFoundError:
                return spotdl.command_line.exitcodes.URI_NOT_FOUND_ERROR
            else:
                spotify_tools.write_all_albums(albums, self.arguments["write_to"])
        elif self.arguments["username"]:
            try:
                playlist_url = spotify_tools.prompt_for_user_playlist(self.arguments["username"])
            except spotdl.helpers.exceptions.UserNotFoundError:
                return spotdl.command_line.exitcodes.URI_NOT_FOUND_ERROR
            else:
                playlist = spotify_tools.fetch_playlist(playlist_url)
                spotify_tools.write_playlist_tracks(playlist, self.arguments["write_to"])

    def save_config(self, config_file=spotdl.config.DEFAULT_CONFIG_FILE, config=spotdl.config.DEFAULT_CONFIGURATION):
        """
        Writes provided configuration to config file.

        Parameters
        ----------
        config_file: `str`
            Path to write the configuration to.

        config: `dict`
            A `dict` consisting of configuration options.
        """

        config_dir = os.path.dirname(config_file)
        os.makedirs(config_dir, exist_ok=True)
        logger.info('Writing configuration to "{0}":'.format(config_file))
        spotdl.config.dump_config(config_file=config_file, config=spotdl.config.DEFAULT_CONFIGURATION)
        config = spotdl.config.dump_config(config=spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"])
        for line in config.split("\n"):
            if line.strip():
                logger.info(line.strip())
        logger.info(
            "Please note that command line arguments have higher priority "
            "than their equivalents in the configuration file.\n"
        )

    def save_default_config(self):
        """
        Writes the default configuration to the default config file if
        it does not already exist.
        """

        if not os.path.isfile(spotdl.config.DEFAULT_CONFIG_FILE):
            self.save_config()

    def remove_saved_config(self, config_file=spotdl.config.DEFAULT_CONFIG_FILE):
        """
        Removes the config file if it exists.

        Parameters
        ----------
        config_file: `str`
            Path to configuration file.
        """

        if os.path.isfile(spotdl.config.DEFAULT_CONFIG_FILE):
            logger.info('Removing "{}".'.format(spotdl.config.DEFAULT_CONFIG_FILE))
            os.remove(spotdl.config.DEFAULT_CONFIG_FILE)
        else:
            logger.info('File does not exist: "{}".'.format(spotdl.config.DEFAULT_CONFIG_FILE))

    def write_m3u(self, track_file, target_path=None):
        """
        Generates an M3U playlist from a given track file and writes it
        to a target file.

        Parameters
        ----------
        track_file: `str`
            Path to file consisting of tracks.

        target_path:`str`
            Path to file to write the M3U playlist to. `None` indicates
            to automatically determine it from the `track_file`.
        """

        with open(track_file, "r") as fin:
            tracks = fin.read().splitlines()

        logger.info(
            "Checking and removing any duplicate tracks in {}.".format(track_file)
        )
        # Remove duplicates and empty elements
        # Also strip whitespaces from elements (if any)
        tracks = spotdl.util.remove_duplicates(
            tracks,
            condition=lambda x: x,
            operation=str.strip
        )

        if target_path is None:
            target_path = "{}.m3u".format(track_file.split(".")[0])

        total_tracks = len(tracks)
        logger.info("Generating {0} from {1} YouTube URLs.".format(target_path, total_tracks))
        write_to_stdout = target_path == "-"
        m3u_headers = "#EXTM3U\n\n"
        if write_to_stdout:
            sys.stdout.write(m3u_headers)
        else:
            with open(target_path, "w") as output_file:
                output_file.write(m3u_headers)

        videos = []
        for n, track in enumerate(tracks, 1):
            search_metadata = MetadataSearch(
                track,
                lyrics=not self.arguments["no_metadata"],
                yt_search_format=self.arguments["search_format"],
                yt_manual=self.arguments["manual"]
            )
            try:
                video = search_metadata.best_on_youtube_search()
            except (NoYouTubeVideoFoundError, NoYouTubeVideoMatchError) as e:
                logger.error(e.args[0])
            else:
                logger.info(
                    "Matched track {0}/{1} ({2})".format(
                        str(n).zfill(len(str(total_tracks))),
                        total_tracks,
                        video["url"],
                    )
                )
                m3u_key = "#EXTINF:{duration},{title}\n{youtube_url}\n".format(
                    duration=spotdl.util.get_sec(video["duration"]),
                    title=video["title"],
                    youtube_url=video["url"],
                )
                logger.debug(m3u_key.strip())
                if write_to_stdout:
                    sys.stdout.write(m3u_key)
                else:
                    with open(target_path, "a") as output_file:
                        output_file.write(m3u_key)

    def download_track(self, track):
        """
        Downloads a track given a track query, Spotify URI or a YouTube
        URI.

        Parameters
        ----------
        track: `str`
            A Spotify URI, YouTube URI or a query.
        """

        subtracks = track.split("::")
        download_track = subtracks[0]
        custom_metadata_track = len(subtracks) > 1
        if custom_metadata_track:
            metadata_track = subtracks[1]
        else:
            metadata_track = download_track

        search_metadata = MetadataSearch(
            metadata_track,
            lyrics=not self.arguments["no_metadata"],
            yt_search_format=self.arguments["search_format"],
            yt_manual=self.arguments["manual"]
        )

        def threaded_metadata():
            try:
                if self.arguments["no_metadata"]:
                    metadata = search_metadata.on_youtube()
                else:
                    metadata = search_metadata.on_youtube_and_spotify()
            except (NoYouTubeVideoFoundError, NoYouTubeVideoMatchError) as e:
                logger.error(e.args[0])
            else:
                return metadata

        metadata = spotdl.util.ThreadWithReturnValue(target=threaded_metadata)
        metadata.start()
        if not custom_metadata_track:
            metadata = metadata.join()
            if not metadata:
                return
            return self.download_track_from_metadata(metadata)

        search_metadata = MetadataSearch(
            download_track,
            lyrics=False,
            yt_search_format=self.arguments["search_format"],
            yt_manual=self.arguments["manual"]
        )
        try:
            download_track_metadata = search_metadata.on_youtube()
        except (NoYouTubeVideoFoundError, NoYouTubeVideoMatchError) as e:
            logger.error(e.args[0])
            return

        metadata = metadata.join()
        if not metadata:
            return

        logger.info('Overriding metadata as per passed metadata-track'.format(metadata_track))
        metadata["streams"] = download_track_metadata["streams"]
        return self.download_track_from_metadata(metadata)

    def should_we_overwrite_existing_file(self, overwrite):
        """
        Returns a `boolean` based on the given value of `overwrite`
        parameter, where `overwrite` is one of `force`, `skip` or
        `prompt`. The method will prompt for input via STDIN if the
        value of `overwrite` is `prompt`.

        Parameters
        ----------
        overwrite: `str`
            One of `force`, `skip` or `prompt`.

        Returns
        -------
        to_overwrite: `bool`
            `True` or `False` depending on whether the existing file
            should be overwritten or not.
        """

        if overwrite == "force":
            logger.info("Forcing overwrite on existing file.")
            to_overwrite = True
        elif overwrite == "prompt":
            to_overwrite = input("Overwrite? (y/N): ").lower() == "y"
        else:
            logger.info("Not overwriting existing file.")
            to_overwrite = False

        return to_overwrite

    def download_track_from_metadata(self, metadata):
        """
        Downloads track audio from the provided metadata.

        Parameters
        ----------
        metadata: `dict`
            A `dict` consisting of metadata in standardized form.
        """

        track = Track(metadata, cache_albumart=(not self.arguments["no_metadata"]))
        stream = metadata["streams"].get(
            quality=self.arguments["quality"],
            preftype=self.arguments["input_ext"],
        )
        if stream is None:
            logger.error('No matching streams found for given input format: "{}".'.format(
                self.arguments["input_ext"]
            ))
            return

        if self.arguments["no_encode"]:
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
        download_to_stdout = filename == "-"
        temp_filename = filename if download_to_stdout else filename + ".temp"

        to_skip_download = self.arguments["dry_run"]
        if os.path.isfile(filename):
            logger.info('A file with name "{filename}" already exists.'.format(
                filename=filename
            ))
            to_skip_download = to_skip_download \
                or not self.should_we_overwrite_existing_file(self.arguments["overwrite"])

        if to_skip_download:
            logger.debug("Skip track download.")
            return

        if not self.arguments["no_metadata"]:
            metadata["lyrics"].start()

        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

        logger.info('Downloading to "{filename}"'.format(filename=filename))
        if self.arguments["no_encode"]:
            track.download(stream, temp_filename)
        else:
            encoder = EncoderFFmpeg()
            if self.arguments["trim_silence"]:
                encoder.set_trim_silence()
            track.download_while_re_encoding(
                stream,
                temp_filename,
                target_encoding=output_extension,
                encoder=encoder,
            )

        if not self.arguments["no_metadata"]:
            logger.info("Applying metadata")
            track.metadata["lyrics"] = track.metadata["lyrics"].join()
            self.apply_metadata(track, temp_filename, output_extension)

        if not download_to_stdout:
            logger.debug('Renaming "{temp_filename}" to "{filename}".'.format(
                temp_filename=temp_filename, filename=filename
            ))
            os.rename(temp_filename, filename)

        return filename

    def apply_metadata(self, track, filename, encoding=None):
        """
        Applies metadata to a given track. This is the same as calling
        :func:`spotdl.track.Track.apply_metadata` except this will
        only raise a warning if an unsupported output format has
        been passed unlike :func:`spotdl.track.Track.apply_metadata`
        which would raise a `TypeError`.

        Parameters
        ----------
        track: :class:`spotdl.track.Track` object
            A corresponding :class:`spotdl.track.Track` object.

        filename: `str`
            A filename where the audio file exists on the disk.

        encoding: `str`, `None`
            An encoding of `None` indicates to automatically determine
            it from the filename.
        """

        try:
            track.apply_metadata(filename, encoding=encoding)
        except MediaFileError:
            logger.warning("Cannot apply metadata on provided output format.")

    def strip_and_filter_duplicates(self, elements):
        """
        Removes any duplicate elements from the given list and strips
        any whitespaces from elements.

        Parameters
        ----------
        elements: `list`
            A list of elements.

        Returns
        -------
        filtered_elements: `list`
            A list of filtered elements.
        """

        filtered_elements = spotdl.util.remove_duplicates(
            elements,
            condition=lambda x: x,
            operation=str.strip
        )
        return filtered_elements

    def filter_against_skip_file(self, items, skip_file):
        """
        Removes the element from `items` if there already exists the
        same element in `skip_file`.

        Parameters
        ----------
        items: `list`
            A list of elements.

        skip_file: `str`
            Path to file.

        Returns
        -------
        filtered_items: `list`
            ``items`` but with duplicates removed.
        """

        skip_items = spotdl.util.readlines_from_nonbinary_file(skip_file)
        filtered_skip_items = self.strip_and_filter_duplicates(skip_items)
        filtered_items = [item for item in items if not item in filtered_skip_items]
        return filtered_items

    def download_tracks_from_file(self, path):
        """
        Download tracks from file.

        Parameters
        ----------
        path: `str`
            Path to the file consisting of tracks.
        """

        logger.info(
            'Checking and removing any duplicate tracks in "{}".'.format(path)
        )
        tracks = spotdl.util.readlines_from_nonbinary_file(path)
        tracks = self.strip_and_filter_duplicates(tracks)

        if self.arguments["skip_file"]:
            len_tracks_before = len(tracks)
            tracks = self.filter_against_skip_file(tracks, self.arguments["skip_file"])
            logger.info("Skipping {} tracks due to matches in skip file.".format(
                len_tracks_before - len(tracks))
            )
        # Overwrite file
        spotdl.util.writelines_to_nonbinary_file(path, tracks)

        logger.info(
            "Downloading {n} tracks.\n".format(n=len(tracks))
        )

        for position, track in enumerate(tracks, 1):
            log_track_query = '{position}. Downloading "{track}"'.format(
                position=position,
                track=track
            )
            logger.info(log_track_query)
            try:
                self.download_track(track)
            except (urllib.request.URLError, TypeError, IOError) as e:
                logger.exception(e.args[0])
                logger.warning(
                    "Failed to download current track due to possible network issue. "
                    "Will retry after other songs."
                )
                tracks.append(track)
            except KeyboardInterrupt:
                # The current track hasn't been downloaded completely.
                # Make sure we continue from here the next the program runs.
                tracks.insert(0, track)
                raise
            else:
                if self.arguments["write_successful_file"]:
                    with open(self.arguments["write_successful_file"], "a") as fout:
                        fout.write("{}\n".format(track))
            finally:
                spotdl.util.writelines_to_nonbinary_file(path, tracks[position:])
                print("", file=sys.stderr)

    """
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
                if self.arguments["write_sucessful_file"]:
                    with open(self.arguments["write_sucessful_file"], "a") as fout:
                        fout.write(current_track)
            finally:
                current_iteration += 1
                with open(path, "w") as fout:
                    fout.writelines(tracks)
    """

