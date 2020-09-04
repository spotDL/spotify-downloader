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

def main():

    # we assume each argument passed is a spotifyLink or a .spotdlTrackingFile
    for arg in CLIArgs[1:]:

        if arg.startswith('https://open.spotify.com/track'):
            try:
                sProvider = searchProvider()
                song = sProvider.searchFromUrl(arg)
                download(song)
            except:
                print('could not download %s' % song.getSongName())

        elif arg.startswith('https://open.spotify.com/album'):
            try:
                albumUrlList = getAlbumTracks(arg)
                parallellDownload(linkList = albumUrlList)
            except:
                print('Could not download album: %s' % arg)
        
        elif  arg.startswith('https://open.spotify.com/playlist'):
            try:
                print('getting playlist Tracks \r', end='\r')
                playlistUrlList = getPlaylistTracks(arg)
                parallellDownload(linkList = playlistUrlList)
            except:
                print('Could not download playlist: %s' % arg)
        
        elif arg.endswith('.spotdlTrackingFile'):
            try:
                parallellDownload(trackingFile = arg)
            except:
                print('Could not process tracking file: %s' % arg)
        
        else:
            try:
                sProvider = searchProvider()
                song = sProvider.searchFromName(arg)

                download(song)
            except:
                print('Could find no song name %s on spotify' % arg)

if __name__ == "__main__":
    main()