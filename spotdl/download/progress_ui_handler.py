from typing import Optional

from rich.text import Text
from rich.theme import Theme
from rich.progress import Task
from rich.console import Console
from rich.style import StyleType
from rich.highlighter import Highlighter
from rich.progress import BarColumn, TimeRemainingColumn, Progress, ProgressColumn
from rich.console import (
    JustifyMethod,
    detect_legacy_windows,
    OverflowMethod,
)

from spotdl.search import SongObject

custom_theme = Theme(
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


class YTDLLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        raise Exception(msg)


class SizedTextColumn(ProgressColumn):
    """A column containing text."""

    def __init__(
        self,
        text_format: str,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Highlighter = None,
        overflow: Optional[OverflowMethod] = None,
        width: int = 20,
    ) -> None:
        self.text_format = text_format
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        self.overflow: Optional[OverflowMethod] = overflow
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
        return text


class DisplayManager:
    def __init__(self):

        # ! Change color system if "legacy" windows terminal to prevent wrong colors displaying
        self.is_legacy = detect_legacy_windows()

        # ! dumb_terminals automatically handled by rich. Color system is too but it is incorrect
        # ! for legacy windows ... so no color for y'all.
        self.console = Console(
            theme=custom_theme, color_system="truecolor" if not self.is_legacy else None
        )

        self._rich_progress_bar = Progress(
            SizedTextColumn(
                "[white]{task.description}",
                overflow="ellipsis",
                width=int(self.console.width / 3),
            ),
            SizedTextColumn("{task.fields[message]}", width=18, style="nonimportant"),
            BarColumn(bar_width=None, finished_style="green"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            console=self.console,
            # ! Normally when you exit the progress context manager (or call stop())
            # ! the last refreshed display remains in the terminal with the cursor on
            # ! the following line. You can also make the progress display disappear on
            # ! exit by setting transient=True on the Progress constructor
            transient=self.is_legacy,
        )

        self.song_count = 0
        self.overall_task_id = None
        self.overall_progress = 0
        self.overall_total = 100
        self.overall_completed_tasks = 0
        self.quiet = False

        # ! Basically a wrapper for rich's: with ... as ...
        self._rich_progress_bar.__enter__()

    def print(self, *text, color="green"):
        """
        `text` : `any`  Text to be printed to screen
        Use this self.print to replace default print().
        """

        if self.quiet:
            return

        line = " ".join(str(item) for item in text)
        if color:
            self._rich_progress_bar.console.print(f"[{color}]{line}")
        else:
            self._rich_progress_bar.console.print(line)

    def set_song_count_to(self, song_count: int) -> None:
        """
        `int` `song_count` : number of songs being downloaded
        RETURNS `~`
        sets the size of the progressbar based on the number of songs in the current
        download set
        """

        # ! all calculations are based of the arbitrary choice that 1 song consists of
        # ! 100 steps/points/iterations
        self.song_count = song_count

        self.overall_total = 100 * song_count

        if self.song_count > 4:
            self.overall_task_id = self._rich_progress_bar.add_task(
                description="Total",
                process_id="0",
                message=f"{self.overall_completed_tasks}/{int(self.overall_total / 100)} complete",
                total=self.overall_total,
                visible=(not self.quiet),
            )

    def update_overall(self):
        """
        Updates the overall progress bar.
        """

        # If the overall progress bar exists
        if self.overall_task_id is not None:
            self._rich_progress_bar.update(
                self.overall_task_id,
                message=f"{self.overall_completed_tasks}/{int(self.overall_total / 100)} complete",
                completed=self.overall_progress,
            )

    def new_progress_tracker(self, songObj):
        """
        returns new instance of `_ProgressTracker` that follows the `songObj` download subprocess
        """
        return _ProgressTracker(self, songObj)

    def close(self) -> None:
        """
        clean up rich
        """

        self._rich_progress_bar.stop()


# ========================
# === Progress Tracker ===
# ========================


class _ProgressTracker:
    def __init__(self, parent, song_object: SongObject):
        self.parent = parent
        self.song_object = song_object

        self.progress = 0
        self.old_progress = 0
        self.download_id = 0
        self.status = ""

        self.task_id = self.parent._rich_progress_bar.add_task(
            description=song_object.display_name,
            process_id=str(self.download_id),
            message="Download Started",
            total=100,
            completed=self.progress,
            start=False,
            visible=(not self.parent.quiet),
        )

    def notify_download_skip(self) -> None:
        """
        updates progress bar to reflect a song being skipped
        """

        self.progress = 100
        self.update("Skipping")

    def ytdl_progress_hook(self, data) -> None:
        """
        Progress hook for youtube-dl. It is called each time
        bytes are read from youtube.
        """

        # ! This will be called until download is complete, i.e we get an overall

        if data["status"] == "downloading":
            file_bytes = data["total_bytes"]
            downloaded_bytes = data["downloaded_bytes"]

            if file_bytes and downloaded_bytes:
                self.progress = downloaded_bytes / file_bytes * 90

            self.update("Downloading")

    def notify_youtube_download_completion(self) -> None:
        """
        updates progresbar to reflect a audio conversion being completed
        """

        self.progress = 90  # self.progress + 5
        self.update("Converting")

    def notify_conversion_completion(self) -> None:
        """
        updates progresbar to reflect a audio conversion being completed
        """

        self.progress = 95  # self.progress + 5
        self.update("Tagging")

    def notify_download_completion(self) -> None:
        """
        updates progresbar to reflect a download being completed
        """

        # ! Download completion implie ID# tag embedding was just finished
        self.progress = 100  # self.progress + 5
        self.update("Done")

    def notify_error(self, e, tb):
        """
        `e` : error message
        `tb` : traceback
        Freezes the progress bar and prints the traceback received
        """
        self.update(message="Error " + self.status)

        message = (
            f"Error: {e}\tWhile {self.status}: {self.song_object.display_name}\n {tb}"
        )

        self.parent.print(message, color="red")

    def update(self, message=""):
        """
        Called at every event.
        """

        self.status = message

        # The change in progress since last update
        delta = self.progress - self.old_progress

        # Update the progress bar
        # ! `start_task` called everytime to ensure progress is remove from indeterminate state
        self.parent._rich_progress_bar.start_task(self.task_id)
        self.parent._rich_progress_bar.update(
            self.task_id,
            description=self.song_object.display_name,
            process_id=str(self.download_id),
            message=message,
            completed=self.progress,
        )

        # If task is complete
        if self.progress == 100 or message == "Error":
            self.parent.overall_completed_tasks += 1
            if self.parent.is_legacy:
                self.parent._rich_progress_bar.remove_task(self.task_id)

        # Update the overall progress bar
        self.parent.overall_progress += delta
        self.parent.update_overall()

        self.old_progress = self.progress
