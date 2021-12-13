from argparse import ArgumentParser, RawDescriptionHelpFormatter

import pkg_resources

help_notice = r"""
To download a song run,
    spotdl [trackUrl]
    ex. spotdl https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b

To download a album run,
    spotdl [albumUrl]
    ex. spotdl https://open.spotify.com/album/4yP0hdKOZPNshxUOjY0cZj

To download a playlist, run:
    spotdl [playlistUrl]
    ex. spotdl https://open.spotify.com/playlist/37i9dQZF1E8UXBoz02kGID

To download your saved songs, run:
    spotdl --user-auth saved

To download all songs from an artist run:
    spotdl [artistUrl]
    ex. spotdl https://open.spotify.com/artist/1fZAAHNWdSM5gqbi9o5iEA

To download youtube video with metadata from spotify run:
    spotdl "YouTubeURL|SpotifyURL"
    ex. spotdl "https://www.youtube.com/watch?v=EO7XnC1YpVo|https://open.spotify.com/track/4fzsfWzRhPawzqhX8Qt9F3"
    Note: urls that you pass have to be quoted properly ex. "YouTubeURL|SpotifyUrl"

To change output format run:
    spotdl [songUrl] --output-format mp3/m4a/flac/opus/ogg/wav
    ex. spotdl [songUrl] --output-format opus

To specifiy path template run:
    spotdl [songUrl] -p 'template'
    ex. spotdl [songUrl] -p "{playlist}/{artists}/{album} - {title} {artist}.{ext}"

To use FFmpeg binary that is not on PATH run:
    spotdl [songUrl] --ffmpeg path/to/your/ffmpeg.exe
    ex. spotdl [songUrl] --ffmpeg C:\ffmpeg\bin\ffmpeg.exe

To generate .m3u file for each playlist run:
    spotdl [playlistUrl] --m3u
    ex. spotdl https://open.spotify.com/playlist/37i9dQZF1E8UXBoz02kGID --m3u

To use Youtube instead of YouTube Music run:
    spotdl [songUrl] --use-youtube
    ex. spotdl https://open.spotify.com/track/4fzsfWzRhPawzqhX8Qt9F3 --use-youtube

To change number of threads used when downloading songs run:
    spotdl [songUrl] --dt [number]
    ex. spotdl https://open.spotify.com/track/4fzsfWzRhPawzqhX8Qt9F3 --dt 8

To change number of threads used when searching for songs run:
    spotdl [songUrl] --st [number]
    ex. spotdl https://open.spotify.com/track/4fzsfWzRhPawzqhX8Qt9F3 --st 8

To ignore your ffmpeg version run:
    spotdl --ignore-ffmpeg-version

To search for and download a song, run, with quotation marks:
Note: This is not accurate and often causes errors.
    spotdl [songQuery]
    ex. spotdl 'The Weeknd - Blinding Lights'

To resume a failed/incomplete download, run:
    spotdl [pathToTrackingFile]
    ex. spotdl 'The Weeknd - Blinding Lights.spotdlTrackingFile'

    .spotdlTrackingFiles are automatically created when a download starts and deleted on completion

You can queue up multiple download tasks by separating the arguments with spaces:
    spotdl [songQuery1] [albumUrl] [songQuery2] ... (order does not matter)
    ex. spotdl 'The Weeknd - Blinding Lights'
            https://open.spotify.com/playlist/37i9dQZF1E8UXBoz02kGID ...

You can use the --debug-termination flag to figure out where in the code spotdl got stuck.

spotDL downloads up to 4 songs in parallel, so for a faster experience,
download albums and playlist, rather than tracks.
"""  # noqa: E501


def parse_arguments():
    # Initialize argument parser
    parser = ArgumentParser(
        prog="spotdl",
        description=help_notice,
        formatter_class=RawDescriptionHelpFormatter,
    )

    # Search query
    parser.add_argument(
        "query", type=str, nargs="+", help="URL/String for a song/album/playlist/artist"
    )

    # Version
    version = pkg_resources.require("spotdl")[0].version
    parser.add_argument("--version", "-v", action="version", version=version)

    # Option to enable debug termination
    parser.add_argument("--debug-termination", action="store_true")

    # Option to specify output directory
    parser.add_argument("--output", "-o", help="Output directory path")

    # Option to specify output format
    parser.add_argument(
        "--output-format",
        "--of",
        help="Output format",
        choices={"mp3", "m4a", "flac", "ogg", "opus", "wav"},
        default="mp3",
    )

    # Option to enable user auth
    parser.add_argument(
        "--user-auth", help="Use User Authentication", action="store_true"
    )

    # Option to use youtube instead of youtube music
    parser.add_argument(
        "--use-youtube", help="Use youtube instead of YTM", action="store_true"
    )

    # Option to select a lyrics provider
    parser.add_argument(
        "--lyrics-provider",
        help="Select a lyrics provider",
        type=str,
        choices=["genius", "musixmatch"],
        default="musixmatch",
    )

    # Option to provide path template for downloaded files
    parser.add_argument(
        "-p",
        "--path-template",
        help="Path template for downloaded files",
        type=str,
        default=None,
    )

    # Option to specify path to local ffmpeg
    parser.add_argument("-f", "--ffmpeg", help="Path to ffmpeg", dest="ffmpeg")

    # Option to ignore ffmpeg version
    parser.add_argument(
        "--ignore-ffmpeg-version", help="Ignore ffmpeg version", action="store_true"
    )

    # Option to specify number of threads to use when downloading songs
    parser.add_argument(
        "--download-threads",
        "--dt",
        help="Number of threads used when downloading songs",
        type=int,
        default=4,
    )

    # Option to specify number of threads to use when searching for songs
    parser.add_argument(
        "--search-threads",
        "--st",
        help="Number of threads used when searching for songs",
        type=int,
        default=4,
    )

    # Option to generate .m3u
    parser.add_argument(
        "--generate-m3u",
        "--m3u",
        help="Generate .m3u file for each playlist",
        action="store_true",
    )

    return parser.parse_args()
