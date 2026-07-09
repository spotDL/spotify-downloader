from enum import Enum


class BatchKind(str, Enum):
    ALBUM = "album"
    PLAYLIST = "playlist"
    SINGLE = "single"

    def __str__(self) -> str:
        return str(self.value)
