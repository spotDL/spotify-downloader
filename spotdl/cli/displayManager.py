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
    ProgressColumn
)
from rich.theme import Theme
from rich.style import StyleType
from rich.console import (
    Console,
    ConsoleRenderable,
    JustifyMethod,
    RenderableType,
    RenderGroup,
    RenderHook,
)
from rich.highlighter import Highlighter
from rich.text import Text



#=============
#=== Theme ===
#==============

custom_theme = Theme({
    "general" : "green",
    "nonimportant" : "rgb(40,100,40)",
    "progress.data.speed" : "red",
    "progress.description" : "none",
    "progress.download" : "green",
    "progress.filesize" : "green",
    "progress.filesize.total" : "green",
    "progress.percentage" : "green",
    "progress.remaining" : "rgb(40,100,40)"
})


#=====================
#=== Setup Logger ===
#=====================

# All of this code and library loggings will output to rich's log handler.
# https://rich.readthedocs.io/en/latest/logging.html

def setup_log(level=logging.ERROR, filename=None, fileonly: bool =False):
    global log

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Reconfigure root logging config
    FORMAT = "%(message)s"
    if filename:
        if fileonly:
            logging.basicConfig(
                level=level, format=FORMAT, datefmt="[%X]", handlers=[logging.FileHandler(filename="debug.log",)] # level=logging.ERROR, 
            )
        else:
            logging.basicConfig(
                level=level, format=FORMAT, datefmt="[%X]", handlers=[RichHandler(), logging.FileHandler(filename="debug.log",)] # level=logging.ERROR, 
            )
    else:
        logging.basicConfig(
            level=level, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()] # level=logging.ERROR, 
        )

    log = logging.getLogger("rich")
    # log.setLevel(level=logging.NOTSET)
    log.info('Hello, World!')


#========================================================
#=== Modified rich Text Column to Support Fixed Width ===
#========================================================

class SizedTextColumn(ProgressColumn):
    """A column containing text."""

    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Highlighter = None,
        overflow: "OverflowMethod" = "ellipsis",
        width: int = 20
    ) -> None:
        self.text_format = text_format
        self.justify = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        self.overflow = overflow,
        self.width = width
        super().__init__()

    def render(self, task: "Task") -> Text:
        _text = self.text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)

        text.truncate(max_width=self.width, overflow=self.overflow, pad=True)
        # text.align(align="left", width=self.width)
        return text



#=======================
#=== Display classes ===
#=======================

