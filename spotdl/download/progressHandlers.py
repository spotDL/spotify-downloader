# ===============
# === Imports ===
# ===============

from rich.console import Console
from rich.progress import BarColumn, TimeRemainingColumn, Progress, ProgressColumn
from rich.progress import Task
from rich.theme import Theme
from rich.style import StyleType
from rich.console import (
    JustifyMethod,
    detect_legacy_windows,
    OverflowMethod,
)
from rich.highlighter import Highlighter
from rich.text import Text

# ! These are not used, they're here for static type checking using mypy
from spotdl.search.songObj import SongObj
from typing import (
    List,
    Optional,
)
from pathlib import Path


# =============
# === Theme ===
# =============

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


# ========================================================
# === Modified rich Text Column to Support Fixed Width ===
# ========================================================


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
        self.justify = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        self.overflow = overflow
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


# =======================
# === Display Manager ===
# =======================


class DisplayManager:
    def __init__(self):

        # ! Change color system if "legacy" windows terminal to prevent wrong colors displaying
        self.isLegacy = detect_legacy_windows()

        # ! dumb_terminals automatically handled by rich. Color system is too but it is incorrect
        # ! for legacy windows ... so no color for y'all.
        self.console = Console(
            theme=custom_theme, color_system="truecolor" if not self.isLegacy else None
        )

        self._richProgressBar = Progress(
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
            transient=self.isLegacy,
        )

        self.songCount = 0
        self.overallTaskID = None
        self.overallProgress = 0
        self.overallTotal = 100
        self.overallCompletedTasks = 0
        self.quiet = False

        # ! Basically a wrapper for rich's: with ... as ...
        self._richProgressBar.__enter__()

    def print(self, *text, color="green"):
        """
        `text` : `any`  Text to be printed to screen
        Use this self.print to replace default print().
        """

        if self.quiet:
            return

        line = ""
        for item in text:
            line += str(item) + " "

        if color:
            self._richProgressBar.console.print(f"[{color}]{line}")
        else:
            self._richProgressBar.console.print(line)

    def set_song_count_to(self, songCount: int) -> None:
        """
        `int` `songCount` : number of songs being downloaded
        RETURNS `~`
        sets the size of the progressbar based on the number of songs in the current
        download set
        """

        # ! all calculations are based of the arbitrary choice that 1 song consists of
        # ! 100 steps/points/iterations
        self.songCount = songCount

        self.overallTotal = 100 * songCount

        if self.songCount > 4:
            self.overallTaskID = self._richProgressBar.add_task(
                description="Total",
                processID="0",
                message=f"{self.overallCompletedTasks}/{int(self.overallTotal / 100)} complete",
                total=self.overallTotal,
                visible=(not self.quiet),
            )

    def update_overall(self):
        """
        Updates the overall progress bar.
        """

        # If the overall progress bar exists
        if self.overallTaskID is not None:
            self._richProgressBar.update(
                self.overallTaskID,
                message=f"{self.overallCompletedTasks}/{int(self.overallTotal / 100)} complete",
                completed=self.overallProgress,
            )

    def new_progress_tracker(self, songObj):
        """
        returns new instance of `_ProgressTracker` that follows the `songObj` download subprocess
        """
        return _ProgressTracker(self, songObj)

    # def clear(self) -> None:
    #     '''
    #     clear the rich progress bar
    #     '''
    #     pass

    def close(self) -> None:
        """
        clean up rich
        """

        self._richProgressBar.stop()

    # def reset(self) -> None:
    #     '''
    #     restart progress for new download instance
    #     '''
    #     pass


# ========================
# === Progress Tracker ===
# ========================


