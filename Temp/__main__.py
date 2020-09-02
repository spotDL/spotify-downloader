from spotdl.utils.authorization import initialize

initialize()

from spotdl.utils.spotifyHelpers import getPlaylistTracks
from spotdl.dlTools.reDO import parallellDownload

from datetime import datetime

#with open('test.spotdlTrackingFile', 'w') as file: file.write(str(getPlaylistTracks('https://open.spotify.com/playlist/4q6GdHWcJwCWchkYiulnxN?si=5oT_2WirRMWk4zWoVnj4lQ')))

if __name__ == '__main__':
    st = datetime.now()
    parallellDownload(trackingFile = 'test.spotdlTrackingFile', folder = 'D:\\Test')
    end = datetime.now()

    print(end - st)