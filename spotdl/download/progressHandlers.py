'''
Everything that has to do with a download's .spotdlTrackingFile is in this file. 
This library is completely optional to the base spotDL download library but is crucial for the command-line service.
'''


#===============
#=== Imports ===
#===============

# from tqdm import tqdm

#! we need to import the whole shebang here to patch multiprocessing's AutoProxy.
#! Attempting to use a displayManager across multiple processes without the
#! patch will result in a 'Key Error: Autoproxy takes no key argument manager_owned'
# import multiprocessing.managers
import multiprocess.managers


#! These are not used, they're here for static type checking using mypy
from spotdl.search.songObj import SongObj
from typing import List

from os import remove

# from spotdl.cli.displayManager import DisplayManager, ProcessDisplayManager




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



