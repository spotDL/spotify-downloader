import appdirs

import argparse
import mimetypes
import os
import sys
import shutil

from spotdl.command_line.exceptions import ArgumentError
import spotdl.util
import spotdl.config

from collections.abc import Sequence
import logging
logger = logging.getLogger(__name__)


_LOG_LEVELS = {
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "DEBUG": logging.DEBUG,
}

if os.path.isfile(spotdl.config.DEFAULT_CONFIG_FILE):
    saved_config = spotdl.config.read_config(spotdl.config.DEFAULT_CONFIG_FILE)
else:
    saved_config = {"spotify-downloader": {}}

_CONFIG_BASE = spotdl.util.merge_copy(
    spotdl.config.DEFAULT_CONFIGURATION,
    saved_config,
)


def get_arguments(config_base=_CONFIG_BASE):
    parser = argparse.ArgumentParser(
        description="Download and convert tracks from Spotify, Youtube, etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    defaults = config_base["spotify-downloader"]

    to_remove_config = "--remove-config" in sys.argv[1:]
    if not to_remove_config and "download-only-metadata" in defaults:
        raise ArgumentError(
            "The default configuration file currently set is not suitable for spotdl>=2.0.0.\n"
            "You need to remove your previous `config.yml` due to breaking changes\n"
            "introduced in v2.0.0, new options being added, and old ones being removed\n"
            "You may want to first backup your old configuration for reference. You can\n"
            "then remove your current configuration by running:\n"
            "```\n"
            "$ spotdl --remove-config\n"
            "```\n"
            "spotdl will automatically generate a new configuration file on the next run.\n"
            "You can then replace the appropriate fields in the newly generated\n"
            "configuration file by referring to your old configuration file.\n\n"
            "For the list of OTHER BREAKING CHANGES and release notes check out:\n"
            "https://github.com/ritiek/spotify-downloader/releases/tag/v2.0.0"
        )

    possible_special_tags = (
        "{track-name}",
        "{artist}",
        "{album}",
        "{album-artist}",
        "{genre}",
        "{disc-number}",
        "{duration}",
        "{year}",
        "{original-date}",
        "{track-number}",
        "{total-tracks}",
        "{isrc}",
        "{track-id}",
        "{output-ext}",
    )

    # `--remove-config` does not require the any of the group arguments to be passed.
    group = parser.add_mutually_exclusive_group(required=not to_remove_config)

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
        "-a",
        "--album",
        help="load tracks from album URL into <album_name>.txt or if "
             "`--write-to=<path/to/file.txt>` has been passed"
    )
    group.add_argument(
        "-aa",
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
        default=defaults["manual"],
        help="choose the track to download manually from a list of matching tracks",
        action="store_true",
    )
    parser.add_argument(
        "-nm",
        "--no-metadata",
        default=defaults["no_metadata"],
        help="do not embed metadata in tracks",
        action="store_true",
    )
    parser.add_argument(
        "-ne",
        "--no-encode",
        default=defaults["no_encode"],
        action="store_true",
        help="do not encode media using FFmpeg",
    )
    parser.add_argument(
        "--overwrite",
        default=defaults["overwrite"],
        choices={"prompt", "force", "skip"},
        help="change the overwrite policy",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default=defaults["quality"],
        choices={"best", "worst"},
        help="preferred audio quality",
    )
    parser.add_argument(
        "-i",
        "--input-ext",
        default=defaults["input_ext"],
        choices={"automatic", "m4a", "opus"},
        help="preferred input format",
    )
    parser.add_argument(
        "-o",
        "--output-ext",
        default=defaults["output_ext"],
        choices={"mp3", "m4a", "flac"},
        help="preferred output format",
    )
    parser.add_argument(
        "--write-to",
        default=defaults["write_to"],
        help="write tracks from Spotify playlist, album, etc. to this file",
    )
    parser.add_argument(
        "-f",
        "--output-file",
        default=defaults["output_file"],
        help="path where to write the downloaded track to, special tags "
        "are to be surrounded by curly braces. Possible tags: {}".format(
            possible_special_tags
        )
    )
    parser.add_argument(
        "--trim-silence",
        default=defaults["trim_silence"],
        help="remove silence from the start of the audio",
        action="store_true",
    )
    parser.add_argument(
        "-sf",
        "--search-format",
        default=defaults["search_format"],
        help="search format to search for on YouTube, special tags "
        "are to be surrounded by curly braces. Possible tags: {}".format(
            possible_special_tags
        )
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        default=defaults["dry_run"],
        help="show only track title and YouTube URL, and then skip "
        "to the next track (if any)",
        action="store_true",
    )
    parser.add_argument(
        "--processor",
        default="synchronous",
        choices={"synchronous", "threaded"},
        # help='list downloading strategy: - "synchronous" downloads '
        # 'tracks one-by-one. - "threaded" (highly experimental at the '
        # 'moment! expect it to slash & burn) pre-fetches the next '
        # 'track\'s metadata for more efficient downloading'
        # XXX: Still very experimental to be exposed
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ns",
        "--no-spaces",
        default=defaults["no_spaces"],
        help="replace spaces in metadata values with underscores when "
        "generating filenames",
        action="store_true",
    )
    parser.add_argument(
        "-sk",
        "--skip-file",
        default=defaults["skip_file"],
        help="path to file containing tracks to skip",
    )
    parser.add_argument(
        "-w",
        "--write-successful-file",
        default=defaults["write_successful_file"],
        help="path to file to write successful tracks to",
    )
    parser.add_argument(
        "--spotify-client-id",
        default=defaults["spotify_client_id"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--spotify-client-secret",
        default=defaults["spotify_client_secret"],
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        default=defaults["log_level"],
        choices=_LOG_LEVELS.keys(),
        type=str.upper,
        help="set log verbosity",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=spotdl.config.DEFAULT_CONFIG_FILE,
        help="path to custom config.yml file"
    )
    parser.add_argument(
        "--remove-config",
        default=False,
        action="store_true",
        help="remove previously saved config"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {}".format(spotdl.__version__),
    )

    return ArgumentHandler(parser=parser)


class ArgumentHandler:
    def __init__(self, args=None, parser=argparse.ArgumentParser(""), config_base=_CONFIG_BASE):
        args_were_passed = args is not None
        if not args_were_passed:
            args = parser.parse_args().__dict__

        config_file = args.get("config")
        configured_args = args.copy()
        if config_file and os.path.isfile(config_file):
            config = spotdl.config.read_config(config_file)
            parser.set_defaults(**config["spotify-downloader"])
            configured_args = parser.parse_args().__dict__

        if args_were_passed:
            parser.set_defaults(**args)
            configured_args = parser.parse_args().__dict__

        defaults = config_base["spotify-downloader"]
        args = spotdl.util.merge_copy(defaults, args)

        self.parser = parser
        self.args = args
        self.configured_args = configured_args

    def get_configured_args(self):
        return self.configured_args

    def get_logging_level(self):
        return _LOG_LEVELS[self.configured_args["log_level"]]

    def run_errands(self):
        args = self.get_configured_args()

        if (args.get("list")
            and not mimetypes.MimeTypes().guess_type(args["list"])[0] == "text/plain"
        ):
            raise ArgumentError(
                "{0} is not of a valid argument to --list, argument must be plain text file.".format(
                    args["list"]
                )
            )

        if args.get("write_m3u") and not args.get("list"):
            raise ArgumentError("--write-m3u can only be used with --list.")

        if args["write_to"] and not (
            args.get("playlist") or args.get("album") or args.get("all_albums") or args.get("username") or args.get("write_m3u")
        ):
            raise ArgumentError(
                "--write-to can only be used with --playlist, --album, --all-albums, --username, or --write-m3u."
            )

        ffmpeg_exists = shutil.which("ffmpeg")
        if not ffmpeg_exists:
            logger.warn("FFmpeg was not found in PATH. Will not re-encode media to specified output format.")
            args["no_encode"] = True

        if args["no_encode"] and args["trim_silence"]:
            logger.warn("--trim-silence can only be used when an encoder is set.")

        if args["output_file"] == "-" and args["no_metadata"] is False:
            logger.warn(
                "Cannot write metadata when target is STDOUT. Pass "
                "--no-metadata explicitly to hide this warning."
            )
            args["no_metadata"] = True
        elif os.path.isdir(args["output_file"]):
            adjusted_output_file = os.path.join(
                args["output_file"],
                self.parser.get_default("output_file")
            )
            logger.warn(
                "Given output file is a directory. Will download tracks "
                "in this directory with their filename as per the default "
                "file format. Pass --output-file=\"{}\" to hide this "
                "warning.".format(
                    adjusted_output_file
                )
            )
            args["output_file"] = adjusted_output_file

        return args

