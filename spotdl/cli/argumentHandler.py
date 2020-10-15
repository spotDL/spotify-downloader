'''
Everything that has to do with translating command line arguments is in this file. 
This library is completely optional to the base spotDL ecosystem but is apart of the command-line service.
These arguments are created to provide as few breaking changes between v2 -> v3 migration so most of these should be the same as spotdl=v2
'''

#===============
#=== Imports ===
#===============

from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj
import sys
import argparse




def get_arguments():
    '''
    Generate all possible arguments along with their alias, alt. alias, and help description
    '''
    parser = argparse.ArgumentParser(
        description="Download Spotify playlists from YouTube with albumart and metadata",
        # version='3.0',
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # add_help=True
    )
    parser.add_argument('-v', '--version', action='version', version='3.0')

    parser.add_argument(
        "query",
        nargs='*',
        help="Download track/album/playlist/artist by Spotify track/album/playlist link, song query, .spotdlTrackingFile, or Youtube url."
    )
    parser.add_argument(
        "-u",
        "--url",
        nargs="+",
        help="Download track(s) by Spotify link, or youtube url."
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Download tracks from a .spotdlTrackingFile (WARNING: this file will be modified!)"
    )
    # parser.add_argument(
    #     "-l",
    #     "--list",
    #     help="Download tracks from a file cantaining a list of queries (WARNING: this file will be modified!)"
    # )
    # parser.add_argument(
    #     "-p",
    #     "--playlist",
    #     help="Load tracks from playlist URL into <playlist_name>.txt or "
    #          "if `--write-to=<path/to/file.txt>` has been passed",
    # )
    # parser.add_argument(
    #     "-a",
    #     "--album",
    #     help="Load tracks from album URL into <album_name>.txt or if "
    #          "`--write-to=<path/to/file.txt>` has been passed"
    # )
    # parser.add_argument(
    #     "-aa",
    #     "--all-albums",
    #     help="load all tracks from artist URL into <artist_name>.txt "
    # )


    authgroup = parser.add_argument_group('authentication')

    authgroup.add_argument(
        "--spotify-client-id",
        # default=defaults["spotify_client_id"],
        help=argparse.SUPPRESS,
    )
    authgroup.add_argument(
        "--spotify-client-secret",
        # default=defaults["spotify_client_secret"],
        help=argparse.SUPPRESS,
    )

    devgroup = parser.add_argument_group('debug')

    devgroup.add_argument(
        "--debug",
        # action="store_true",
        nargs='?',
        const='local',  # Scope: local/global/file(global)
        help=argparse.SUPPRESS,
    )

    return parser


def get_options(args=sys.argv[1:]):
    '''
    Parse all the options created in get_arguments() and match them up with the arguments fed into the command
    sys.argv[1:] grabs all the args and filters out the 1st one: the filename.
    '''

    options = get_arguments().parse_args(args)
    return options

