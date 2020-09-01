from spotdl.utils.authorization import initialize
initialize()

from datetime import datetime

from spotdl.providers.defaultProviders import searchProvider
from spotdl.utils.spotifyHelpers import getAlbumTracks
from spotdl.dlTools.downloader import process, embedDetails, downloadMaster

#with open('test.spotdlTrackingFile', 'w') as file: file.write(str(getAlbumTracks('https://open.spotify.com/album/2YMWspDGtbDgYULXvVQFM6?si=fDgELmQNQMa8bdhWCc6OXQ')))

if __name__ == '__main__':
    t1 = datetime.now()
    sp = searchProvider()

    songs = eval(open('test.spotdlTrackingFile', 'r').read())
    print('STARTING')

    for each in songs:
        song = sp.searchFromUrl(each)
        process(song, folder='.\\SingleProc')
        print(song.getSongName())
    t2 = datetime.now()
    w = downloadMaster('test.spotdlTrackingFile')
    w.start()
    t3 = datetime.now()

    print(t2-t1)
    print(t3-t2)

# while True:
#     try:
#         song = searchProvider().searchFromName(input('\nsearch term: '))
# 
#         print()
#         print(song.getSongName())
#         print(song.getContributingArtists())
#         print(song.getYoutubeLink())
# 
#         process(song, folder='D:\\')
#     except:
#         print('Error')