class _ProgressTracker:
    def __init__(self, parent, songObj):
        self.parent = parent
        self.songObj = songObj

        self.progress = 0
        self.oldProgress = 0
        self.downloadID = 0
        self.status = ""

        self.taskID = self.parent._richProgressBar.add_task(
            description=songObj.get_display_name(),
            processID=str(self.downloadID),
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

    def pytube_progress_hook(self, stream, chunk, bytes_remaining) -> None:
        """
        Progress hook built according to pytube's documentation. It is called each time
        bytes are read from youtube.
        """

        # ! This will be called until download is complete, i.e we get an overall

        fileSize = stream.filesize

        # ! How much of the file was downloaded this iteration scaled put of 90.
        # ! It's scaled to 90 because, the arbitrary division of each songs 100
        # ! iterations is (a) 90 for download (b) 5 for conversion & normalization
        # ! and (c) 5 for ID3 tag embedding
        iterFraction = len(chunk) / fileSize * 90

        self.progress = self.progress + iterFraction
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

        message = f"Error: {e}\tWhile {self.status}: {self.songObj.get_display_name()}\n {str(tb)}"
        self.parent.print(message, color="red")

    def update(self, message=""):
        """
        Called at every event.
        """

        self.status = message

        # The change in progress since last update
        delta = self.progress - self.oldProgress

        # Update the progress bar
        # ! `start_task` called everytime to ensure progress is remove from indeterminate state
        self.parent._richProgressBar.start_task(self.taskID)
        self.parent._richProgressBar.update(
            self.taskID,
            description=self.songObj.get_display_name(),
            processID=str(self.downloadID),
            message=message,
            completed=self.progress,
        )

        # If task is complete
        if self.progress == 100 or message == "Error":
            self.parent.overallCompletedTasks += 1
            if self.parent.isLegacy:
                self.parent._richProgressBar.remove_task(self.taskID)

        # Update the overall progress bar
        self.parent.overallProgress += delta
        self.parent.update_overall()

        self.oldProgress = self.progress


# ===============================
# === Download tracking class ===
# ===============================


class DownloadTracker:
    def __init__(self):
        self.songObjList = []
        self.saveFile: Optional[Path] = None

    def load_tracking_file(self, trackingFilePath: str) -> None:
        """
        `str` `trackingFilePath` : path to a .spotdlTrackingFile

        RETURNS `~`

        reads songsObj's from disk and prepares to track their download
        """

        # Attempt to read .spotdlTrackingFile, raise exception if file can't be read
        trackingFile = Path(trackingFilePath)
        if not trackingFile.is_file():
            raise FileNotFoundError(f"no such tracking file found: {trackingFilePath}")

        with trackingFile.open("rb") as file_handle:
            songDataDumps = eval(file_handle.read().decode())

        # Save path to .spotdlTrackingFile
        self.saveFile = trackingFile

        # convert song data dumps to songObj's
        # ! see, songObj.get_data_dump and songObj.from_dump for more details
        for dump in songDataDumps:
            self.songObjList.append(SongObj.from_dump(dump))

    def load_song_list(self, songObjList: List[SongObj]) -> None:
        """
        `list<songOjb>` `songObjList` : songObj's being downloaded

        RETURNS `~`

        prepares to track download of provided songObj's
        """

        self.songObjList = songObjList

        self.backup_to_disk()

    def get_song_list(self) -> List[SongObj]:
        """
        RETURNS `list<songObj>

        get songObj's representing songs yet to be downloaded
        """
        return self.songObjList

    def backup_to_disk(self):
        """
        RETURNS `~`

        backs up details of songObj's yet to be downloaded to a .spotdlTrackingFile
        """
        # remove tracking file if no songs left in queue
        # ! we use 'return None' as a convenient exit point
        if len(self.songObjList) == 0:
            if self.saveFile and self.saveFile.is_file():
                self.saveFile.unlink()
            return None

        # prepare datadumps of all songObj's yet to be downloaded
        songDataDumps = []

        for song in self.songObjList:
            songDataDumps.append(song.get_data_dump())

        # ! the default naming of a tracking file is $nameOfFirstSOng.spotdlTrackingFile,
        # ! it needs a little fixing because of disallowed characters in file naming
        if not self.saveFile:
            songName = self.songObjList[0].get_song_name()

            for disallowedChar in ["/", "?", "\\", "*", "|", "<", ">"]:
                if disallowedChar in songName:
                    songName = songName.replace(disallowedChar, "")

            songName = songName.replace('"', "'").replace(":", " - ")

            self.saveFile = Path(songName + ".spotdlTrackingFile")

        # backup to file
        # ! we use 'wb' instead of 'w' to accommodate your fav K-pop/J-pop/Viking music
        with open(self.saveFile, "wb") as file_handle:
            file_handle.write(str(songDataDumps).encode())

    def notify_download_completion(self, songObj: SongObj) -> None:
        """
        `songObj` `songObj` : songObj representing song that has been downloaded

        RETURNS `~`

        removes given songObj from download queue and updates .spotdlTrackingFile
        """

        if songObj in self.songObjList:
            self.songObjList.remove(songObj)

        self.backup_to_disk()

    def clear(self):
        self.songObjList = []
        self.saveFile = None
