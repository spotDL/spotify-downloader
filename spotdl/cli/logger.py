#===============
#=== Imports ===
#===============

# from tqdm import tqdm  # Importing breaks python package: willmcgugan/rich
from rich.progress import track
from rich.progress import Progress, BarColumn, TimeRemainingColumn
# from alive_progress import showtime



#=======================
#=== Display classes ===
#=======================

def log(text, color=None, end='\n'):
    print(text, end=end)

richProgressBar = Progress(
    "[progress.description]{task.description}",
    BarColumn(bar_width=None, style="black on black"),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn()
)
richProgressBar.__enter__()

class NewProgressBar: # Basically a wrapper to convert: with ... as ...  ->  ObjOrient     Is it Necessary?
    instances = []
    def __init__(self, name, start=0):
        self.__class__.instances.append(self)
        self.name = name
        self.percent = start
        self.prevPercent = start
        self.task = richProgressBar.add_task("[red]" + self.name, total=100)
        
        
    def setProgress(self, percent):
        self.percent = percent
        incriment = percent - self.prevPercent
        self.prevPercent = percent
        # self.progressBar.update(incriment)
        richProgressBar.update(self.task, advance=incriment)
        # self.updateProgress()

    # def updateProgress(self):
        # print('updating...')

    @classmethod
    def printInstances(cls):
        for instance in cls.instances:
            print(instance)

    def close(self):
        richProgressBar.stop()

def stop():
    richProgressBar.stop()