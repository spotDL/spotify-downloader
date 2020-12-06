#! Basic necessities to get the CLI running
from argparse import ArgumentParser
from argparse import Namespace
import sys

#! Song Search from different start points
from spotdl.search.utils import get_playlist_tracks, get_album_tracks, search_for_song
from spotdl.search.songObj import SongObj
from spotdl.search.spotifyClient import SpotifyClient

class SpotDlApp():

    help_notice = '''
    To download a song run,
        spotdl $trackUrl
        eg. spotdl https://open.spotify.com/track/08mG3Y1vljYA6bvDt4Wqkj?si=SxezdxmlTx-CaVoucHmrUA
    
    To download a album run,
        spotdl $albumUrl
        eg. spotdl https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=gF5dOQm8QUSo-NdZVsFjAQ
    
    To download a playlist run,
        spotdl $playlistUrl
        eg. spotdl https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ
    
    To search for and download a song (not very accurate) run,
        spotdl $songQuery
        eg. spotdl 'The HU - Sugaan Essenna'
    
    To resume a failed/incomplete download run,
        spotdl $pathToTrackingFile
        eg. spotdl 'Sugaan Essenna.spotdlTrackingFile'
    
        Note, '.spotDlTrackingFiles' are automatically created during download start, they are deleted on
        download completion
    
    You can chain up download tasks by seperating them with spaces:
        spotdl $songQuery1 $albumUrl $songQuery2 ... (order does not matter)
        eg. spotdl 'The Hu - Sugaan Essenna' https://open.spotify.com/playlist/37i9dQZF1DWXhcuQw7KIeM?si=xubKHEBESM27RqGkqoXzgQ ...
    
    Spotdl downloads up to 4 songs in parallel - try to download albums and playlists instead of
    tracks for more speed
    '''

    default_client_id = '4fe3fecfe5334023a1472516cc99d805'
    default_client_secret = '0f02b7c483c04257984695007a4a8d5c'

    def _parseArgs(self, cmdLine) -> Namespace:
        argParser = ArgumentParser(add_help=False)
        argParser.add_argument("--help", help="print help message", action="store_true")
        argParser.add_argument("--h", help="print help message", action="store_true")
        argParser.add_argument("--clientId", help="provide alternative clientId for spotipy")
        argParser.add_argument("--clientSecret", help="provide alternative clientSecret for spotipy")
        argParser.add_argument("spotify_url")
        return argParser.parse_args(cmdLine)

    def runSpotDl(self, cmdLine, spotifyClient: SpotifyClient, downloader):
        '''
        This is where all the console processing magic happens.
        Its super simple, rudimentary even but, it's dead simple & it works.
        '''

        cliArgs = self._parseArgs(cmdLine)
        if cliArgs.help or cliArgs.h:
            print(SpotDlApp.help_notice)
            sys.exit(0)

        if cliArgs.clientId and not cliArgs.clientSecret:
            sys.exit("Must supply either BOTH clientId and clientSecret, or neither.")
        elif cliArgs.clientSecret and not cliArgs.clientId:
            sys.exit("Must supply either BOTH clientId and clientSecret, or neither.")
    
        if (cliArgs.clientId and cliArgs.clientSecret):
            spotifyClientId = cliArgs.clientId
            spotifyClientSecret = cliArgs.clientSecret
        else:
            spotifyClientId = SpotDlApp.default_client_id
            spotifyClientSecret = SpotDlApp.default_client_secret
        spotifyClient.initialize(
            clientId = spotifyClientId,
            clientSecret = spotifyClientSecret
        )

        spotifyUrl = cliArgs.spotify_url
        if 'open.spotify.com' in spotifyUrl and 'track' in spotifyUrl:
            print('Fetching Song...')
            song = SongObj.from_url(spotifyUrl, spotifyClient.get_spotify_client())

            if song.get_youtube_link() != None:
                downloader.download_single_song(song)
            else:
                print('Skipping %s (%s) as no match could be found on youtube' % (
                    song.get_song_name(), spotifyUrl
                ))
        
        elif 'open.spotify.com' in spotifyUrl and 'album' in spotifyUrl:
            print('Fetching Album...')
            songObjList = get_album_tracks(spotifyUrl, spotifyClient.get_spotify_client())

            downloader.download_multiple_songs(songObjList)
        
        elif 'open.spotify.com' in spotifyUrl and 'playlist' in spotifyUrl:
            print('Fetching Playlist...')
            songObjList = get_playlist_tracks(spotifyUrl, spotifyClient.get_spotify_client())

            downloader.download_multiple_songs(songObjList)
        
        elif spotifyUrl.endswith('.spotdlTrackingFile'):
            print('Preparing to resume download...')
            downloader.resume_download_from_tracking_file(spotifyUrl)
        
        else:
            print('Searching for song "%s"...' % spotifyUrl)
            try:
                song = search_for_song(spotifyUrl, spotifyClient.get_spotify_client())
                downloader.download_single_song(song)

            except Exception:
                print('No song named "%s" could be found on spotify' % spotifyUrl)
    
        downloader.close()