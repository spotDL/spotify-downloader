#===============
#=== Imports ===
#===============

from tqdm import tqdm
from rich.progress import track




#=======================
#=== Display classes ===
#=======================

def log(text, color=None, end='\n'):
    print(text, end=end)



class NewProgressBar:
    instances = []
    def __init__(self, name, start=0):
        self.__class__.instances.append(self)
        self.name = name
        self.percent = start
        self.prevPercent = start
        self.progressBar = tqdm(
            total           = 100,
            # dynamic_ncols   = True,
            # bar_format      = '{percentage:3.0f}%|{bar}|ETA: {remaining}, {rate_min}',
            # unit            = 'song',
            leave             = True,
            position        = len(self.__class__.instances)
        )
        
    def setProgress(self, percent):
        self.percent = percent
        incriment = percent - self.prevPercent
        self.prevPercent = percent
        self.progressBar.update(incriment)
        # self.updateProgress()

    # def updateProgress(self):
        # print('updating...')

    @classmethod
    def printInstances(cls):
        for instance in cls.instances:
            print(instance)

    def close(self):
        self.progressBar.close()
