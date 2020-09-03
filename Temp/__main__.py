#===============
#=== Imports ===
#===============

from sys import argv as CLIArgs

# if we don't initialize spotdl first, just about every
# import from spotdl will raise an error
from spotdl.utils.authorization import initialize
initialize()

from spotdl.utils.spotifyHelpers import getAlbumTracks, getPlaylistTracks
from spotdl.providers.defaultProviders import searchProvider
from spotdl.dlTools.downloader import download, parallellDownload


#===========================
#=== Our dead simple CLI ===
#===========================

if __name__ == "__main__":

    # we assume each argument passed is a spotifyLink
    for arg in CLIArgs[1:]:
        try:

            if arg.startswith('http://open.spotify.com/track'):
                sProvider = searchProvider()
                song = sProvider.searchFromUrl(arg)
                download(song)

            elif arg.startswith('http://open.spotify.com/album'):
                albumUrlList = getAlbumTracks(arg)
                parallellDownload(linkList = albumUrlList)

            elif  arg.startswith('http://open.spotify.com/playlist'):
                playlistUrlList = getPlaylistTracks(arg)
                parallellDownload(linkList = playlistUrlList)

            elif arg.endswith('spotdlTrackingFile'):
                parallellDownload(trackingFile = arg)

            else:
                print('unknown argument, not recognized: %s' % arg)
        
        except:
            print('argument could not be processed: %s' % arg)