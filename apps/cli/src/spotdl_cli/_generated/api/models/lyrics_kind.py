from enum import Enum


class LyricsKind(str, Enum):
    PLAIN = "plain"
    SYNCED = "synced"

    def __str__(self) -> str:
        return str(self.value)
