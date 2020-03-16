from logzero import logger as log
import appdirs

import logging
import yaml
import argparse
import mimetypes
import os

import spotdl
from spotdl import internals


_LOG_LEVELS_STR = ["INFO", "WARNING", "ERROR", "DEBUG"]

default_conf = {
    "spotify-downloader": {
        "no-remove-original": False,
        "manual": False,
        "no-metadata": False,
        "no-fallback-metadata": False,
        "avconv": False,
        "folder": internals.get_music_dir(),
        "overwrite": "prompt",
        "input-ext": ".m4a",
        "output-ext": ".mp3",
        "write-to": None,
        "trim-silence": False,
        "download-only-metadata": False,
        "dry-run": False,
        "music-videos-only": False,
        "no-spaces": False,
        "file-format": "{artist} - {track_name}",
        "search-format": "{artist} - {track_name} lyrics",
        "youtube-api-key": None,
        "skip": None,
        "write-successful": None,
        "log-level": "INFO",
        "spotify_client_id": "4fe3fecfe5334023a1472516cc99d805",
        "spotify_client_secret": "0f02b7c483c04257984695007a4a8d5c",
    }
}


def log_leveller(log_level_str):
    loggin_levels = [logging.INFO, logging.WARNING, logging.ERROR, logging.DEBUG]
    log_level_str_index = _LOG_LEVELS_STR.index(log_level_str)
    loggin_level = loggin_levels[log_level_str_index]
    return loggin_level


def merge(default, config):
    """ Override default dict with config dict. """
    merged = default.copy()
    merged.update(config)
    return merged


def get_config(config_file):
    try:
        with open(config_file, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)
    except FileNotFoundError:
        log.info("Writing default configuration to {0}:".format(config_file))
        with open(config_file, "w") as ymlfile:
            yaml.dump(default_conf, ymlfile, default_flow_style=False)
            cfg = default_conf

        for line in yaml.dump(
            default_conf["spotify-downloader"], default_flow_style=False
        ).split("\n"):
            if line.strip():
                log.info(line.strip())
        log.info(
            "Please note that command line arguments have higher priority "
            "than their equivalents in the configuration file"
        )

    return cfg["spotify-downloader"]


def override_config(config_file, parser, raw_args=None):
    """ Override default dict with config dict passed as comamnd line argument. """
    config_file = os.path.realpath(config_file)
    config = merge(default_conf["spotify-downloader"], get_config(config_file))
    parser.set_defaults(**config)
    return parser.parse_args(raw_args)


