#===============
#=== Imports ===
#===============

# from tqdm import tqdm  # Importing breaks python package: willmcgugan/rich
from rich.progress import track, Progress, BarColumn, TimeRemainingColumn
from datetime import datetime
import atexit

#======================
#=== Initialization ===
#======================

# def initializer():
#     global _richProgressBar
    
_richProgressBar = Progress(
    "[progress.description]{task.description}",
    BarColumn(bar_width=None, style="black on black"),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn(),
    #transient=True     # Normally when you exit the progress context manager (or call stop()) the last refreshed display remains in the terminal with the cursor on the following line. You can also make the progress display disappear on exit by setting transient=True on the Progress constructor
)
_richProgressBar.__enter__()
print('displayManager & rich Initialized  ' + str(datetime.now()))
  

def stop():
    '''
    Must be called to de-activate rich's text formatting and resume normal termial operation
    '''
    _richProgressBar.stop()
atexit.register(stop)

#=======================
#=== Display classes ===
#=======================

def log(*text, type=None, color="orange", log_locals=False):
    '''
    Use this print to replace default print(). 
    TODO: Make output customizable, to file, pipe, etc.
    '''
    # color = "orange"
    # print(text)
    if color:
        _richProgressBar.console.log("[" + color + "]Message:" + text, log_locals=log_locals)
    else:
        _richProgressBar.console.log("Message:" + text, log_locals=log_locals)

def print(text, type=None, color="green"):
    '''
    Use this logger for debug messages. 
    TODO: Make output customizable, to file, pipe, etc.
    '''
    # color = "green"

    # print(text)
    if color:
        _richProgressBar.console.print("[" + color + "]" + text)
    else:
        _richProgressBar.console.print(""+ text)
        # _richProgressBar.console.log("Working on job:", text)

class NewProgressBar: 
    '''
    Basically a wrapper to convert: with ... as ...  ->  ObjOrient class    
    Is it Necessary? IDK. Is there a better way to do it? Probably.
    '''
    _instances = []
    def __init__(self, name, start=0, total=100):
        self.__class__._instances.append(self)
        self.name = name
        self.percent = start
        self.prevPercent = start
        self.total = total
        self.task = _richProgressBar.add_task("[green]" + self.name, total=total)
        
        
    def setProgress(self, percent):
        '''
        set this progress bar's completed percentage
        '''
        self.percent = percent
        value = self.percent * self.total
        # self.prevPercent = self.percent
        _richProgressBar.update(self.task, completed=value)
        
    def update(self, value):
        '''
        same as self.setProgress() except accepts raw numercical value
        '''
        self.percent = value / self.total
        _richProgressBar.update(self.task, completed=value)

    def setTotal(self, total):
        _richProgressBar.update(self.task, total=total)

    def clear(self):
        _richProgressBar.update(self.task, completed=0)

    def reset(self):
        _richProgressBar.update(self.task, completed=0)
    
    def done(self):
        _richProgressBar.update(self.task, visible=False)
        print("Finished Downloading")

    def close(self):
        _richProgressBar.update(self.task, visible=False)
        print("Finished Downloading")



    @classmethod
    def printInstances(cls):
        for instance in cls._instances:
            print(instance)




class DisplayManager():
    def __init__(self):
        #! specializedTQDM handles most of the display details, displayManager is an
        #! additional bit of calculations to ensure that the specializedTQDM progressbar
        #! works accurately across downloads from multiple processes
        # self.progressBar = SpecializedTQDM(
        #     total           = 100,
        #     dynamic_ncols   = True,
        #     bar_format      = '{percentage:3.0f}%|{bar}|ETA: {remaining}, {rate_min}',
        #     unit            = 'song'
        # )
        self.progressBar = NewProgressBar(
            name            = "Total",
            total           = 100,
        )
        print('Display Manager Initialized')

    def set_song_count_to(self, songCount: int) -> None:
        '''
        `int` `songCount` : number of songs being downloaded

        RETURNS `~`

        sets the size of the progressbar based on the number of songs in the current
        download set
        '''

        #! all calculations are based of the arbitrary choice that 1 song consists of
        #! 100 steps/points/iterations 

        # self.progressBar.total = songCount * 100
        self.progressBar.setTotal(songCount * 100)

    def notify_download_skip(self) -> None:
        '''
        updates progress bar to reflect a song being skipped
        '''

        self.progressBar.update(100)
    
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
        print('Conversion Complete')
        self.progressBar.update(5)
    
    def notify_download_completion(self) -> None:
        '''
        updates progresbar to reflect a download being completed
        '''

        #! Download completion implie ID# tag embedding was just finished
        print('Download Complete')
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

