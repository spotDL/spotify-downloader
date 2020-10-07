'''
Everything that has to do with outputting information onto the screen is in this file. 
This library is completely optional to the base spotDL ecosystem but is apart of the command-line service.
'''


#===============
#=== Imports ===
#===============

# from tqdm import tqdm  # Importing breaks python package: willmcgugan/rich
from rich.progress import track, Progress, BarColumn, TimeRemainingColumn
from rich.console import Console
from datetime import datetime




#=======================
#=== Display classes ===
#=======================

class NewProgressBar: 
    '''
    Makes a new progress bar and handles it
    '''
    _instances = []
    def __init__(self, name, richProgressBar, log = print, start=0, total=100):
        self.__class__._instances.append(self)
        self.name = name
        self.percent = start
        self.prevPercent = start
        self.total = total
        self.log = log
        self._richProgressBar = richProgressBar
        self.task = self._richProgressBar.add_task("[green]" + self.name, total=total)
        
        
    def set_by_percent(self, percent):
        '''
        set this progress bar's completed percentage
        '''
        self.percent = percent
        # self.prevPercent = self.percent
        self._richProgressBar.update(self.task, completed=percent)
        
    def set_by_incriment(self, value):
        '''
        same as self.setProgress() except accepts raw numercical value
        '''
        self.percent = value + self.percent
        self._richProgressBar.update(self.task, advance=value)

    def setTotal(self, total):
        self._richProgressBar.update(self.task, total=total)

    def clear(self):
        self._richProgressBar.update(self.task, completed=0)

    def reset(self):
        self._richProgressBar.update(self.task, completed=0)
    
    def done(self):
        self._richProgressBar.update(self.task, visible=False)
        self.log("Finished Downloading")

    def close(self):
        self._richProgressBar.update(self.task, visible=False)
        self.log("Finished Downloading")

    @classmethod
    def printInstances(cls):
        for instance in cls._instances:
            print(instance)


class DisplayManager():
    '''
    Basically a wrapper to convert: rich's with ... as ... into new with ... as ...
    '''
    def __init__(self):
        # self.a = 1
        # self.console = Console()
        self._richProgressBar = Progress(
            "[progress.description]{task.description}",
            BarColumn(bar_width=None, style="black on black"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            # console = self.console    # use this when self.console = Console()
            #transient=True     # Normally when you exit the progress context manager (or call stop()) the last refreshed display remains in the terminal with the cursor on the following line. You can also make the progress display disappear on exit by setting transient=True on the Progress constructor
        )
        print('Display Manager Initialized')
        # self.progressBar = NewProgressBar(
        #     name            = "Total",
        #     richProgressBar = self._richProgressBar,
        #     total           = 100
        # )

    def __enter__(self):
        # self.__init__()
        print('Display Manager Entered')
        self._richProgressBar.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        # _richProgressBar.__exit__()
        self._richProgressBar.stop()
        print('Display Manager Exited')

    def log(self, *text, type=None, color="orange", log_locals=False):
        '''
        Use this print to replace default print(). 
        '''
        # color = "orange"
        # print(text)
        if color:
            self._richProgressBar.console.log("[" + color + "]Message:" + text, log_locals=log_locals)
        else:
            self._richProgressBar.console.log("Message:" + text, log_locals=log_locals)

    def print(self, text, type=None, color="green"):
        '''
        Use this logger for debug messages. 
        TODO: Make output customizable, to file, pipe, etc.
        '''
        # color = "green"

        # print(text)
        if color:
            self._richProgressBar.console.print("[" + color + "]" + text)
        else:
            self._richProgressBar.console.print(""+ text)
            # self._richProgressBar.console.log("Working on job:", text)

    def GetProcessDisplayManager(self):
        print('Handing off subprocess function')
        return ProcessDisplayManager(self)

    def getrich(self):
        return self._richProgressBar

    def getself(self):
        return self




class ProcessDisplayManager():
    def __init__(self, parent):
        print('Subprocess Display Manager Initialized')
        self.progressBar = NewProgressBar( # Each process gets a progress bar
            name            = "Total",
            richProgressBar = parent._richProgressBar,
            total           = 100,
        )
        self.print = parent.print
    
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

        self.progressBar.set_by_percent(100)
    
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

        self.progressBar.set_by_incriment(iterFraction)
    
    def notify_conversion_completion(self) -> None:
        '''
        updates progresbar to reflect a audio conversion being completed
        '''
        self.print('Conversion Complete')
        self.progressBar.set_by_incriment(5)
    
    def notify_download_completion(self) -> None:
        '''
        updates progresbar to reflect a download being completed
        '''

        #! Download completion implie ID# tag embedding was just finished
        self.print('Download Complete')
        self.progressBar.set_by_incriment(5)
    
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
            

class DisplayRelay():
    def __init__(self, queue, id):
        self.q = queue
        self.id = id

        
