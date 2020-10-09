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
import time



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
    def __init__(self, queue = None):
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
        self.queue = queue

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

    def get_rich(self):
        return self._richProgressBar

    def get_self(self):
        return self

    def attach_to(self, queue):
        self.queue = queue

    def monitor_processes(self, multiprocessResult, queue = None):
        if not queue:
            queue = self.queue

        print('Proc:', multiprocessResult, multiprocessResult.ready())

        while not multiprocessResult.ready():
            time.sleep(0.1)
            messages = []
            try:
                # data = q.get(False)
                # If `False`, the program is not blocked. `Queue.Empty` is thrown if
                # the queue is empty
                for _ in range(queue.qsize()):
                    data = queue.get(False)
                    messages.append(data)
            except:
                data = None

            print('refresh: not yet', messages)

        print('Results Ready')
        multiprocessResult.wait()
        print('Results:', multiprocessResult.get())

