from enum import Enum


class EntityType(str, Enum):
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"
    TRACK = "track"

    def __str__(self) -> str:
        return str(self.value)
