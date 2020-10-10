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
        # print('Display Manager Initialized')
        self.queue = queue
        self.current_status = {}

    def __enter__(self):
        # self.__init__()
        # print('Display Manager Entered')
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

    def print(self, *text, type=None, color="green"):
        '''
        Use this logger for debug messages. 
        TODO: Make output customizable, to file, pipe, etc.
        '''
        # color = "green"

        # print(text)
        if color:
            self._richProgressBar.console.print("[" + color + "]" + str(text))
        else:
            self._richProgressBar.console.print(""+ text)
            # self._richProgressBar.console.log("Working on job:", text)

    def get_rich(self):
        '''
        I had to
        '''
        return self._richProgressBar

    def get_self(self):
        return self

    def listen_to_queue(self, queue):
        self.queue = queue

    def filter_and_save_messages(self, messages):
        '''
        Filteres throught all the messages from the queue, comparing them to current_status dictionary, sorting out old ones, updating or creating new processes if needed 
        '''
        for message in messages:
            messageID = list(message.keys())[0]
            if messageID in self.current_status:
                # self.print('Updating existing process', message, self.current_status)
                if message[messageID]['time'] > self.current_status[messageID]['time']:
                    task = self.current_status[messageID]['task']
                    self._richProgressBar.update(task, completed=message[messageID]['progress'])
                    self.current_status[messageID] = message[messageID]
            else:
                # self.print('New process', message)
                self.current_status[messageID] = message[messageID]
                task = self._richProgressBar.add_task(message[messageID]['name'], total=100)

            self.current_status[messageID]['task'] = task
        return self.current_status


    def process_monitor(self, multiprocessResult, queue = None):
        if not queue:
            queue = self.queue

        # self.print('Proc:', multiprocessResult, multiprocessResult.ready())

        while not multiprocessResult.ready():
            time.sleep(0.1)
            messages = []
            try:
                for _ in range(queue.qsize()):
                    data = queue.get(False)
                    messages.append(data)
            except:
                data = None

            # print('refresh: not yet', messages)
            self.filter_and_save_messages(messages)
            # self.print('refresh: ', self.filter_and_save_messages(messages))

        # self.print('Results Ready')
        multiprocessResult.wait()
        self.print('Results:', multiprocessResult.get())

