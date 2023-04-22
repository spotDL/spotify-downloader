"""
Module that handles the command line arguments.
"""

import argparse
import sys
import textwrap
from argparse import ArgumentParser, Namespace, _ArgumentGroup
from typing import List

from spotdl import _version
from spotdl.download.downloader import AUDIO_PROVIDERS, LYRICS_PROVIDERS
from spotdl.utils.ffmpeg import FFMPEG_FORMATS
from spotdl.utils.formatter import VARS
from spotdl.utils.logging import NAME_TO_LEVEL

__all__ = ["OPERATIONS", "SmartFormatter", "parse_arguments"]

OPERATIONS = ["download", "save", "web", "sync", "meta", "url"]


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
        default="download",
        const="download",
        nargs="?",
        help=(
            "N|The operation to perform.\n"
            "download: Download the songs to the disk and embed metadata.\n"
            "save: Saves the songs metadata to a file for further use.\n"
            "web: Starts a web interface to simplify the download process.\n"
            "sync: Removes songs that are no longer present, downloads new ones\n"
            "meta: Update your audio files with metadata\n"
            "url: Get the download URL for songs\n\n"
        ),
    )

    # Add query argument
    query = parser.add_argument(
        "query",
        nargs="+",
        type=str,
        help=(
            "N|Spotify/YouTube URL for a song/playlist/album/artist/etc. to download.\n"
            "For album searching, include 'album:' and optional 'artist:' tags\n"
            "(ie. 'album:the album name' or 'artist:the artist album: the album').\n"
            "For manual audio matching, you can use the format 'YouTubeURL|SpotifyURL'\n"
            "You can only use album/playlist/tracks urls when "
            "downloading/matching youtube urls.\n"
            "When using youtube url without spotify url, "
            "you won't be able to use `--fetch-albums` option.\n\n"
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
        help=(
            "The lyrics provider to use. You can provide more than one for fallback. "
            "Synced lyrics might not work correctly with some music players. "
            "For such cases it's better to use `--generate-lrc` option."
        ),
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
        type=str,
    )

    # Add don't filter results argument
    parser.add_argument(
        "--dont-filter-results",
        dest="filter_results",
        action="store_const",
        const=False,
        help="Disable filtering results.",
    )

    # Add use only verified results argument
    parser.add_argument(
        "--only-verified-results",
        action="store_const",
        const=True,
        help="Use only verified results. (Not all providers support this)",
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
        action="store_const",
        const=True,
        help="Login to Spotify using OAuth.",
    )

    # Add client id argument
    parser.add_argument(
        "--client-id",
        help="The client id to use when logging in to Spotify.",
        type=str,
    )

    # Add client secret argument
    parser.add_argument(
        "--client-secret",
        help="The client secret to use when logging in to Spotify.",
        type=str,
    )

    # Add auth token argument
    parser.add_argument(
        "--auth-token",
        help="The authorization token to use directly to log in to Spotify.",
        type=str,
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

    # Add max retries argument
    parser.add_argument(
        "--max-retries",
        type=int,
        help="The maximum number of retries to perform when getting metadata.",
    )

    # Add headless argument
    parser.add_argument(
        "--headless",
        action="store_const",
        const=True,
        help="Run in headless mode.",
    )

    # Add use cache file argument
    parser.add_argument(
        "--use-cache-file",
        action="store_const",
        const=True,
        help=(
            "Use the cache file to get metadata. "
            "It's located under C:\\Users\\user\\.spotdl\\.spotify_cache "
            "or ~/.spotdl/.spotify_cache under linux. "
            "It only caches tracks and "
            "gets updated whenever spotDL gets metadata from Spotify. "
            "(It may provide outdated metadata use with caution)"
        ),
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
        type=str,
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
            "auto",
            "disable",
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
        ]
        + list(map(str, range(0, 10))),
        type=str.lower,
        help=(
            "The constant/variable bitrate to use for the output file. "
            "Values from 0 to 9 are variable bitrates. "
            "Auto will use the bitrate of the original file. "
            "Disable will disable the bitrate option. "
            "(In case of m4a and opus files, auto and disable will skip the conversion)"
        ),
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
        type=str,
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
        nargs="?",
        help=(
            "Name of the m3u file to save the songs to. "
            "Defaults to {list[0]}.m3u8 "
            "If you want to generate a m3u for each list in the query use {list}, "
            "If you want to generate a m3u file based on the first list in the query use {list[0]}"
            ", (0 is the first list in the query, 1 is the second, etc. "
            "songs don't count towards the list number) "
        ),
        const="{list[0]}.m3u8",
    )

    # Add cookie file argument
    parser.add_argument(
        "--cookie-file",
        help="Path to cookies file.",
        type=str,
    )

    # Add overwrite argument
    parser.add_argument(
        "--overwrite",
        choices={"force", "skip", "metadata"},
        help=(
            "How to handle existing/duplicate files. "
            "(When combined with --scan-for-songs force will remove "
            "all duplicates, and metadata will only apply metadata to the "
            "latest song and will remove the rest. )"
        ),
        type=str,
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

    # Add archive_file argument
    parser.add_argument(
        "--archive",
        type=str,
        help="Specify the file name for an archive of already downloaded songs",
    )

    # Option to set the track number & album of tracks in a playlist to their index in the playlist
    # & the name of playlist respectively.
    parser.add_argument(
        "--playlist-numbering",
        action="store_const",
        dest="playlist_numbering",
        const=True,
        help="Sets each track in a playlist to have the playlist's name as its album,\
            and album art as the playlist's icon",
    )

    # Option to scan the output directory for existing files
    parser.add_argument(
        "--scan-for-songs",
        action="store_const",
        const=True,
        help=(
            "Scan the output directory for existing files. "
            "This option should be combined with the --overwrite option "
            "to control how existing files are handled. (Output directory is the last directory "
            "that is not a template variable in the output template)"
        ),
    )

    # Option to fetch all albums from songs in query
    parser.add_argument(
        "--fetch-albums",
        action="store_const",
        const=True,
        help="Fetch all albums from songs in query",
    )

    # Option to change the id3 separator
    parser.add_argument(
        "--id3-separator",
        type=str,
        help="Change the separator used in the id3 tags. Only supported for mp3 files.",
    )

    # Option to use ytm data instead of spotify data
    # when downloading using ytm link
    parser.add_argument(
        "--ytm-data",
        action="store_const",
        const=True,
        help="Use ytm data instead of spotify data when downloading using ytm link.",
    )

    # Option whether to add unavailable songs to the m3u file
    parser.add_argument(
        "--add-unavailable",
        action="store_const",
        const=True,
        help="Add unavailable songs to the m3u/archive files when downloading",
    )

    # Generate lrc files
    parser.add_argument(
        "--generate-lrc",
        action="store_const",
        const=True,
        help=(
            "Generate lrc files for downloaded songs. "
            "Requires `synced` provider to be present in the lyrics providers list."
        ),
    )

    # Force update metadata
    parser.add_argument(
        "--force-update-metadata",
        action="store_const",
        const=True,
        help="Force update metadata for songs that already have metadata.",
    )

    # Sync without deleting
    parser.add_argument(
        "--sync-without-deleting",
        action="store_const",
        const=True,
        help="Sync without deleting songs that are not in the query.",
    )

    # Max file name length
    parser.add_argument(
        "--max-filename-length",
        type=int,
        help=(
            "Max file name length. "
            "(This won't override the max file name length enforced by the OS)"
        ),
    )


def parse_web_options(parser: _ArgumentGroup):
    """
    Parse web options from the command line.

    ### Arguments
    - parser: The argument parser to add the options to.
    """

    # Add host argument
    parser.add_argument(
        "--host",
        type=str,
        help="The host to use for the web server.",
    )

    # Add port argument
    parser.add_argument(
        "--port",
        type=int,
        help="The port to run the web server on.",
    )

    # Add keep alive argument
    parser.add_argument(
        "--keep-alive",
        action="store_const",
        const=True,
        help="Keep the web server alive even when no clients are connected.",
    )

    # Add allowed origins argument
    parser.add_argument(
        "--allowed-origins",
        nargs="*",
        help="The allowed origins for the web server.",
    )

    # Add use output directory argument
    parser.add_argument(
        "--web-use-output-dir",
        action="store_const",
        const=True,
        help=(
            "Use the output directory instead of the session directory for downloads. ("
            "This might cause issues if you have multiple users using the web-ui at the same time)"
        ),
    )

    # Add keep sessions argument
    parser.add_argument(
        "--keep-sessions",
        action="store_const",
        const=True,
        help="Keep the session directory after the web server is closed.",
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


def create_parser() -> ArgumentParser:
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
            "For more information, visit http://spotdl.rtfd.io/ "
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

    # Parse web options
    web_options = parser.add_argument_group("Web options")
    parse_web_options(web_options)

    # Parse misc options
    misc_options = parser.add_argument_group("Misc options")
    parse_misc_options(misc_options)

    # Parse other options
    other_options = parser.add_argument_group("Other options")
    parse_other_options(other_options)

    return parser


def parse_arguments() -> Namespace:
    """
    Parse arguments from the command line.

    ### Arguments
    - parser: The argument parser to parse the arguments from.

    ### Returns
    - A Namespace object containing the parsed arguments.
    """

    # Create parser
    parser = create_parser()

    # Parse arguments
    return parser.parse_args()
