#===============
#=== Imports ===
#===============

from spotdl.providers.defaultProviders import searchProvider
from spotdl.dlTools.dlBase import process

from multiprocessing import Pool
from multiprocessing.managers import BaseManager

from tqdm import tqdm

from os import remove



#=========================
#=== Control Variables ===
#=========================

poolSize = 8



#========================================
#=== Multiprocessing Helper Functions ===
#========================================

def getSongFromUrl(url):
    '''
    `str` `url` : spotify Url of a song

    returns an instance of `songObj` that uniquely identifies the passed
    spotify song
    '''

    sProvider = searchProvider()

    return sProvider.searchFromUrl(url)



#=======================================
#=== Multiprocessing Support Classes ===
#=======================================

class tqdmAltRate(tqdm):

    @property
    def format_dict(self):
        formatDict = super(tqdmAltRate, self).format_dict

        if formatDict['rate']:
            newRate = '{:.2f}'.format( (1/formatDict['rate']) / 60)
        else:
            newRate = '~'

        formatDict.update(rate_min = (newRate + 'min/' + formatDict['unit']))

        return formatDict

class downloadTracker():
    def __init__(self, trackingFile = None, songObjList = None):
        '''
        `str` `trackingFile` : path to a .spotdlTrackingFile, pass only if your
        trying to resume a download

        `list<songObj>` `songObjList` : a list of `songObj`'s representing songs
        to be downloaded

        tracks download progress so that it can be resumed if incomplete. Either
        `trackingFile` or `songObjectList` must be passed, if both are passed,
        priority is given to the `songObjList`, `trackingFile` is ignored
        '''

        # either trackingFile or songObjList should be passed, raise error
        # if neither is passed
        if trackingFile == None and songObjList == None:
            raise Exception('Either trackingFile or songObjList should be passed')
        
        if trackingFile and not trackingFile.endswith('.spotdlTrackingFile'):
            raise Exception('tracingFile should be a .spotdlTrackingFile')

        # downloadTracker has 3 attributes,
        # - self.songList : list<songObj> : songObj's of songs to be downloaded
        # - self.linkList : list<str>     : links of songs to be downloaded
        # - self.outfile  : str           : path to .spotdlTrackingFile
        # - self.status   : dict          : dict containing current progress status
        # - self.progressbar : tqdm       : a modified edition of tqdm

        self.status = {
            'downloading'   : 0,
            'converting'    : 0,
            'embedding'     : 0
        }

        # self.status is structured as follows:
        #
        # KEY               CONTENTS
        # downloading       no. of links currently being downloaded
        # converting        no. of links being converted after download
        # embedding         no. of links being embedded with metadata after conversion
        #
        # links are sequentially moved through each KEY, i.e. there is no
        # duplication of links across multiple KEY's). Once embedding, the link
        # is removed from self.status and also self.linkList

        # initialize attributes if songObjList is passed
        if songObjList:
            # songList
            self.songList = songObjList

            # linkList
            self.linkList = []
            
            for song in self.songList:
                self.linkList.append(song.getSpotifyLink())
            
            # outFile to be set at the end, backup links
            self.backupToOutFile()
        
        # initialize attributes if trackingFile provided
        elif trackingFile:

            # tracking file contains a list of links, read the file and
            # evaluate the list
            trackingFileHandle = open(trackingFile, 'r')

            self.linkList = eval(trackingFileHandle.read())

            trackingFileHandle.close()

            # build a songObjList
            linkToSongObjConverters = Pool(poolSize)

            self.songList = linkToSongObjConverters.map(
                func = getSongFromUrl,
                iterable = self.linkList
            )

            linkToSongObjConverters.close()
            linkToSongObjConverters.join()

        # set outfile depending on weather trackingFile has been provided
        # or not
        if trackingFile:
            self.outfile = trackingFile
        else:
            # first Song
            fSong = self.songList[0]

            self.outfile = '.\\' + fSong.getSongName() + '.spotdlTrackingFile'
        
        self.progressbar = tqdmAltRate(
            total           = len(self.linkList),
            dynamic_ncols   = True,
            bar_format      = '{desc} {percentage:3.0f}%|{bar}|ETA: {remaining_s}, {rate_min}',
            unit            = 'song'
        )
    
    def backupToOutFile(self):
        '''
        saves all the links yet to be downloaded to a .spotdlTrackingFile
        '''

        trackingFile = open(self.outfile, 'w')
        trackingFile.write(str(self.linkList))
        trackingFile.close()
    
    def getSongList(self):
        '''
        returns a `list<songObj>` containing `songObj` representations of all
        songs yet to be downloaded
        '''

        return self.songList
    
    def notifyDownloadError(self):
        '''
        updates status of download process
        '''

        self.status['downloading'] -= 1

        self.updateDisplay()

    def notifyDownloadStart(self):
        '''
        updates status of download process
        '''

        self.status['downloading'] += 1
            
        self.updateDisplay()
    
    def notifyConversionStart(self):
        '''
        updates status of download process
        '''
        
        self.status['downloading'] -= 1
        self.status['converting'] += 1
            
        self.updateDisplay()
    
    def notifyEmbeddingStart(self):
        '''
        updates status of download process
        '''

        self.status['converting'] -= 1
        self.status['embedding'] += 1
            
        self.updateDisplay()
    
    def notifyCompletion(self, songObj):
        '''
        `songObj` `songObj` : `songObj` being processed

        removes given `songObj` from download list
        '''

        for song in self.songList:
            if song.getSongName() == songObj.getSongName() and \
                song.getContributingArtists() == songObj.getContributingArtists():
                
                self.songList.remove(song)
                self.linkList.remove(song.getSpotifyLink())
                self.backupToOutFile()
            
                self.updateDisplay(songProcessingFinished = True)
    
            if len(self.songList) == 0:
                remove(self.outfile)
    
    def updateDisplay(self, songProcessingFinished = False):
        '''
        `bool` `songProcessingFinished` : indicates wether a song has been
        fully processed; `False` indicates that it has merely moved from
        one stage of processing to the next

        updates the TQDM progressbar display
        '''

        cDownloads  = self.status['downloading']
        cConverting = self.status['converting']
        cEmbedding  = self.status['embedding']

        statusString = 'D:%d C:%d E:%d' % (cDownloads, cConverting, cEmbedding)
        self.progressbar.set_description(statusString)

        if songProcessingFinished:
            self.progressbar.update(1)
        else:
            self.progressbar.update(0)

    def close(self):
        '''
        clean up and notify the user of incomplete downloads
        '''

        self.progressbar.close()

        outFileNameIndex = self.outfile.rfind('\\') + 1
        outFileName = self.outfile[outFileNameIndex:]

        if len(self.songList) > 0:
            print('\n the following songs couldn\'t be downloaded, you can resume ' +
                ' the following from %s:' % outFileName)
        
            for song in self.songList:
                print( ('\t %s' % song.getSongName()).encode() )


