'''
Everything that has to do with outputting information onto the screen is in this file. 
This library is completely optional to the base spotDL ecosystem but is apart of the command-line interface service.
'''


#===============
#=== Imports ===
#===============

# from tqdm import tqdm  # Importing breaks python package: willmcgugan/rich
from rich.console import Console
from datetime import datetime
import time
import logging
from rich.logging import RichHandler
from rich.progress import (
    track,
    BarColumn,
    DownloadColumn,
    TextColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    Progress,
    TaskID,
)

#=====================
#=== Setup Logger ===
#=====================

# All of this code and library loggings will output to rich's log handler.
# https://rich.readthedocs.io/en/latest/logging.html

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.ERROR, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")
log.info("Hello, World!")


#=======================
#=== Display classes ===
#=======================

class DisplayManager():
    '''
    Basically a wrapper to convert: rich's with ... as ... into new with ... as ...
    All of the process information is read from a queue and stored inside of a dict: self.currentStatus.

    queue         -> { (processID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message) } } 

    currentStatus -> { (processID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message), 'task': <_richProgressBar.task Object> } } 
    '''
    def __init__(self, queue = None):
        # self.console = Console()
        self._richProgressBar = Progress(
            TextColumn("{task.fields[processID]}", style="rgb(40,100,40)"),
            TextColumn("[white]{task.description}"), # overflow='ellipsis',
            # "[progress.description]{task.description}",
            TextColumn("[green]{task.fields[message]}"),
            BarColumn(bar_width=None, style="black on black", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            # console = self.console    # use this when self.console = Console()
            #transient=True     # Normally when you exit the progress context manager (or call stop()) the last refreshed display remains in the terminal with the cursor on the following line. You can also make the progress display disappear on exit by setting transient=True on the Progress constructor
        )
  

        self.queue = queue
        self.currentStatus = {}
        self.loggingLevel = 5 # DEBUG = 5, INFO = 4, WARNING = 3, ERROR = 2, CRITICAL = 1
        self.overallID = None
        self.overallProgress = 0
        self.overallTotal = 100
    def __enter__(self):
        # self.__init__()
        self._richProgressBar.__enter__()
        return self ## Important

    def __exit__(self, type, value, traceback):
        self._richProgressBar.stop()
        # print('Display Manager Exited')

    def print(self, *text, logLevel=5, color="green"):
        '''
        `text` : `any`  Text to be printed to screen

        `logLevel` : `int(0-5, Default=5)` Logging Level of message (Default 0)

        Use this self.print to replace default print(). 
        '''

        if logLevel <= self.loggingLevel:
            if color:
                self._richProgressBar.console.print("[" + color + "]" + str(text))
            else:
                self._richProgressBar.console.print(text)
                # self._richProgressBar.console.log("Working on job:", text)

    def get_rich(self):
        '''
        I had to
        '''
        return self._richProgressBar

    def get_self(self):
        '''Returns self'''
        return self

    def listen_to_queue(self, queue):
        '''
        `queue` : `multiprocessing.Queue`

        Lets DisplayManager instance know what queue it should be listening to
        '''
        self.queue = queue

    def remove_duplicate_messages(self, messages):
        '''
        `messages` : `list` A List of messages, each in `dict` format.

        RETURNS `messages` : `dict` Cleaned up list of messages

        Filters throught all the messages from the list and remove duplicates but leaves the latest.
        '''

        # self.print('before new list: ', messages)

        existingIDs = []
        newMessageList = []
        latestMessage = None
        for message in messages:
            messageID = list(message.keys())[0] # Gets the message's process ID
            if messageID not in existingIDs:
                existingIDs.append(messageID)

        # self.print('Gathered:', existingIDs)

        for ID in existingIDs:
            for message in messages:
                messageID = list(message.keys())[0] # Gets the message's process ID
                if messageID == ID:
                    try:
                        # print(messageID, message[messageID]['time'])
                        if message[messageID]['time'] > latestMessage[messageID]['time']:
                            latestMessage = message
                    except:
                        latestMessage = message
            newMessageList.append(latestMessage)

        # self.print('new list: ', newMessageList)

        return newMessageList



    def handle_messages(self, messages):
        '''
        `messages` : `list` A List of messages, each in `dict` format, for the mailman to sort througth.

        RETURNS `currentStatus` : `dict` Dictionary of the all processes & respective information

        Filters throught all the messages from the queue, comparing them to currentStatus dictionary, updating or creating new processes if needed.
        '''

        for message in messages:
            messageID = list(message.keys())[0] # Gets the message's process ID
            if messageID == 0:
                self.handle_misc_message(message[messageID])
            else:
                if messageID in self.currentStatus:
                    # Process alread exists. If newer than others, update accordingly
                    if message[messageID]['time'] > self.currentStatus[messageID]['time']:
                        taskID = self.currentStatus[messageID]['taskID']
                        self._richProgressBar.update(taskID, description=message[messageID]['name'], processID=str(messageID), message=message[messageID]['message'], completed=message[messageID]['progress'])
                        self.currentStatus[messageID] = message[messageID]
                else:
                    # New process has appeared in queue
                    self.currentStatus[messageID] = message[messageID]
                    taskID = self._richProgressBar.add_task(description=message[messageID]['name'], processID=str(messageID), message=message[messageID]['message'], total=100)
                self.currentStatus[messageID]['taskID'] = taskID

        self.update_overall()

        return self.currentStatus

    def handle_misc_message(self, message):
        '''
        `message` : `dict`

        Any message that did not come from a sub-process will be handled here
        '''
        if message['name'] == 'Song Count' and message['progress'] > 4:
            self.overallTotal = 100 * message['progress']
            self.overallID = self._richProgressBar.add_task(description='Total', processID=0, message='', total=self.overallTotal)

    def update_overall(self):
        '''Updates the overall progress bar.
        '''
        self.overallProgress = 0
        for processID in self.currentStatus:
            self.overallProgress += self.currentStatus[processID]['progress']
        if self.overallID:
            self._richProgressBar.update(self.overallID, completed=self.overallProgress)

    def collect_messages_from(self, queue):
        '''
        `queue` : `multiprocessing.Queue` The queue in which all the messages are emitted from the parallel processes

        RETURNS `messages` : `list` A list of all the messages gatered from the queue
        '''
        messages = []
        try:
            for _ in range(queue.qsize()):
                data = queue.get(False)
                messages.append(data)
        except:
            data = None

        return messages

    def process_monitor(self, multiprocessResult, queue = None):
        '''
        `multiprocessResult` : `multiprocessing.pool.AsyncResult` 

        `queue` : `Queue` the queue to listen to. Can alternatively be assigned through `displayManager.listen_to_queue(queue)`

        Use this function as the callback of an async multiprocessing job to monitor it & the queue
        This method is where the majority of the time is spent after the download has begun.
        '''
        if not queue:
            queue = self.queue

        while not multiprocessResult.ready():
            time.sleep(0.1)
            messages = self.collect_messages_from(queue)
            messages = self.remove_duplicate_messages(messages)
            self.handle_messages(messages)

        # Goes through queue 1 more time to ensure all messages have been gathered and processed
        time.sleep(0.1)
        messages = self.collect_messages_from(queue)
        messages = self.remove_duplicate_messages(messages)
        self.handle_messages(messages)


        # self.print('Results Ready')
        multiprocessResult.wait()
        # self.print('Results:', multiprocessResult.get())
        results = multiprocessResult.get()
        for result in results:
            if result != None:
                # self.print(result)
                log.ERROR(result)

        return results

