import appdirs

import argparse
import mimetypes
import os
import sys
import shutil

import spotdl.util
import spotdl.config

from collections.abc import Sequence
import logging
logger = logging.getLogger(__name__)

_LOG_LEVELS_STR = ("INFO", "WARNING", "ERROR", "DEBUG")


def log_leveller(log_level_str):
    logging_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
    log_level_str_index = _LOG_LEVELS_STR.index(log_level_str)
    logging_level = logging_levels[log_level_str_index]
    return logging_level


def override_config(config_file, parser, argv=None):
    """ Override default dict with config dict passed as comamnd line argument. """
    config_file = os.path.realpath(config_file)
    config = spotdl.util.merge(
        spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"],
        spotdl.config.get_config(config_file)
    )
    parser.set_defaults(**config)
    return parser.parse_args(argv)


def get_arguments(argv=None, base_config_file=spotdl.config.default_config_file):
    parser = argparse.ArgumentParser(
        description="Download and convert tracks from Spotify, Youtube etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    if base_config_file:
        config_dir = os.path.dirname(base_config_file)
        os.makedirs(os.path.dirname(base_config_file), exist_ok=True)
        config = spotdl.util.merge(
            spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"],
            spotdl.config.get_config(base_config_file)
        )
    else:
        config = spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"]

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-s",
        "--song",
        nargs="+",
        help="download track(s) by spotify link or name"
    )
    group.add_argument(
        "-l",
        "--list",
        help="download tracks from a file (WARNING: this file will be modified!)"
    )
    group.add_argument(
        "-p",
        "--playlist",
        help="load tracks from playlist URL into <playlist_name>.txt or "
             "if `--write-to=<path/to/file.txt>` has been passed",
    )
    group.add_argument(
        "-b",
        "--album",
        help="load tracks from album URL into <album_name>.txt or if "
             "`--write-to=<path/to/file.txt>` has been passed"
    )
    group.add_argument(
        "-ab",
        "--all-albums",
        help="load all tracks from artist URL into <artist_name>.txt "
             "or if `--write-to=<path/to/file.txt>` has been passed"
    )
    group.add_argument(
        "-u",
        "--username",
        help="load tracks from user's playlist into <playlist_name>.txt "
             "or if `--write-to=<path/to/file.txt>` has been passed"
    )

    parser.add_argument(
        "--write-m3u",
        help="generate an .m3u playlist file with youtube links given "
             "a text file containing tracks",
        action="store_true",
    )
    parser.add_argument(
        "-m",
        "--manual",
        default=config["manual"],
        help="choose the track to download manually from a list of matching tracks",
        action="store_true",
    )
    parser.add_argument(
        "-nm",
        "--no-metadata",
        default=config["no_metadata"],
        help="do not embed metadata in tracks",
        action="store_true",
    )
    parser.add_argument(
        "-ne",
        "--no-encode",
        default=config["no-encode"],
        action="store_true",
        help="do not encode media using FFmpeg",
    )
    parser.add_argument(
        "--overwrite",
        default=config["overwrite"],
        choices={"prompt", "force", "skip"},
        help="change the overwrite policy",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default=config["quality"],
        choices={"best", "worst"},
        help="preferred audio quality",
    )
    parser.add_argument(
        "-i",
        "--input-ext",
        default=config["input_ext"],
        choices={"automatic", "m4a", "opus"},
        help="preferred input format",
    )
    parser.add_argument(
        "-o",
        "--output-ext",
        default=config["output_ext"],
        choices={"mp3", "m4a", "flac"},
        help="preferred output format",
    )
    parser.add_argument(
        "--write-to",
        default=config["write_to"],
        help="write tracks from Spotify playlist, album, etc. to this file",
    )
    parser.add_argument(
        "-f",
        "--output-file",
        default=config["output_file"],
        help="path where to write the downloaded track to, special tags "
        "are to be surrounded by curly braces. Possible tags: "
        # "{}".format([spotdl.util.formats[x] for x in spotdl.util.formats]),
    )
    parser.add_argument(
        "--trim-silence",
        default=config["trim_silence"],
        help="remove silence from the start of the audio",
        action="store_true",
    )
    parser.add_argument(
        "-sf",
        "--search-format",
        default=config["search_format"],
        help="search format to search for on YouTube, special tags "
        "are to be surrounded by curly braces. Possible tags: "
        # "{}".format([spotdl.util.formats[x] for x in spotdl.util.formats]),
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        default=config["dry_run"],
        help="show only track title and YouTube URL, and then skip "
        "to the next track (if any)",
        action="store_true",
    )
    parser.add_argument(
        "-mo",
        "--music-videos-only",
        default=config["music_videos_only"],
        help="search only for music videos on Youtube (works only "
        "when YouTube API key is set)",
        action="store_true",
    )
    # parser.add_argument(
    #     "--processor",
    #     default=config["processor"],
    #     choices={"synchronous", "threaded"},
    #     help='list downloading strategy: - "synchronous" downloads '
    #     'tracks one-by-one. - "threaded" (highly experimental at the '
    #     'moment! expect it to slash & burn) pre-fetches the next '
    #     'track\'s metadata for more efficient downloading'
    # )
    parser.add_argument(
        "-ns",
        "--no-spaces",
        default=config["no_spaces"],
        help="replace spaces with underscores in file names",
        action="store_true",
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        default=config["log_level"],
        choices=_LOG_LEVELS_STR,
        type=str.upper,
        help="set log verbosity",
    )
    parser.add_argument(
        "-yk",
        "--youtube-api-key",
        default=config["youtube_api_key"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-sk",
        "--skip",
        default=config["skip"],
        help="path to file containing tracks to skip",
    )
    parser.add_argument(
        "-w",
        "--write-successful",
        default=config["write_successful"],
        help="path to file to write successful tracks to",
    )
    parser.add_argument(
        "-sci",
        "--spotify-client-id",
        default=config["spotify_client_id"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-scs",
        "--spotify-client-secret",
        default=config["spotify_client_secret"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-c",
        "--config",
        default=base_config_file,
        help="path to custom config.yml file"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {}".format(spotdl.__version__),
    )

    parsed = parser.parse_args(argv)

    if base_config_file and parsed.config is not None:
        parsed = override_config(parsed.config, parser)

    parsed.log_level = log_leveller(parsed.log_level)
    # TODO: Remove this line once we can experiement with other
    # download processors (such as "threaded").
    parsed.processor = "synchronous"
    return Arguments(parser, parsed)


class Arguments:
    def __init__(self, parser, parsed):
        self.parser = parser
        self.parsed = parsed

    def run_errands(self):
        if (self.parsed.list
            and not mimetypes.MimeTypes().guess_type(self.parsed.list)[0] == "text/plain"
        ):
            self.parser.error(
                "{0} is not of a valid argument to --list, argument must be plain text file.".format(
                    self.parsed.list
                )
            )

        if self.parsed.write_m3u and not self.parsed.list:
            self.parser.error("--write-m3u can only be used with --list")

        if self.parsed.write_to and not (
            self.parsed.playlist or self.parsed.album or self.parsed.all_albums or self.parsed.username
        ):
            self.parser.error(
                "--write-to can only be used with --playlist, --album, --all-albums, or --username"
            )

        ffmpeg_exists = shutil.which("ffmpeg")
        if not ffmpeg_exists:
            logger.warn("FFmpeg was not found in PATH. Will not re-encode media to specified output format.")
            self.parsed.output_ext = self.parsed.input_ext

        if self.parsed.output_file == "-" and self.parsed.no_metadata is False:
            logger.warn(
                "Cannot write metadata when target is STDOUT. Pass "
                "--no-metadata explicitly to hide this warning."
            )
            self.parsed.no_metadata = True
        elif os.path.isdir(self.parsed.output_file):
            adjusted_output_file = os.path.join(
                self.parsed.output_file,
                self.parser.get_default("output_file")
            )
            logger.warn(
                "Given output file is a directory. Will download tracks "
                "in this directory with their filename as per the default "
                "file format. Pass '--output-file=\"{}\"' to hide this "
                "warning.".format(
                    adjusted_output_file
                )
            )
            self.parsed.output_file = adjusted_output_file

        # We're done dealing with configuration file here and don't need to use it later
        del self.parsed.config

        return self.parsed.__dict__

