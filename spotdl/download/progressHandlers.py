#===============
#=== Imports ===
#===============

from tqdm import tqdm

#! we need to import the whole shebang here to patch multiprocessing's AutoProxy.
#! Attempting to use a displayManager across multiple processes without the
#! patch will result in a 'Key Error: Autoproxy takes no key argument manager_owned'
import multiprocessing.managers

#! These are not used, they're here for static type checking using mypy
from spotdl.search.songObj import SongObj
from typing import List

from os import remove



#=================
#=== The Patch ===
#=================
originalAutoproxy = multiprocessing.managers.AutoProxy

def patchedAutoproxy(token, serializer, manager=None,
    authkey=None,exposed=None, incref=True, manager_owned=True):
    '''
    A patch to `multiprocessing.managers.AutoProxy`
    '''

    #! we bypass the unwanted key argument here
    return originalAutoproxy(token, serializer, manager, authkey, exposed, incref)

#! Update the Autoproxy definition in multiprocessing.managers package
multiprocessing.managers.AutoProxy = patchedAutoproxy



#=======================
#=== Display classes ===
#=======================

class SpecializedTQDM(tqdm):

    @property
    def format_dict(self):
        formatDict = super(SpecializedTQDM, self).format_dict

        #! 1/rate is the time it takes to finish 1 iteration (secs). The displayManager
        #! for which specializedTQDM is built works on the assumption that 100 iterations
        #! makes one song downloaded. Hence the time in seconds per song would be
        #! 100 * (1/rate) and in minuts would be 100/ (60 * rate)
        if formatDict['rate']:
            newRate = '{:.2f}'.format(100 / (60 * formatDict['rate'] ))
        else:
            newRate = '~'

        formatDict.update(rate_min = (newRate + 'min/' + formatDict['unit']))

        #! You can now use {rate_min} as a formatting arg to get rate in mins/unit

        return formatDict

class DisplayManager():
    def __init__(self):
        #! specializedTQDM handles most of the display details, displayManager is an
        #! additional bit of calculations to ensure that the specializedTQDM progressbar
        #! works accurately across downloads from multiple processes
        self.progressBar = SpecializedTQDM(
            total           = 100,
            dynamic_ncols   = True,
            bar_format      = '{percentage:3.0f}%|{bar}|ETA: {remaining}, {rate_min}',
            unit            = 'song'
        )

    def set_song_count_to(self, songCount: int) -> None:
        '''
        `int` `songCount` : number of songs being downloaded

        RETURNS `~`

        sets the size of the progressbar based on the number of songs in the current
        download set
        '''

        #! all calculations are based of the arbitrary choice that 1 song consists of
        #! 100 steps/points/iterations 
        self.progressBar.total = songCount * 100

    def notify_download_skip(self) -> None:
        '''
        updates progress bar to reflect a song being skipped
        '''

        self.progressBar.update(5)
    
    def pytube_progress_hook(self, stream, chunk, bytes_remaining) -> None:
        '''
        Progress hook built according to pytube's documentation. It is called each time
        bytes are read from youtube.
        '''

        #! This will be called until download is complete, i.e we get an overall
        #! self.progressBar.update(90)

        fileSize = stream.filesize

        #! How much of the file was downloaded this iteration scaled put of 90.
        #! It's scaled to 90 because, the arbitrary division of each songs 100
        #! iterations is (a) 90 for download (b) 5 for conversion & normalization
        #! and (c) 5 for ID3 tag embedding
        iterFraction = len(chunk) / fileSize * 90

        self.progressBar.update(iterFraction)
    
    def notify_conversion_completion(self) -> None:
        '''
        updates progresbar to reflect a audio conversion being completed
        '''

        self.progressBar.update(5)
    
    def notify_download_completion(self) -> None:
        '''
        updates progresbar to reflect a download being completed
        '''

        #! Download completion implie ID# tag embedding was just finished
        self.progressBar.update(5)
    
    def reset(self) -> None:
        '''
        prepare displayManager for a new download set. call
        `displayManager.set_song_count_to` before next set of downloads for accurate
        progressbar.
        '''

        self.progressBar.reset()
    
    def clear(self) -> None:
        '''
        clear the tqdm progress bar
        '''

        self.progressBar.clear()
    
    def close(self) -> None:
        '''
        clean up TQDM
        '''

        self.progressBar.close()



