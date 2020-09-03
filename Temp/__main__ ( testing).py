from spotdl.utils.authorization import initialize

initialize()

from spotdl.providers.defaultProviders import searchProvider
from spotdl.utils.spotifyHelpers import getPlaylistTracks, searchForSong
from spotdl.dlTools.reDO import parallellDownload, process

from datetime import datetime

# If your from mutagen, uncomment the below and change the variable in getPlaylistTracks
# mutagen_embed_roor_link = 'https://open.spotify.com/playlist/0MsBYWcYv4sc2tr0kJnfL5?si=Ga8mTg6hRlGopVFXcKS_4g'

link1 = 'https://open.spotify.com/playlist/37i9dQZF1EpGlVPORupxY0?si=4JFPSe-ZRtu-WdH9iMadwQ'
link = 'https://open.spotify.com/playlist/37i9dQZF1EpiXbCbU404ST?si=37XXkcoTTye0eBFciHr9RA'

with open('test.spotdlTrackingFile', 'w') as file: file.write(str(getPlaylistTracks(link)))
with open('test1.spotdlTrackingFile', 'w') as file: file.write(str(getPlaylistTracks(link1)))

if __name__ == '__main__':
    st = datetime.now()
    parallellDownload(trackingFile = 'test.spotdlTrackingFile', folder = 'D:\\Test')
    parallellDownload(trackingFile = 'test1.spotdlTrackingFile', folder = 'D:\\Test')
    end = datetime.now()

    print(end - st)