def get_arguments(raw_args=None, to_group=True, to_merge=True):
    parser = argparse.ArgumentParser(
        description="Download and convert tracks from Spotify, Youtube etc.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    if to_merge:
        config_dir = os.path.join(appdirs.user_config_dir(), "spotdl")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "config.yml")
        config = merge(default_conf["spotify-downloader"], get_config(config_file))
    else:
        config = default_conf["spotify-downloader"]

    if to_group:
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "-s", "--song", nargs="+", help="download track by spotify link or name"
        )
        group.add_argument("-l", "--list", help="download tracks from a file")
        group.add_argument(
            "-p",
            "--playlist",
            help="load tracks from playlist URL into <playlist_name>.txt",
        )
        group.add_argument(
            "-b", "--album", help="load tracks from album URL into <album_name>.txt"
        )
        group.add_argument(
            "-ab",
            "--all-albums",
            help="load all tracks from artist URL into <artist_name>.txt",
        )
        group.add_argument(
            "-u",
            "--username",
            help="load tracks from user's playlist into <playlist_name>.txt",
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
        "-nr",
        "--no-remove-original",
        default=config["no-remove-original"],
        help="do not remove the original file after conversion",
        action="store_true",
    )
    parser.add_argument(
        "-nm",
        "--no-metadata",
        default=config["no-metadata"],
        help="do not embed metadata in tracks",
        action="store_true",
    )
    parser.add_argument(
        "-nf",
        "--no-fallback-metadata",
        default=config["no-fallback-metadata"],
        help="do not use YouTube as fallback for metadata if track not found on Spotify",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--avconv",
        default=config["avconv"],
        help="use avconv for conversion (otherwise defaults to ffmpeg)",
        action="store_true",
    )
    parser.add_argument(
        "-f",
        "--folder",
        default=os.path.abspath(config["folder"]),
        help="path to folder where downloaded tracks will be stored in",
    )
    parser.add_argument(
        "--overwrite",
        default=config["overwrite"],
        help="change the overwrite policy",
        choices={"prompt", "force", "skip"},
    )
    parser.add_argument(
        "-i",
        "--input-ext",
        default=config["input-ext"],
        help="preferred input format .m4a or .webm (Opus)",
        choices={".m4a", ".webm"},
    )
    parser.add_argument(
        "-o",
        "--output-ext",
        default=config["output-ext"],
        help="preferred output format .mp3, .m4a (AAC), .flac, etc.",
    )
    parser.add_argument(
        "--write-to",
        default=config["write-to"],
        help="write tracks from Spotify playlist, album, etc. to this file",
    )
    parser.add_argument(
        "-ff",
        "--file-format",
        default=config["file-format"],
        help="file format to save the downloaded track with, each tag "
        "is surrounded by curly braces. Possible formats: "
        "{}".format([internals.formats[x] for x in internals.formats]),
    )
    parser.add_argument(
        "--trim-silence",
        default=config["trim-silence"],
        help="remove silence from the start of the audio",
        action="store_true",
    )
    parser.add_argument(
        "-sf",
        "--search-format",
        default=config["search-format"],
        help="search format to search for on YouTube, each tag "
        "is surrounded by curly braces. Possible formats: "
        "{}".format([internals.formats[x] for x in internals.formats]),
    )
    parser.add_argument(
        "-dm",
        "--download-only-metadata",
        default=config["download-only-metadata"],
        help="download tracks only whose metadata is found",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        default=config["dry-run"],
        help="show only track title and YouTube URL, and then skip "
        "to the next track (if any)",
        action="store_true",
    )
    parser.add_argument(
        "-mo",
        "--music-videos-only",
        default=config["music-videos-only"],
        help="search only for music videos on Youtube (works only "
        "when YouTube API key is set",
        action="store_true",
    )
    parser.add_argument(
        "-ns",
        "--no-spaces",
        default=config["no-spaces"],
        help="replace spaces with underscores in file names",
        action="store_true",
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        default=config["log-level"],
        choices=_LOG_LEVELS_STR,
        type=str.upper,
        help="set log verbosity",
    )
    parser.add_argument(
        "-yk",
        "--youtube-api-key",
        default=config["youtube-api-key"],
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
        default=config["write-successful"],
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
        "-c", "--config", default=None, help="path to custom config.yml file"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {}".format(spotdl.__version__),
    )

    parsed = parser.parse_args(raw_args)

    if parsed.config is not None and to_merge:
        parsed = override_config(parsed.config, parser)

    if (
        to_group
        and parsed.list
        and not mimetypes.MimeTypes().guess_type(parsed.list)[0] == "text/plain"
    ):
        parser.error(
            "{0} is not of a valid argument to --list, argument must be plain text file".format(
                parsed.list
            )
        )

    if parsed.write_m3u and not parsed.list:
        parser.error("--write-m3u can only be used with --list")

    if parsed.avconv and parsed.trim_silence:
        parser.error("--trim-silence can only be used with FFmpeg")

    if parsed.write_to and not (
        parsed.playlist or parsed.album or parsed.all_albums or parsed.username
    ):
        parser.error(
            "--write-to can only be used with --playlist, --album, --all-albums, or --username"
        )

    parsed.log_level = log_leveller(parsed.log_level)

    return parsed