#===============================
#=== Download tracking class ===
#===============================

class DownloadTracker():
    def __init__(self):
        self.songObjList = []
        self.saveFile = None
    
    def load_tracking_file(self, trackingFilePath: str) -> None:
        '''
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        RETURNS `~`

        reads songsObj's from disk and prepares to track their download
        '''

        # Attempt to read .spotdlTrackingFile, raise exception if file can't be read
        try:
            file = open(trackingFilePath, 'rb')
            songDataDumps = eval(file.read().decode())
            file.close()
        except FileNotFoundError:
            raise Exception('no such tracking file found: %s' % trackingFilePath)
        
        # Save path to .spotdlTrackingFile
        self.saveFile = trackingFilePath

        # convert song data dumps to songObj's
        #! see, songObj.get_data_dump and songObj.from_dump for more details
        for dump in songDataDumps:
            self.songObjList.append( SongObj.from_dump(dump) )
    
    def load_song_list(self, songObjList: List[SongObj]) -> None:
        '''
        `list<songOjb>` `songObjList` : songObj's being downloaded

        RETURNS `~`

        prepares to track download of provided songObj's
        '''

        self.songObjList = songObjList

        self.backup_to_disk()
    
    def get_song_list(self) -> List[SongObj]:
        '''
        RETURNS `list<songObj>

        get songObj's representing songs yet to be downloaded
        '''
        return self.songObjList
    
    def backup_to_disk(self):
        '''
        RETURNS `~`

        backs up details of songObj's yet to be downloaded to a .spotdlTrackingFile
        '''
        # remove tracking file if no songs left in queue
        #! we use 'return None' as a convenient exit point
        if len(self.songObjList) == 0:
            remove(self.saveFile)
            return None




        # prepare datadumps of all songObj's yet to be downloaded
        songDataDumps = []

        for song in self.songObjList:
            songDataDumps.append(song.get_data_dump())
        
        #! the default naming of a tracking file is $nameOfFirstSOng.spotdlTrackingFile,
        #! it needs a little fixing because of disallowed characters in file naming
        if not self.saveFile:
            songName = self.songObjList[0].get_song_name()

            for disallowedChar in ['/', '?', '\\', '*','|', '<', '>']:
                if disallowedChar in songName:
                    songName = songName.replace(disallowedChar, '')
            
            songName = songName.replace('"', "'").replace(': ', ' - ')

            self.saveFile = songName + '.spotdlTrackingFile'
        


        # backup to file
        #! we use 'wb' instead of 'w' to accommodate your fav K-pop/J-pop/Viking music
        file = open(self.saveFile, 'wb')
        file.write(
            str(songDataDumps).encode()
        )
        file.close()
    
    def notify_download_completion(self, songObj: SongObj) -> None:
        '''
        `songObj` `songObj` : songObj representing song that has been downloaded

        RETURNS `~`

        removes given songObj from download queue and updates .spotdlTrackingFile
        '''

        if songObj in self.songObjList:
            self.songObjList.remove(songObj)
        
        self.backup_to_disk()
    
    def clear(self):
        self.songObjList = []
        self.saveFile = None



#===============================================
#=== Enabling work across multiple processes ===
#===============================================

#! we actually run displayManagers and downloadTrackers in a separate process and pass
#! reference handles of those objects to various processes. Thats handled by a
#! BaseManager, i.e. this part of the file. Every bit of the above classes is designed
#! to work across multiple processes and work accurately but, this is the part that
#! puts multiprocessing into the picture

class ProgressRootProcess(multiprocessing.managers.BaseManager): pass

ProgressRootProcess.register('DownloadTracker', DownloadTracker)
ProgressRootProcess.register('DisplayManager',  DisplayManager)

#! You can now run the following code to work with both DisplayManagers and
#! DownloadTrackers:
#!
#!          rootProc = progressRootProcess()
#!          rootProc.start()
#!
#!          displayManager  = rootProc.DisplayManager()
#!          downloadTracker = rootProc.DownloadTracker()
#!
#! The returned objects will be instances of AutoProxy but you can use them like a normal
#! DisplayManager or DowloadTracker