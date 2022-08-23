"""
Module that handles the command line arguments.
"""

import argparse
import sys
import textwrap

from argparse import _ArgumentGroup, ArgumentParser, Namespace
from typing import List

from spotdl import _version
from spotdl.download.progress_handler import NAME_TO_LEVEL
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.formatter import VARS
from spotdl.download.downloader import (
    AUDIO_PROVIDERS,
    LYRICS_PROVIDERS,
)


OPERATIONS = ["download", "save", "web", "sync"]


class SmartFormatter(argparse.HelpFormatter):
    """
    Class that overrides the default help formatter.
    """

    def _split_lines(self, text: str, width: int) -> List[str]:
        """
        Split the text in multiple lines if a line starts
        with a N|
        """

        if text.startswith("N|"):
            return text[2:].splitlines()

        text = self._whitespace_matcher.sub(" ", text).strip()

        return textwrap.wrap(text, width)


def parse_arguments() -> Namespace:
    """
    Parse arguments from the command line.

    ### Returns
    - A Namespace object containing the parsed arguments.
    """

    # Initialize argument parser
    parser = ArgumentParser(
        prog="spotdl",
        description="Download your Spotify playlists and songs along with album art and metadata",
        formatter_class=SmartFormatter,
        epilog=(
            "For more information, visit https://spotdl.github.io/spotify-downloader/ "
            "or join our Discord server: https://discord.com/invite/xCa23pwJWY"
        ),
    )

    # Parse main options
    main_options = parser.add_argument_group("Main options")
    parse_main_options(main_options)

    # Parse spotify options
    spotify_options = parser.add_argument_group("Spotify options")
    parse_spotify_options(spotify_options)

    # Parse ffmpeg options
    ffmpeg_options = parser.add_argument_group("FFmpeg options")
    parse_ffmpeg_options(ffmpeg_options)

    # Parse output options
    output_options = parser.add_argument_group("Output options")
    parse_output_options(output_options)

    # Parse misc options
    misc_options = parser.add_argument_group("Misc options")
    parse_misc_options(misc_options)

    # Parse other options
    other_options = parser.add_argument_group("Other options")
    parse_other_options(other_options)

    return parser.parse_args()


def parse_main_options(parser: _ArgumentGroup):
    """
    Parse main options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add operation argument
    operation = parser.add_argument(
        "operation",
        choices=OPERATIONS,
        help=(
            "N|The operation to perform.\n"
            "download: Download the songs to the disk and embed metadata.\n"
            "save: Saves the songs metadata to a file for further use.\n"
            "web: Starts a web interface to simplify the download process.\n"
            "sync: removes songs that are no longer present, downloads new ones\n"
        ),
    )

    # Add query argument
    query = parser.add_argument(
        "query",
        nargs="+",
        type=str,
        help=(
            "Spotify URL for a song/playlist/album/artist/etc. to download."
            "For manual audio matching, you can use the format 'YouTubeURL|SpotifyURL'"
        ),
    )

    try:
        is_web = sys.argv[1] == "web"
    except IndexError:
        is_web = False

    is_frozen = getattr(sys, "frozen", False)

    # If the program is frozen, we and user didn't pass any arguments,
    # or if the user is using the web interface, we don't need to parse
    # the query
    if (is_frozen and len(sys.argv) < 2) or (len(sys.argv) > 1 and is_web):
        # If we are running the web interface
        # or we are in the frozen env and not running web interface
        # don't remove the operation from the arg parser
        if not is_web or (is_frozen and not is_web):
            parser._remove_action(operation)  # pylint: disable=protected-access

        parser._remove_action(query)  # pylint: disable=protected-access

    # Audio provider argument
    parser.add_argument(
        "--audio",
        dest="audio_providers",
        nargs="*",
        choices=AUDIO_PROVIDERS,
        help="The audio provider to use. You can provide more than one for fallback.",
    )

    # Lyrics provider argument
    parser.add_argument(
        "--lyrics",
        dest="lyrics_providers",
        nargs="*",
        choices=LYRICS_PROVIDERS.keys(),
        help="The lyrics provider to use. You can provide more than one for fallback.",
    )

    # Add config argument
    parser.add_argument(
        "--config",
        action="store_true",
        help=(
            "Use the config file to download songs. "
            "It's located under C:\\Users\\user\\.spotdl\\config.json "
            "or ~/.spotdl/config.json under linux"
        ),
    )

    # Add search query argument
    parser.add_argument(
        "--search-query",
        help=f"The search query to use, available variables: {', '.join(VARS)}",
    )

    # Add don't filter results argument
    parser.add_argument(
        "--dont-filter-results",
        dest="filter_results",
        help="Disable filtering results.",
    )


def parse_spotify_options(parser: _ArgumentGroup):
    """
    Parse spotify options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add login argument
    parser.add_argument(
        "--user-auth",
        help="Login to Spotify using OAuth.",
    )

    # Add client id argument
    parser.add_argument(
        "--client-id",
        help="The client id to use when logging in to Spotify.",
    )

    # Add client secret argument
    parser.add_argument(
        "--client-secret",
        help="The client secret to use when logging in to Spotify.",
    )

    # Add auth token argument
    parser.add_argument(
        "--auth-token",
        help="The authorisation token to use directly to log in to Spotify.",
    )

    # Add cache path argument
    parser.add_argument(
        "--cache-path",
        type=str,
        help="The path where spotipy cache file will be stored.",
    )

    # Add no cache argument
    parser.add_argument(
        "--no-cache",
        action="store_const",
        const=True,
        help="Disable caching (both requests and token).",
    )

    # Add cookie file argument
    parser.add_argument(
        "--cookie-file",
        help="Path to cookies file.",
    )


