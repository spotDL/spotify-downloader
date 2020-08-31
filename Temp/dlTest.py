from spotdl.utils.authorization import initialize
initialize()

from spotdl.providers.defaultProviders import searchProvider

from spotdl.dlTools.downloader import process, embedDetails

while True:
    song = searchProvider().searchFromName(input('\nsearch term: '))

    print()
    print(song.getSongName())
    print(song.getContributingArtists())
    print(song.getYoutubeLink())
    
    process(song, folder='D:\\')