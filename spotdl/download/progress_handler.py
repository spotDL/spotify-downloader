import logging

from typing import Optional, List

from rich.text import Text
from rich.theme import Theme
from rich.progress import Task
from rich.console import Console
from rich.style import StyleType
from rich.highlighter import Highlighter
from rich.progress import (
    BarColumn,
    TimeRemainingColumn,
    Progress,
    ProgressColumn,
    TaskID,
)
from rich.console import (
    JustifyMethod,
    detect_legacy_windows,
    OverflowMethod,
)

from spotdl.types.song import Song

# https://github.com/python/cpython/blob/3.10/Lib/logging/__init__.py
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

LEVEL_TO_NAME = {
    CRITICAL: "CRITICAL",
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
    DEBUG: "DEBUG",
    NOTSET: "NOTSET",
}

NAME_TO_LEVEL = {
    "CRITICAL": CRITICAL,
    "FATAL": FATAL,
    "ERROR": ERROR,
    "WARN": WARNING,
    "WARNING": WARNING,
    "INFO": INFO,
    "DEBUG": DEBUG,
    "NOTSET": NOTSET,
}

THEME = Theme(
    {
        "bar.back": "grey23",
        "bar.complete": "rgb(165,66,129)",
        "bar.finished": "rgb(114,156,31)",
        "bar.pulse": "rgb(165,66,129)",
        "general": "green",
        "nonimportant": "rgb(40,100,40)",
        "progress.data.speed": "red",
        "progress.description": "none",
        "progress.download": "green",
        "progress.filesize": "green",
        "progress.filesize.total": "green",
        "progress.percentage": "green",
        "progress.remaining": "rgb(40,100,40)",
    }
)


class ProgressHandlerError(Exception):
    """
    Base class for all exceptions raised by ProgressHandler subclasses.
    """


class SizedTextColumn(ProgressColumn):
    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        overflow: Optional[OverflowMethod] = None,
        width: int = 20,
    ) -> None:
        """
        A column containing text.
        """

        self.text_format = text_format
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        self.overflow: Optional[OverflowMethod] = overflow
        self.width = width
        super().__init__()

    def render(self, task: Task) -> Text:
        """
        Render the Column.
        """

        _text = self.text_format.format(task=task)
        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)
        if self.highlighter:
            self.highlighter.highlight(text)

        text.truncate(max_width=self.width, overflow=self.overflow, pad=True)
        return text


class ProgressHandler:
    def __init__(self, log_level: int = INFO, simple_tui: bool = False):
        """
        Initialize the progress handler.
        """

        self.songs: List[Song] = []
        self.song_count: int = 0
        self.overall_progress = 0
        self.overall_total = 100
        self.overall_completed_tasks = 0
        self.previous_overall = self.overall_completed_tasks

        if log_level not in LEVEL_TO_NAME:
            raise ProgressHandlerError(f"Invalid log level: {log_level}")

        self.log_level = log_level
        self.simple_tui = simple_tui
        self.quiet = self.log_level < 10
        self.overall_task_id: Optional[TaskID] = None

        if not self.simple_tui:
            # Change color system if "legacy" windows terminal to prevent wrong colors displaying
            self.is_legacy = detect_legacy_windows()

            # dumb_terminals automatically handled by rich. Color system is too but it is incorrect
            # for legacy windows ... so no color for y'all.
            self.console = Console(
                theme=THEME, color_system="truecolor" if not self.is_legacy else None
            )

            self.rich_progress_bar = Progress(
                SizedTextColumn(
                    "[white]{task.description}",
                    overflow="ellipsis",
                    width=int(self.console.width / 3),
                ),
                SizedTextColumn(
                    "{task.fields[message]}", width=18, style="nonimportant"
                ),
                BarColumn(bar_width=None, finished_style="green"),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeRemainingColumn(),
                console=self.console,
                # Normally when you exit the progress context manager (or call stop())
                # the last refreshed display remains in the terminal with the cursor on
                # the following line. You can also make the progress display disappear on
                # exit by setting transient=True on the Progress constructor
                transient=self.is_legacy,
            )

            # Basically a wrapper for rich's: with ... as ...
            self.rich_progress_bar.__enter__()
        else:
            logging.basicConfig(
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
                level=self.log_level,
            )

    def add_song(self, song: Song) -> None:
        """
        Adds a song to the list of songs.
        """

        self.songs.append(song)
        self.set_song_count(len(self.songs))

    def set_songs(self, songs: List[Song]) -> None:
        """
        Sets the list of songs to be downloaded.
        """

        self.songs = songs
        self.set_song_count(len(songs))

    def set_song_count(self, count: int) -> None:
        """
        Set the number of songs to download.
        """

        self.song_count = count
        self.overall_total = 100 * count

        if not self.simple_tui:
            if self.song_count > 4:
                self.overall_task_id = self.rich_progress_bar.add_task(
                    description="Total",
                    message=(
                        f"{self.overall_completed_tasks}/{int(self.overall_total / 100)}"
                        "complete"
                    ),
                    total=self.overall_total,
                    visible=(not self.quiet),
                )

    def debug(self, message: str) -> None:
        """
        Debug message.
        """

        if not self.simple_tui:
            if self.log_level > DEBUG:
                return

            self.rich_progress_bar.console.print(f"[blue]{message}")
        else:
            logging.debug(message)

    def log(self, message: str) -> None:
        """
        Log message.
        """

        if not self.simple_tui:
            if self.log_level > INFO:
                return

            self.rich_progress_bar.console.print(f"[green]{message}")
        else:
            logging.info(message)

    def warn(self, message: str) -> None:
        """
        Warning message.
        """

        if not self.simple_tui:
            if self.log_level > WARNING:
                return

            self.rich_progress_bar.console.print(f"[yellow]{message}")
        else:
            logging.warning(message)

    def error(self, message: str) -> None:
        """
        Error message.
        """

        if not self.simple_tui:
            if self.log_level > ERROR:
                return

            self.rich_progress_bar.console.print(f"[red]{message}")
        else:
            logging.error(message)

    def update_overall(self) -> None:
        """
        Update the overall progress bar.
        """

        if not self.simple_tui:
            # If the overall progress bar exists
            if self.overall_task_id is not None:
                self.rich_progress_bar.update(
                    self.overall_task_id,
                    message=f"{self.overall_completed_tasks}/"
                    f"{int(self.overall_total / 100)} "
                    "complete",
                    completed=self.overall_progress,
                )
        else:
            if self.previous_overall != self.overall_completed_tasks:
                logging.info(
                    "%s/%s complete", self.overall_completed_tasks, self.song_count
                )
                self.previous_overall = self.overall_completed_tasks

    def get_new_tracker(self, song: Song):
        """
        Get a new progress tracker.
        """

        return SongTracker(self, song)

    def close(self) -> None:
        """
        Close the Tui Progress Handler.
        """

        if not self.simple_tui:
            self.rich_progress_bar.stop()
        else:
            logging.shutdown()


