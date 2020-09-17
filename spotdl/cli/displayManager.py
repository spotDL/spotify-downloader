#===============
#=== Imports ===
#===============

# from tqdm import tqdm  # Importing breaks python package: willmcgugan/rich
from rich.progress import track, Progress, BarColumn, TimeRemainingColumn


#======================
#=== Initialization ===
#======================

_richProgressBar = Progress(
    "[progress.description]{task.description}",
    BarColumn(bar_width=None, style="black on black"),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn(),
    #transient=True     # Normally when you exit the progress context manager (or call stop()) the last refreshed display remains in the terminal with the cursor on the following line. You can also make the progress display disappear on exit by setting transient=True on the Progress constructor
)
_richProgressBar.__enter__()


#=======================
#=== Display classes ===
#=======================


def log(text, type=None, color=None, log_locals=False):
    '''
    Use this print to replace default print(). 
    TODO: Make output customizable, to file, pipe, etc.
    '''

    # print(text)
    if color:
        _richProgressBar.console.log("[" + color + "]Working on job:", text, log_locals=log_locals)
    else:
        _richProgressBar.console.log("Working on job:", text, log_locals=log_locals)

def print(text, type=None, color=None):
    '''
    Use this logger for debug messages. 
    TODO: Make output customizable, to file, pipe, etc.
    '''

    # print(text)
    if color:
        _richProgressBar.console.print("[" + color + "]Working on job:", text)
    else:
        _richProgressBar.console.print("Working on job:", text)
        # _richProgressBar.console.log("Working on job:", text)

class NewProgressBar: 
    '''
    Basically a wrapper to convert: with ... as ...  ->  ObjOrient class    
    Is it Necessary? IDK. Is there a better way to do it? Probably.
    '''
    _instances = []
    def __init__(self, name, start=0):
        self.__class__._instances.append(self)
        self.name = name
        self.percent = start
        self.prevPercent = start
        self.task = _richProgressBar.add_task("[green]" + self.name, total=100)
        
        
    def setProgress(self, percent):
        self.percent = percent
        # self.prevPercent = self.percent
        _richProgressBar.update(self.task, completed=self.percent)

    def done(self):
        _richProgressBar.update(self.task, visible=False)
        print("Finished Downloading")
        

    @classmethod
    def printInstances(cls):
        for instance in cls._instances:
            print(instance)


def stop():
    '''
    Must be called to de-activate rich's text formatting and resume normal termial operating
    '''
    _richProgressBar.stop()

