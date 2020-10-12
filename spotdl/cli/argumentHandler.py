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

# from spotdl.cli.displayManager import print



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

    return parser


def get_options(args=sys.argv[1:]):
    '''
    Parse all the options created in get_arguments() and match them up with the arguments fed into the command
    sys.argv[1:] grabs all the args and filters out the 1st one: the filename.
    '''

    options = get_arguments().parse_args(args)
    return options


def passArgs(cliArgs, downloader):
    print(cliArgs)
    for request in cliArgs[1:]:
        if 'open.spotify.com' in request and 'track' in request:
            print('Fetching Song...')
            song = SongObj.from_url(request)
            downloader.download_single_song(song)
        
        elif 'open.spotify.com' in request and 'album' in request:
            print('Fetching Album...')
            songObjList = get_album_tracks(request)
            downloader.download_multiple_songs(songObjList)
        
        elif 'open.spotify.com' in request and 'playlist' in request:
            print('Fetching Playlist...')
            songObjList = get_playlist_tracks(request)
            downloader.download_multiple_songs(request)
        
        elif request.endswith('.spotdlTrackingFile'):
            print('Preparing to resume download...')
            downloader.resume_download_from_tracking_file(request)
        
        else:
            print('Searching for song "%s"...' % request)
            try:
                song = search_for_song(request)
            except:            
                print('No song named "%s" could be found on spotify' % request)
            downloader.download_single_song(song)


def passArgs2(cliArgs, downloader):
    '''
    `array` `cliArgs` : arguments gathered
    `downloader` : initiated downloader to download song

    Each arg option gets checked if it was used, and if so, the corresponding action(s) (with its parameters) gets ran.
    '''
    options = get_options(cliArgs)
    print("options:" + str(options))


    if options.spotify_client_id:
        print('gonna use id:', options.spotify_client_id)

    if options.song:
        print('gonna get song by url: ' + options.song[0])
        request = options.song[0]
        if 'open.spotify.com' in request and 'track' in request:
            print('Fetching Song...')
            song = SongObj.from_url(request)
            downloader.download_single_song(song)
        
        elif request.endswith('.spotdlTrackingFile'):
            print('Preparing to resume download...')
            downloader.resume_download_from_tracking_file(request)
        
        else:
            print('Searching for song "%s"...' % request)
            try:
                song = search_for_song(request)
            except:            
                print('No song named "%s" could be found on spotify' % request)
            downloader.download_single_song(song)

    elif options.album:
        print('gonna get album' + options.album[0])

    elif options.query:
        print('Main')

    else:
        print('Idk what im supposed to do...')
   