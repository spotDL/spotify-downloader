from logzero import logger as log
import appdirs

import logging
import argparse
import mimetypes
import os
import sys
import shutil

import spotdl.util
import spotdl.config


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


def get_arguments(argv=None, to_merge=True):
    parser = argparse.ArgumentParser(
        description="Download and convert tracks from Spotify, Youtube etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    config_file = spotdl.config.default_config_file
    if to_merge:
        config_dir = os.path.dirname(spotdl.config.default_config_file)
        os.makedirs(os.path.dirname(spotdl.config.default_config_file), exist_ok=True)
        config = spotdl.util.merge(
            spotdl.config.DEFAULT_CONFIGURATION["spotify-downloader"],
            spotdl.config.get_config(config_file)
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
        "-b"
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
        "-e",
        "--encoder",
        default=config["encoder"],
        choices={"ffmpeg", "avconv", "null"},
        help="use this encoder for conversion",
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
    parser.add_argument(
        "--processor",
        default=config["processor"],
        choices={"synchronous", "threaded"},
        help='list downloading strategy: - "synchronous" downloads '
        'tracks one-by-one. - "threaded" (highly experimental at the '
        'moment! expect it to slash & burn) pre-fetches the next '
        'track\'s metadata for more efficient downloading'
    )
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
        default=config_file,
        help="path to custom config.yml file"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {}".format(spotdl.__version__),
    )

    parsed = parser.parse_args(argv)

    if parsed.config is not None and to_merge:
        parsed = override_config(parsed.config, parser)

    return run_errands(parser, parsed, config)


def run_errands(parser, parsed, config):
    if (parsed.list
        and not mimetypes.MimeTypes().guess_type(parsed.list)[0] == "text/plain"
    ):
        parser.error(
            "{0} is not of a valid argument to --list, argument must be plain text file".format(
                parsed.list
            )
        )

    if parsed.write_m3u and not parsed.list:
        parser.error("--write-m3u can only be used with --list")

    if parsed.trim_silence and not "ffmpeg" in parsed.encoder:
        parser.error("--trim-silence can only be used with FFmpeg")

    if parsed.write_to and not (
        parsed.playlist or parsed.album or parsed.all_albums or parsed.username
    ):
        parser.error(
            "--write-to can only be used with --playlist, --album, --all-albums, or --username"
        )

    encoder_exists = shutil.which(parsed.encoder)
    if not encoder_exists:
        # log.warn("Specified encoder () was not found. Will not encode to specified "
        #          "output format".format(parsed.encoder))
        parsed.encoder = "null"

    if parsed.output_file == "-" and parsed.no_metadata is False:
        # log.warn(
        #     "Cannot write metadata when target file is STDOUT. Pass "
        #     "--no-metadata explicitly to hide this warning."
        # )
        parsed.no_metadata = True
    elif os.path.isdir(parsed.output_file):
        adjusted_output_file = os.path.join(
            parsed.output_file,
            config["output-file"]
        )
        # log.warn(
        #     "Specified output file is a directory. Will write the filename as in
        #     "default file format. Pass --output-file={} to hide this warning".format(
        #         adjusted_output_file
        # )
        parsed.output_file = adjusted_output_file

    parsed.log_level = log_leveller(parsed.log_level)

    # We're done dealing with configuration file here and don't need to use it later
    del parsed.config

    return parsed

