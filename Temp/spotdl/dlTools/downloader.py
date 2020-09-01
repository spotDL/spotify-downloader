from multiprocessing.managers import BaseManager
from multiprocessing import Pool

from os import makedirs, remove, rename
from os.path import join, exists

from spotdl.dlTools.dlBase import *
from spotdl.providers.defaultProviders import searchProvider

# initially download to temp folder
# convert, move to top, how to shellIt?

# ALL SHELL COMMANDS ACCEPT WILDCARDS, AND DON'T ASK FOR CONFIRMATION
# COPY   SHELL    -> COPY /Y $srcDir\*.$extension $destDir
# MOVE   SHELL    -> MOVE /Y $srcDir\*.$extension $destDir
# DELETE SHELL    -> DEL  /Q $Dir

# save to .\Temp > convert > embed > mode to topDir > remove from list

class downloadTracker():

    def __init__(self, trackingFile = None, songObjList = None, outFileName = 'outfile'):
        '''
        `str` `trackingFile` : path to a .spotdlTrackingFile

        `list<songObj>` `songObjList` : a list of songObj's to download

        `str` `outfile` : name of the file to which download tracking data is
        to be written

        either `trackingFile` or `songObjList` must be passed, if both are
        passed, preference is given to `songObjList`
        '''

        self.songList = []
        self.linkList = []
        self.outfile = outFileName + '.spotdlTrackingFile'

        if trackingFile == None and songObjList == None:
            raise Exception('Either trackingFile or songObjList should' +
                'be passed')
        
        elif songObjList:
            self.songList = songObjList

            for song in self.songList:
                self.linkList.append(song.getSpotifyLink())

            self.backupToOutFile()
        
        else:
            linkListStr = open(trackingFile, 'r').read()
            self.linkList = eval(linkListStr)
            
            self.outfile = trackingFile

            def parallelLinkToSongProc(link):
                sp = searchProvider()

                return sp.searchFromUrl(link)

            processPool = Pool(8)
            self.songList = processPool.map(
                func = parallelLinkToSongProc,
                iterable = self.linkList
            )
          
    def backupToOutFile(self):
        outFile = open(self.outfile, 'w')
        outFile.write(str(self.linkList))
        outFile.close()

    def getSongList(self):
        return self.songList
    
    def notifyCompletion(self, songObj):
        for song in self.songList:
            if song.getSongName() == songObj.getSongName() and \
                song.getContributingArtists() == songObj.getContributingArtists():
                
                self.songList.remove(song)
                self.linkList.remove(song.getSpotifyLink())
                self.backupToOutFile()
                print(song.getSongName())
            
            if len(self.songList) == 0:
                remove(self.outfile)
                print('COMPLETE')

class dlManager(BaseManager): pass

dlManager.register('downloadTracker', downloadTracker)

class downloadMaster():
    poolsize = 8

    def __init__(self, trackingFile = None, songObjList = None, outFileName = 'outfile'):
        dlMan = dlManager()
        dlMan.start()

        self.tracker = dlMan.downloadTracker(trackingFile, songObjList, outFileName)
    
    def start(self):
        args = ( (song, self.tracker) for song in self.tracker.getSongList())

        self.procPool = Pool(downloadMaster.poolsize)

        print('STARTING')

        self.procPool.starmap(
            func = process,
            iterable = args
        )

        self.procPool.close()

def process(songObj, downloadController = None, folder = '.'):
    # create a temp folder if not present
    tmpPath = join(folder, 'Temp')

    if not exists(tmpPath):
        makedirs(tmpPath)

    # download song
    downloadedPath = downloadTrack(
        songObj.getYoutubeLink(),
        tmpPath
    )

    # convert to .mp3
    convertedPath = convertToMp3(
        downloadedPath,
        tmpPath
        )
        
    # if the downloaded file is .mp3, it isn't converted or is
    # overwritten by the converted .mp3 file, so we wouldn't want
    # to remove it if the paths are the same
    if convertedPath != downloadedPath:
        remove(downloadedPath)

    # embed metadata
    embedDetails(
        convertedPath,
        songObj
    )

    # rename converted file
    songRenameName = ''

    for artist in songObj.getContributingArtists():
        songRenameName += artist + ', '
    
    songRenameName = songRenameName[:-2] + ' - ' + songObj.getSongName() + '.mp3'
    renamedPath = join(folder, songRenameName.replace('"', "'").replace(':', ' -'))

    rename(convertedPath, renamedPath)

    if downloadController:
        downloadController.notifyCompletion(songObj)