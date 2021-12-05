from pathlib import Path
from typing import Optional, List

from spotdl.search import SongObject, song_gatherer
from spotdl.utils.song_name_utils import format_name


class DownloadTracker:
    def __init__(self):
        self.song_list = []
        self.save_file: Optional[Path] = None

    def load_tracking_file(self, tracking_file_path: str) -> None:
        """
        `str` `tracking_file_path` : path to a .spotdlTrackingFile

        RETURNS `~`

        reads songsObj's from disk and prepares to track their download
        """

        # Attempt to read .spotdlTrackingFile, raise exception if file can't be read
        tracking_file = Path(tracking_file_path).resolve()
        if not tracking_file.is_file():
            raise FileNotFoundError(
                f"no such tracking file found: {tracking_file_path}"
            )

        with tracking_file.open("rb") as file_handle:
            song_data_dumps = eval(file_handle.read().decode())

        # Save path to .spotdlTrackingFile
        self.save_file = tracking_file

        # convert song data dumps to songObj's
        # ! see, songGatherer.get_data_dump and songGatherer.from_dump for more details
        for dump in song_data_dumps:
            self.song_list.append(song_gatherer.from_dump(dump))

    def load_song_list(self, song_list: List[SongObject]) -> None:
        """
        `list<songOjb>` `song_list` : songObj's being downloaded

        RETURNS `~`

        prepares to track download of provided songObj's
        """

        self.song_list = song_list

        self.backup_to_disk()

    def get_song_list(self) -> List[SongObject]:
        """
        RETURNS `list<songObj>

        get songObj's representing songs yet to be downloaded
        """
        return self.song_list

    def backup_to_disk(self):
        """
        RETURNS `~`

        backs up details of songObj's yet to be downloaded to a .spotdlTrackingFile
        """
        # remove tracking file if no songs left in queue
        # ! we use 'return None' as a convenient exit point
        if len(self.song_list) == 0:
            if self.save_file and self.save_file.is_file():
                self.save_file.unlink()

            return None

        # prepare datadumps of all songObj's yet to be downloaded
        song_data_dumps = [song.data_dump for song in self.song_list]

        # ! the default naming of a tracking file is $nameOfFirstSOng.spotdlTrackingFile,
        # ! it needs a little fixing because of disallowed characters in file naming
        if not self.save_file:
            song_name = self.song_list[0].song_name

            song_name = format_name(song_name)

            self.save_file = Path(song_name + ".spotdlTrackingFile")

        # save encoded string to a file
        with open(self.save_file, "wb") as file_handle:
            file_handle.write(str(song_data_dumps).encode())

    def notify_download_completion(self, song_object: SongObject) -> None:
        """
        `songObj` `songObj` : songObj representing song that has been downloaded

        RETURNS `~`

        removes given songObj from download queue and updates .spotdlTrackingFile
        """

        if song_object in self.song_list:
            self.song_list.remove(song_object)

        self.backup_to_disk()

    def clear(self):
        self.song_list = []
        self.save_file = None
