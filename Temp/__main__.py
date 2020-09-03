from spotdl.utils.authorization import initialize

initialize()

from spotdl.utils.spotifyHelpers import getPlaylistTracks
from spotdl.dlTools.reDO import parallellDownload

from datetime import datetime

# If your from mutagen, uncomment the below and change the variable in getPlaylistTracks
# mutagen_embed_roor_link = 'https://open.spotify.com/playlist/0MsBYWcYv4sc2tr0kJnfL5?si=Ga8mTg6hRlGopVFXcKS_4g'

link = 'https://open.spotify.com/playlist/4q6GdHWcJwCWchkYiulnxN?si=ryYHuJJITqKWa-o2wc4dmw'

with open('test.spotdlTrackingFile', 'w') as file: file.write(str(getPlaylistTracks(link)))

if __name__ == '__main__':
    st = datetime.now()
    parallellDownload(trackingFile = 'test.spotdlTrackingFile', folder = 'D:\\Test')
    end = datetime.now()

    print(end - st)