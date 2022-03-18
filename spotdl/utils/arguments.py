import sys

from argparse import _ArgumentGroup, ArgumentParser, Namespace

from spotdl import _version
from spotdl.download.progress_handler import NAME_TO_LEVEL
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.config import DEFAULT_CONFIG
from spotdl.download.downloader import (
    AUDIO_PROVIDERS,
    LYRICS_PROVIDERS,
)


OPERATIONS = ["download", "save", "preload", "web", "sync"]


def parse_arguments() -> Namespace:
    """
    Parse arguments from the command line.
    """

    # Initialize argument parser
    parser = ArgumentParser(
        prog="spotdl",
        description="Download your Spotify playlists and songs along with album art and metadata",
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
    """

    # Add mode argument
    parser.add_argument(
        "operation", choices=OPERATIONS, help="The operation to perform."
    )

    # Add query argument
    parser.add_argument(
        "query",
        nargs="+" if len(sys.argv) > 1 and "web" != sys.argv[1] else "?",
        type=str,
        help="URL for a song/playlist/album/artist/etc. to download.",
    )

    # Audio provider argument
    parser.add_argument(
        "--audio",
        dest="audio_provider",
        choices=AUDIO_PROVIDERS.keys(),
        default=DEFAULT_CONFIG["audio_provider"],
        help="The audio provider to use.",
    )

    # Lyrics provider argument
    parser.add_argument(
        "--lyrics",
        dest="lyrics_provider",
        choices=LYRICS_PROVIDERS.keys(),
        default=DEFAULT_CONFIG["lyrics_provider"],
        help="The lyrics provider to use.",
    )

    # Add config argument
    parser.add_argument(
        "--config",
        action="store_true",
        help="Use the config file to download songs.",
    )

    # Add search query argument
    parser.add_argument(
        "--search-query",
        default=DEFAULT_CONFIG["search_query"],
        help="The search query to use.",
    )

    # Add don't filter results argument
    parser.add_argument(
        "--dont-filter-results",
        action="store_false",
        dest="filter_results",
        default=DEFAULT_CONFIG["filter_results"],
        help="Disable filtering results.",
    )

    return parser


def parse_spotify_options(parser: _ArgumentGroup):
    """
    Parse spotify options from the command line.
    """

    # Add login argument
    parser.add_argument(
        "--user-auth",
        action="store_true",
        default=DEFAULT_CONFIG["user_auth"],
        help="Login to Spotify using OAuth.",
    )

    # Add client id argument
    parser.add_argument(
        "--client-id",
        default=DEFAULT_CONFIG["client_id"],
        help="The client id to use when logging in to Spotify.",
    )

    # Add client secret argument
    parser.add_argument(
        "--client-secret",
        default=DEFAULT_CONFIG["client_secret"],
        help="The client secret to use when logging in to Spotify.",
    )

    # Add cache path argument
    parser.add_argument(
        "--cache-path",
        type=str,
        default=DEFAULT_CONFIG["cache_path"],
        help="The path where spotipy cache file will be stored.",
    )

    # Add no cache argument
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=DEFAULT_CONFIG["no_cache"],
        help="Disable caching.",
    )

    # Add cookie file argument
    parser.add_argument(
        "--cookie-file",
        default=DEFAULT_CONFIG["cookie_file"],
        help="Path to cookies file.",
    )


def parse_ffmpeg_options(parser: _ArgumentGroup):
    """
    Parse ffmpeg options from the command line.
    """

    # Add ffmpeg executable argument
    parser.add_argument(
        "--ffmpeg",
        default=DEFAULT_CONFIG["ffmpeg"],
        help="The ffmpeg executable to use.",
    )

    # Add search threads argument
    parser.add_argument(
        "--threads",
        default=DEFAULT_CONFIG["threads"],
        type=int,
        help="The number of threads to use when downloading songs.",
    )

    # Add variable bitrate argument
    parser.add_argument(
        "--variable-bitrate",
        choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
        default=DEFAULT_CONFIG["variable_bitrate"],
        help="The variable bitrate to use for the output file.",
    )

    # Add constant bit rate argument
    parser.add_argument(
        "--constant-bitrate",
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
        default=DEFAULT_CONFIG["constant_bitrate"],
        help="The constant bitrate to use for the output file.",
    )

    # Additional ffmpeg arguments
    parser.add_argument(
        "--ffmpeg-args",
        nargs="*",
        default=DEFAULT_CONFIG["ffmpeg_args"],
        help="Additional ffmpeg arguments.",
    )


def parse_output_options(parser: _ArgumentGroup):
    """
    Parse output options from the command line.
    """

    # Add output format argument
    parser.add_argument(
        "--format",
        choices=FFMPEG_FORMATS.keys(),
        default=DEFAULT_CONFIG["format"],
        help="The format to download the song in.",
    )

    # Add save file argument
    parser.add_argument(
        "--save-file",
        type=str,
        default=DEFAULT_CONFIG["save_file"],
        help="The file to save/load the songs data from/to. It has to end with .spotdl",
        required=len(sys.argv) > 1 and sys.argv[1] in ["save", "preload"],
    )

    # Add name format argument
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_CONFIG["output"],
        help="Specify the downloaded file name format.",
    )

    # Add m3u argument
    parser.add_argument(
        "--m3u",
        type=str,
        default=DEFAULT_CONFIG["m3u"],
        help="Name of the m3u file to save the songs to.",
    )

    # Add overwrite argument
    parser.add_argument(
        "--overwrite",
        choices={"force", "skip"},
        default=DEFAULT_CONFIG["overwrite"],
        help="Overwrite existing files.",
    )

    # Option to restrict filenames for easier handling in the shell
    parser.add_argument(
        "--restrict",
        default=DEFAULT_CONFIG["restrict"],
        help="Restrict filenames to ASCII only",
        action="store_true",
    )


def parse_misc_options(parser: _ArgumentGroup):
    """
    Parse misc options from the command line.
    """

    # Add verbose argument
    parser.add_argument(
        "--log-level",
        default=DEFAULT_CONFIG["log_level"],
        choices=NAME_TO_LEVEL.keys(),
        help="Select log level.",
    )

    # Add simple tui argument
    parser.add_argument(
        "--simple-tui",
        action="store_true",
        default=DEFAULT_CONFIG["simple_tui"],
        help="Use a simple tui.",
    )

    # Add headless argument
    parser.add_argument(
        "--headless",
        action="store_true",
        default=DEFAULT_CONFIG["headless"],
        help="Run in headless mode.",
    )


def parse_other_options(parser: _ArgumentGroup):
    """
    Parse other options from the command line.
    These are used only as a placeholders
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
        "--version",
        "-v",
        action="version",
        help="Show the version number and exit.",
        version=_version.__version__,
    )