#======================================
#=== The Main Multiprocessing Class ===
#======================================

# parallellDownloadTracker (BELOW) is the class that actually enables the
# use of a single downloadTracker across multiple processess. a.k.a it puts
# the 'multiprocessing' in 'Multiprocessing support classes'
#
# Do note that downloadTracker can be used in single processing but it'd be
# too darn slow

class parallellDownloadTracker(BaseManager):
    # docstring
    '''
    A `BaseManager` to enable usage of `downloadTracker` across multiple
    processes.

    Use the following code and use the resulting object as you would a
    `downloadTracker`,

        # Initialize a manager

        q = parallellDownloadTracker()
        q.start()

        # get an autoproxy reference to downloadTracker object created
        # in a separate process (this means that all function calls
        # passed to it will execute in a separate process - a central
        # point of control - thereby avoiding errors and weird
        # multiprocessing behaviors)

        dlTracker = q.downloadTracker()

        # use dlTracker like a normal downloadTracker
    '''

    # do nothing
    pass

parallellDownloadTracker.register('downloadTracker', downloadTracker)



#======================================
#=== This is where the work happens ===
#======================================

download = process

def parallellDownload(trackingFile = None, songObjList = None, folder = '.'):
    '''
    `str` `trackingFile` : path to a .spotdlTrackingFile
    
    `list<songObj>` `songObjList` : a list of song objects representing songs
    to download

    `str` `folder` : path to download folder

    Either `trackingFile` or `songObjectList` must be passed, if both are
    passed, priority is given to the `songObjList`, `trackingFile` is ignored
    '''
    
    # Obtain a reference to a downloadTracker that can be used across multiple
    # processes
    rootProcess = parallellDownloadTracker()
    rootProcess.start()

    dlTracker = rootProcess.downloadTracker(trackingFile, songObjList)

    # Prepare args to be passed to each process that downloads songs
    argGenerator = (
        (song, dlTracker, folder) for song in dlTracker.getSongList()
    )

    # Download songs in parallell via a download Pool
    downloadPool = Pool(poolSize)

    downloadPool.starmap(
        func     = process,
        iterable = argGenerator
    )

    # Clean up behind you
    dlTracker.close()
    rootProcess.shutdown()

    downloadPool.close()
    downloadPool.join()