# ===============
# === Imports ===
# ===============

# ! These are not used, they're here for static type checking using mypy
from spotdl.search.songObj import SongObj
import spotdl.search.songGatherer as songGatherer
import typing
from pathlib import Path


# ===============================
# === Download tracking class ===
# ===============================


class DownloadTracker:
    def __init__(self):
        self.songObjList = []
        self.saveFile: typing.Optional[Path] = None

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
        # ! see, songGatherer.get_data_dump and songGatherer.from_dump for more details
        for dump in songDataDumps:
            self.songObjList.append(songGatherer.from_dump(dump))

    def load_song_list(self, songObjList: typing.List[SongObj]) -> None:
        """
        `list<songOjb>` `songObjList` : songObj's being downloaded

        RETURNS `~`

        prepares to track download of provided songObj's
        """

        self.songObjList = songObjList

        self.backup_to_disk()

    def get_song_list(self) -> typing.List[SongObj]:
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
