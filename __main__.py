from spotdl.search.spotifyClient import initialize

from spotdl.search.utils import get_playlist_tracks

from spotdl.download.downloader import DownloadManager
from spotdl.search.songObj import SongObj

if __name__ == '__main__':
    initialize(
        clientId='4fe3fecfe5334023a1472516cc99d805',
        clientSecret='0f02b7c483c04257984695007a4a8d5c'
        )

    #cp = [
    #'https://open.spotify.com/playlist/4q6GdHWcJwCWchkYiulnxN?si=5MA4InKgRSWnfT344UDzMw',
    #'https://open.spotify.com/playlist/0pIwglF2dofjZRBb2ZcboR?si=6zcqKDmXRx6fWefulmxwvg',
    #'https://open.spotify.com/playlist/37i9dQZF1EpiXbCbU404ST?si=sdOo_mN-TcGNla4roiuJFQ',
    #'https://open.spotify.com/playlist/2GNgOMv4JMkv96wsOo64Wx?si=1f02HuudQr244xMMSgq9lA',
    #'https://open.spotify.com/playlist/37i9dQZF1EpGlVPORupxY0?si=wytPwJA4SvKk1UVjRhnOLw',
    #'https://open.spotify.com/playlist/37i9dQZF1EpiXbCbU404ST?si=-vUDyYAJQ2q0tKaaZ9VCfQ'
    #]

    #songObjList = []

    #print('Fetching playlist...')
    #for each in cp:
    #    print('Fetching: %s...' % each)
    #    songObjList += get_playlist_tracks(each)

    man = DownloadManager()

    #song = SongObj.from_url('https://open.spotify.com/track/0m3offEyxRFE41CG2UQKBp?si=XImR7iMrS1Crgproz4dfCQ')
    #man.download_single_song(song)

    #man.download_multiple_songs(songObjList)
    man.resume_download_from_tracking_file('multiList.spotdlTrackingFile')
    #man.resume_download_from_tracking_file("Losing Hold (feat. Austin Jenckes).spotdlTrackingFile")