class DisplayManager():
    '''
    Basically a wrapper to convert: rich's with ... as ... into new with ... as ...
    All of the process information is read from a queue and stored inside of a dict: self.currentStatus
    '''
    def __init__(self, queue = None):
        self.console = Console(theme = custom_theme)
        self._richProgressBar = Progress(
            SizedTextColumn("{task.fields[processID]}", style="nonimportant", width=7),
            SizedTextColumn("[white]{task.description}", overflow="ellipsis", width=60), # overflow='ellipsis',
            # "[progress.description]{task.description}",
            SizedTextColumn("{task.fields[message]}", width=18, style="nonimportant"),
            BarColumn(bar_width=None, style="black on black", finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            console = self.console    # use this when self.console = Console()
            #transient=True     # Normally when you exit the progress context manager (or call stop()) the last refreshed display remains in the terminal with the cursor on the following line. You can also make the progress display disappear on exit by setting transient=True on the Progress constructor
        )

        self.queue = queue
        self.currentStatus = {}
        self.overallID = None
        self.overallProgress = 0
        self.overallTotal = 100
        self.overallCompletedTasks = 0
        setup_log()

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

        Use this self.print to replace default print(). 
        '''

        line = ''
        for item in text:
            line += str(item) + ' '

        if color:
            self._richProgressBar.console.print("[" + color + "]" + str(line))
        else:
            self._richProgressBar.console.print(line)
            # self._richProgressBar.console.log("Working on job:", text)

    def string_column(self, size: int, data: str) -> str:
        '''
        `size` : `int` Length of string

        `data` : `str` Makes string length of `size`
        '''
        return (data[:size-3] + '...') if len(data) > size else data.ljust(size)

    def set_log_level(self, scope='local', level=logging.DEBUG) -> None:
        '''
        `level` : logging level to set

        This is set to change the global logging level. If any files, modules, or libraries use the logging package, it will be outputted. here.
        '''
        log.debug('Debug mode turning on...')
        if scope == 'global':
            setup_log(level=level, filename='debug.log')  # All logging logs
        elif scope == 'file':
            setup_log(level=level, filename='debug.log', fileonly=True)
        else:
            log.setLevel(level=logging.DEBUG)

            
        # if logging.getLogger().isEnabledFor(logging.INFO):  # If log level is INFO or higher
        log.debug('Log level is set')
        log.debug('Debug')
        log.info('Info')
        log.warning('Warning')
        log.error('Error')
        log.critical('Critical')

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

        RETURNS `newMessageList` : `list` Cleaned up list of `dict` messages

        Filters through all the messages from the list and remove duplicates but leaves the latest.
        '''

        # self.print('before new list: ', messages)
        log.info('before new list: ' + str(messages) )

        existingIDs = []
        newMessageList = []
        latestMessage = None
        for message in messages:
            downloadID = list(message.keys())[0] # Gets the message's process ID
            if downloadID not in existingIDs:
                existingIDs.append(downloadID)

        # self.print('Gathered:', existingIDs)

        for ID in existingIDs:
            for message in messages:
                downloadID = list(message.keys())[0] # Gets the message's process ID
                if downloadID == ID:
                    try:
                        # print(downloadID, message[downloadID]['time'])
                        if message[downloadID]['time'] >= latestMessage[downloadID]['time']:
                            latestMessage = message
                    except:
                        latestMessage = message
            newMessageList.append(latestMessage)

        # self.print('new list: ', newMessageList)
        log.info('new list: ' + str(newMessageList) )

        return newMessageList


    def handle_messages(self, messages):
        '''
        `messages` : `list` A List of messages, each in `dict` format, for the mailman to sort through.

        RETURNS `currentStatus` : `dict` Dictionary of the all processes & respective information

        Filters through all the messages from the queue, comparing them to currentStatus dictionary, updating or creating new processes if needed.
        
        messages (from queue) -> [ { int(downloadID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message) } }, ...]

        currentStatus -> [ { str(downloadID): { 'time': (timestamp), 'name': (display name), 'progress': (int: 0-100), 'message': (str: message), 'task': <_richProgressBar.task Object> } }, ...] 
        '''

        for message in messages:
            downloadID = list(message.keys())[0] # Gets the message's process ID
            if downloadID == '0':
                self.handle_misc_message(message[downloadID])
            else:
                if downloadID in self.currentStatus:
                    # Process already exists. If newer than others, update accordingly
                    # if message[downloadID]['time'] > self.currentStatus[downloadID]['time']:
                    taskID = self.currentStatus[downloadID]['taskID']
                    self._richProgressBar.start_task(taskID)
                    self._richProgressBar.update(taskID, description=message[downloadID]['name'], processID=str(downloadID), message=message[downloadID]['message'], completed=message[downloadID]['progress'])
                    self.currentStatus[downloadID] = message[downloadID]
                else:
                    # New process has appeared in queue
                    self.currentStatus[downloadID] = message[downloadID]
                    taskID = self._richProgressBar.add_task(description=message[downloadID]['name'], processID=str(downloadID), message=message[downloadID]['message'], total=100, completed=message[downloadID]['progress'], start=False)
                    if message[downloadID]['message'] != "Download Started":
                        self._richProgressBar.start_task(taskID)


                if message[downloadID]['progress'] == 100:
                    self.overallCompletedTasks += 1
                self.currentStatus[downloadID]['taskID'] = taskID

        self.update_overall()

        return self.currentStatus

    def handle_misc_message(self, message):
        '''
        `message` : `dict`

        Any message that did not come from a sub-process will be handled here: ( {ID: 0 {...} )
        '''
        if message['name'] == 'Song Count' and message['progress'] >= 4:
            # self.print('Total songs:',  message['progress'])
            self.overallTotal = 100 * message['progress']
            self.overallID = self._richProgressBar.add_task(description='Total', processID='0', message='', total=self.overallTotal)
        elif message['name'] == 'Error' or message['message']:
            self.print('PID:', message['progress'], 'Error:', message['message'])

    def update_overall(self):
        '''Updates the overall progress bar.
        '''
        self.overallProgress = 0
        for processID in self.currentStatus:
            self.overallProgress += self.currentStatus[processID]['progress']
        if self.overallID != None:  # If the overall progress bar exists
            # log.info('Updating total to:' + str(self.overallProgress) )
            self._richProgressBar.update(self.overallID, message=str(self.overallCompletedTasks) + '/' + str(int(self.overallTotal/100)) + " complete", completed=self.overallProgress)

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
            time.sleep(0.01)
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
        if isinstance(results, list): 
            for result in results:
                if result != None:
                    # self.print(result)
                    log.ERROR(result)
        else:
            result = results
            if result != None:
                log.ERROR(result)

        return results