class SongTracker:
    def __init__(self, parent, song: Song) -> None:
        """
        Initialize the Tui Song Tracker.
        """

        self.parent = parent
        self.song = song

        self.progress: int = 0
        self.old_progress: int = 0
        self.status = ""

        if not self.parent.simple_tui:
            self.task_id = self.parent.rich_progress_bar.add_task(
                description=song.display_name,
                message="Download Started",
                total=100,
                completed=self.progress,
                start=False,
                visible=(not self.parent.quiet),
            )

    def update(self, message=""):
        """
        Called at every event.
        """

        self.status = message

        # The change in progress since last update
        delta = self.progress - self.old_progress

        if not self.parent.simple_tui:

            # Update the progress bar
            # `start_task` called everytime to ensure progress is remove from indeterminate state
            self.parent.rich_progress_bar.start_task(self.task_id)
            self.parent.rich_progress_bar.update(
                self.task_id,
                description=self.song.display_name,
                message=message,
                completed=self.progress,
            )

            # If task is complete
            if self.progress == 100 or message == "Error":
                self.parent.overall_completed_tasks += 1
                self.parent.rich_progress_bar.remove_task(self.task_id)

            # Update the overall progress bar
            self.parent.overall_progress += delta
            self.parent.update_overall()

            self.old_progress = self.progress
        else:
            # If task is complete
            if self.progress == 100 or message == "Error":
                self.parent.overall_completed_tasks += 1

            # Update the overall progress bar
            self.parent.overall_progress += delta
            self.old_progress = self.progress

            self.parent.log(f"{self.song.name} - {self.song.artist}: {message}")
            self.parent.update_overall()

    def notify_error(self, message: str, traceback: Exception) -> None:
        """
        Logs an error message.
        """

        self.update("Error")

        self.parent.debug(message)
        self.parent.error(f"{traceback.__class__.__name__}: \"{self.song.display_name}\" - {traceback}")

    def notify_download_complete(self, status="Embeding metadata") -> None:
        """
        Notifies the progress handler that the song has been downloaded.
        """

        self.progress = 95
        self.update(status)

    def notify_complete(self, status="Done") -> None:
        """
        Notifies the progress handler that the song has been downloaded and converted.
        """

        self.progress = 100
        self.update(status)

    def notify_download_skip(self, status="Skipped") -> None:
        """
        Notifies the progress handler that the song has been skipped.
        """

        self.progress = 100
        self.update(status)

    def progress_hook(self, progress: int) -> None:
        """
        Updates the progress.
        """

        self.progress = int(progress * .95)

        self.update("Downloading")
