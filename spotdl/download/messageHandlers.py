'''
Everything that has to do with multi-process communication is in this file. 
'''

#===============
#=== Imports ===
#===============

import time
import sys
from datetime import datetime


#============================================
#=== Subprocess Reporting to Main Process ===
#============================================

class ParentMessageTracker():
    '''
    This Class is an placeholder for the shared message_queue & overall progress information.
    It is also responsible for dispatching Process Trackers.
    '''

    def __init__(self, message_queue, lock = None):
        self.message_queue = message_queue
        self.overallProgress = 0
        self.overallTotal = 100
        self.lock = lock

    def set_song_count_to(self, count: int):
        '''
        `count` : `int` The numbers of songs the current download Pool has mapped

        Sets the current song count so that the DisplayManager can estimate an overall progress indicator.
        '''
        self.overallTotal = 100 * count
        self.put('0', 'Song Count', count)

    def put(self, ID: str, name: str, progress, message = ''):
        '''
        `ID` : `str` Current process ID

        `name` : `str` Display Name

        `progress` : 'int` 0-100 

        `message` : `str` (Optional) Message to display
        
        queue -> `{ (processID): { 'time': (timestamp), 'name': (display name), 'progress': (0-100), 'message': (message) } }`
        '''

        message = { ID: { 'time': datetime.timestamp(datetime.now()), 'name': name, 'progress': int(progress), 'message': message}}
        self.message_queue.put(message)

    def newMessageTracker(self, name):
        '''
        Dispatch a new Message Plugin

        `RETURNS` `DownloadMessagesPlugin` instance with `self` (`self.put()` method) already passed into it.
        '''
        return MessagesTrackerPlugin(self, name)
    
class MessagesTrackerPlugin():
    '''
    A Plugin for handling callback events from each download process seperately. 
    Each function here corresponds to a function that is called throughout the main download process.
    This class handles things such as displayName, processProgress, processMessages, etc.
    A New message Tracker object is created for each download process and passed into it upon creation.
    '''

    def __init__(self, parent, displayName):
        self.parent = parent
        self.displayName = displayName
        self.ID = None
        self.progress = 0
        self.isComplete = False
        # print('New Tracker Initialized')
        # self.total = 100

    def notify_download_begin(self, ID: str):
        '''
        `ID` : `int` Process ID of download process

        RETURNS `~`

        Should be called at the beginning of each download
        '''
        self.ID = ID
        self.send_update('Download Started')


    def set_song_count_to(self, songCount: int) -> None:
        '''
        `songCount` : `int` number of songs being downloaded

        RETURNS `~`

        sets the size of the progressbar based on the number of songs in the current
        download set
        '''

        #! all calculations are based of the arbitrary choice that 1 song consists of
        #! 100 steps/points/iterations 

        self.parent.overallTotal = songCount * 100
        self.send_update('Song Count now' + str(songCount))

    def notify_download_skip(self) -> None:
        '''
        updates progress bar to reflect a song being skipped
        '''

        # self.progressBar.set_by_percent(100)
        self.progress = 100
        self.isComplete = True
        self.send_update('Skipping')

    def download_progress_hook(self, stream, chunk, bytes_remaining) -> None:
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

        self.progress += iterFraction
        # if not int(self.progress) % 10:
        self.send_update('Downloading...')

    def notify_download_completion(self) -> None:
        '''
        updates progresbar to reflect a download being completed. 
        '''
        self.progress = 90
        self.send_update('Converting...') # Download Complete, Converting...
    
    def notify_conversion_completion(self) -> None:
        '''
        updates progresbar to reflect a audio conversion being completed
        '''

        self.progress = 95
        self.send_update('Tagging...') # Conversion Complete, Tagging...

    def notify_finished(self):
        '''
        updates progres to show the process is completed
        '''
        self.isComplete = True
        self.progress = 100
        # self.send_update('Finished Tagging')
        # time.sleep(0.01) # Or else the messages will not be distinguishable from a timestamp sort
        self.send_update('Done') # finished Tagging

    def notify_error(self, pid, e, tb=''):
        '''
        Reports error message to queue
        '''
        self.send_update(message='Error')
        self.parent.put(ID='0', name='Error', progress=pid, message=str(e) + " - " + str(tb))

    def send_update(self, message = ''):
        '''
        Called everytime the user should be notified.
        This is where the communication information layout is defined.
        queue -> { (processID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message) } }
        '''
        if self.parent.lock:
            self.parent.lock.acquire()
        # self.parent.message_queue.put(line2) #, block=False
        self.parent.put(self.ID, self.displayName, self.progress, message)
        if self.parent.lock:
            self.parent.lock.release()

            
    def close(self) -> None:
        '''
        clean up and exit
        '''

        self.send_update('Leaving Display Manager')