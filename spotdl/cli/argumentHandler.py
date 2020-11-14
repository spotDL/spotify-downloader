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




def get_cli_arguments():
    '''
    Generate all possible arguments along with their alias, alt. alias, and help description

    RETURNS `ArgumentParser` object
    '''
    parser = argparse.ArgumentParser(
        description="Download Spotify playlists from YouTube with albumart and metadata",
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # add_help=True
    )

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

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not output to console"
    )


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

    return parser


def get_cli_options():
    '''
    Convert argument strings to objects and assign them as attributes of the namespace

    RETURNS `options` the populated namespace.
    '''

    options = get_cli_arguments().parse_args()
    return options