def parse_ffmpeg_options(parser: _ArgumentGroup):
    """
    Parse ffmpeg options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add ffmpeg executable argument
    parser.add_argument(
        "--ffmpeg",
        help="The ffmpeg executable to use.",
    )

    # Add search threads argument
    parser.add_argument(
        "--threads",
        type=int,
        help="The number of threads to use when downloading songs.",
    )
    # Add constant bit rate argument
    parser.add_argument(
        "--bitrate",
        choices=[
            "8k",
            "16k",
            "24k",
            "32k",
            "40k",
            "48k",
            "64k",
            "80k",
            "96k",
            "112k",
            "128k",
            "160k",
            "192k",
            "224k",
            "256k",
            "320k",
        ],
        type=str.lower,
        help="The constant bitrate to use for the output file.",
    )

    # Additional ffmpeg arguments
    parser.add_argument(
        "--ffmpeg-args",
        type=str,
        help="Additional ffmpeg arguments passed as a string.",
    )


def parse_output_options(parser: _ArgumentGroup):
    """
    Parse output options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add output format argument
    parser.add_argument(
        "--format",
        choices=FFMPEG_FORMATS.keys(),
        help="The format to download the song in.",
    )

    # Add save file argument
    parser.add_argument(
        "--save-file",
        type=str,
        help=(
            "The file to save/load the songs data from/to. "
            "It has to end with .spotdl. "
            "If combined with the download operation, it will save the songs data to the file. "
            "Required for save/preload/sync"
        ),
        required=len(sys.argv) > 1 and sys.argv[1] in ["save"],
    )

    # Add preload argument
    parser.add_argument(
        "--preload",
        action="store_const",
        const=True,
        help="Preload the download url to speed up the download process.",
    )

    # Add name format argument
    parser.add_argument(
        "--output",
        type=str,
        help=f"Specify the downloaded file name format, available variables: {', '.join(VARS)}",
    )

    # Add m3u argument
    parser.add_argument(
        "--m3u",
        type=str,
        help="Name of the m3u file to save the songs to.",
    )

    # Add overwrite argument
    parser.add_argument(
        "--overwrite",
        choices={"force", "skip"},
        help="Overwrite existing files.",
    )

    # Option to restrict filenames for easier handling in the shell
    parser.add_argument(
        "--restrict",
        action="store_const",
        const=True,
        help="Restrict filenames to ASCII only",
    )

    # Option to print errors on exit, useful for long playlist
    parser.add_argument(
        "--print-errors",
        action="store_const",
        const=True,
        help="Print errors (wrong songs, failed downloads etc) on exit, useful for long playlist",
    )

    # Option to use sponsor block
    parser.add_argument(
        "--sponsor-block",
        action="store_const",
        const=True,
        help="Use the sponsor block to download songs from yt/ytm.",
    )


def parse_misc_options(parser: _ArgumentGroup):
    """
    Parse misc options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add verbose argument
    parser.add_argument(
        "--log-level",
        choices=NAME_TO_LEVEL.keys(),
        help="Select log level.",
    )

    # Add simple tui argument
    parser.add_argument(
        "--simple-tui",
        action="store_const",
        const=True,
        help="Use a simple tui.",
    )

    # Add headless argument
    parser.add_argument(
        "--headless",
        action="store_const",
        const=True,
        help="Run in headless mode.",
    )


def parse_other_options(parser: _ArgumentGroup):
    """
    Parse other options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    parser.add_argument(
        "--download-ffmpeg",
        action="store_true",
        help="Download ffmpeg to spotdl directory.",
    )

    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate a config file. This will overwrite current config if present.",
    )

    parser.add_argument(
        "--check-for-updates", action="store_true", help="Check for new version."
    )

    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run in profile mode. Useful for debugging.",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        help="Show the version number and exit.",
        version=_version.__version__,
    )
