"""
Module that holds the ProgressHandler class and Song Tracker class.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from rich import get_console
from rich.console import JustifyMethod, OverflowMethod
from rich.highlighter import Highlighter
from rich.markup import escape
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskID,
    TimeRemainingColumn,
)
from rich.style import StyleType
from rich.text import Text

from spotdl.types.song import Song
from spotdl.utils.static import BAD_CHARS

__all__ = [
    "ProgressHandler",
    "SongTracker",
    "ProgressHandlerError",
    "SizedTextColumn",
]

logger = logging.getLogger(__name__)


class ProgressHandlerError(Exception):
    """
    Base class for all exceptions raised by ProgressHandler subclasses.
    """


class SizedTextColumn(ProgressColumn):
    """
    Custom sized text column based on the Rich library.
    """

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

        ### Arguments
        - text_format: The format string to use for the text.
        - style: The style to use for the text.
        - justify: The justification to use for the text.
        - markup: Whether or not the text should be rendered as markup.
        - highlighter: A Highlighter to use for highlighting the text.
        - overflow: The overflow method to use for truncating the text.
        - width: The maximum width of the text.
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

        ### Arguments
        - task: The Task to render.

        ### Returns
        - A Text object.
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
    """
    Class for handing the progress of a download, including the progress bar.
    """

    def __init__(
        self,
        simple_tui: bool = False,
        update_callback: Optional[Callable[[Any, str], None]] = None,
        web_ui: bool = False,
    ):
        """
        Initialize the progress handler.

        ### Arguments
        - simple_tui: Whether or not to use the simple TUI.
        - update_callback: A callback to call when the progress bar is updated.
        """

        self.songs: List[Song] = []
        self.song_count: int = 0
        self.overall_progress = 0
        self.overall_total = 100
        self.overall_completed_tasks = 0
        self.update_callback = update_callback
        self.previous_overall = self.overall_completed_tasks

        self.simple_tui = simple_tui
        self.web_ui = web_ui
        self.quiet = logger.getEffectiveLevel() < 10
        self.overall_task_id: Optional[TaskID] = None

        if not self.simple_tui:
            console = get_console()

            self.rich_progress_bar = Progress(
                SizedTextColumn(
                    "[white]{task.description}",
                    overflow="ellipsis",
                    width=int(console.width / 3),
                ),
                SizedTextColumn(
                    "{task.fields[message]}", width=18, style="nonimportant"
                ),
                BarColumn(bar_width=None, finished_style="green"),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeRemainingColumn(),
                # Normally when you exit the progress context manager (or call stop())
                # the last refreshed display remains in the terminal with the cursor on
                # the following line. You can also make the progress display disappear on
                # exit by setting transient=True on the Progress constructor
                transient=True,
            )

            # Basically a wrapper for rich's: with ... as ...
            self.rich_progress_bar.__enter__()

    def add_song(self, song: Song) -> None:
        """
        Adds a song to the list of songs.

        ### Arguments
        - song: The song to add.
        """

        self.songs.append(song)
        self.set_song_count(len(self.songs))

    def set_songs(self, songs: List[Song]) -> None:
        """
        Sets the list of songs to be downloaded.

        ### Arguments
        - songs: The list of songs to download.
        """

        self.songs = songs
        self.set_song_count(len(songs))

    def set_song_count(self, count: int) -> None:
        """
        Set the number of songs to download.

        ### Arguments
        - count: The number of songs to download.
        """

        self.song_count = count
        self.overall_total = 100 * count

        if not self.simple_tui:
            if self.song_count > 4:
                self.overall_task_id = self.rich_progress_bar.add_task(
                    description="Total",
                    message=(
                        f"{self.overall_completed_tasks}/{int(self.overall_total / 100)} "
                        "complete"
                    ),
                    total=self.overall_total,
                    visible=(not self.quiet),
                )

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
                logger.info(
                    "%s/%s complete", self.overall_completed_tasks, self.song_count
                )
                self.previous_overall = self.overall_completed_tasks

    def get_new_tracker(self, song: Song) -> "SongTracker":
        """
        Get a new progress tracker.

        ### Arguments
        - song: The song to track.

        ### Returns
        - A new progress tracker.
        """

        return SongTracker(self, song)

    def close(self) -> None:
        """
        Close the Tui Progress Handler.
        """

        if not self.simple_tui:
            self.rich_progress_bar.stop()

        logging.shutdown()


class SongTracker:
    """
    Class to track the progress of a song.
    """

    def __init__(self, parent, song: Song) -> None:
        """
        Initialize the Tui Song Tracker.

        ### Arguments
        - parent: The parent Tui Progress Handler.
        """

        self.parent: "ProgressHandler" = parent
        self.song = song

        # Clean up the song name
        # from weird unicode characters
        self.song_name = "".join(
            char
            for char in self.song.display_name
            if char not in [chr(i) for i in BAD_CHARS]
        )

        self.progress: int = 0
        self.old_progress: int = 0
        self.status = ""

        if not self.parent.simple_tui:
            self.task_id = self.parent.rich_progress_bar.add_task(
                description=escape(self.song_name),
                message="Download Started",
                total=100,
                completed=self.progress,
                start=False,
                visible=(not self.parent.quiet),
            )

    def update(self, message=""):
        """
        Called at every event.

        ### Arguments
        - message: The message to display.
        """

        old_message = self.status
        self.status = message

        # The change in progress since last update
        delta = self.progress - self.old_progress

        if not self.parent.simple_tui:
            # Update the progress bar
            # `start_task` called everytime to ensure progress is remove from indeterminate state
            self.parent.rich_progress_bar.start_task(self.task_id)
            self.parent.rich_progress_bar.update(
                self.task_id,
                description=escape(self.song_name),
                message=message,
                completed=self.progress,
            )

            # If task is complete
            if self.progress == 100 or message == "Error":
                self.parent.overall_completed_tasks += 1
                self.parent.rich_progress_bar.remove_task(self.task_id)
        else:
            # If task is complete
            if self.progress == 100 or message == "Error":
                self.parent.overall_completed_tasks += 1

            # When running web ui print progress
            # only one time when downloading/converting/embedding
            if self.parent.web_ui and old_message != self.status:
                logger.info("%s: %s", self.song_name, message)
            elif not self.parent.web_ui and delta:
                logger.info("%s: %s", self.song_name, message)

        # Update the overall progress bar
        if self.parent.song_count == self.parent.overall_completed_tasks:
            self.parent.overall_progress = self.parent.song_count * 100
        else:
            self.parent.overall_progress += delta

        self.parent.update_overall()
        self.old_progress = self.progress

        if self.parent.update_callback:
            self.parent.update_callback(self, message)

    def notify_error(
        self, message: str, traceback: Exception, finish: bool = False
    ) -> None:
        """
        Logs an error message.

        ### Arguments
        - message: The message to log.
        - traceback: The traceback of the error.
        - finish: Whether to finish the task.
        """

        self.update("Error")
        if finish:
            self.progress = 100

        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.exception(message)
        else:
            logger.error("%s: %s", traceback.__class__.__name__, traceback)

    def notify_download_complete(self, status="Converting") -> None:
        """
        Notifies the progress handler that the song has been downloaded.

        ### Arguments
        - status: The status to display.
        """

        self.progress = 50
        self.update(status)

    def notify_conversion_complete(self, status="Embedding metadata") -> None:
        """
        Notifies the progress handler that the song has been converted.

        ### Arguments
        - status: The status to display.
        """

        self.progress = 95
        self.update(status)

    def notify_complete(self, status="Done") -> None:
        """
        Notifies the progress handler that the song has been downloaded and converted.

        ### Arguments
        - status: The status to display.
        """

        self.progress = 100
        self.update(status)

    def notify_download_skip(self, status="Skipped") -> None:
        """
        Notifies the progress handler that the song has been skipped.

        ### Arguments
        - status: The status to display.
        """

        self.progress = 100
        self.update(status)

    def ffmpeg_progress_hook(self, progress: int) -> None:
        """
        Updates the progress.

        ### Arguments
        - progress: The progress to update to.
        """

        if self.parent.simple_tui and not self.parent.web_ui:
            self.progress = 50
        else:
            self.progress = 50 + int(progress * 0.45)

        self.update("Converting")

    def yt_dlp_progress_hook(self, data: Dict[str, Any]) -> None:
        """
        Updates the progress.

        ### Arguments
        - progress: The progress to update to.
        """

        if data["status"] == "downloading":
            file_bytes = data.get("total_bytes")
            if file_bytes is None:
                file_bytes = data.get("total_bytes_estimate")

            downloaded_bytes = data.get("downloaded_bytes")
            if self.parent.simple_tui and not self.parent.web_ui:
                self.progress = 50
            elif file_bytes and downloaded_bytes:
                self.progress = downloaded_bytes / file_bytes * 50

            self.update("Downloading")
