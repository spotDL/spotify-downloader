from enum import Enum


class OutputFormat(str, Enum):
    FLAC = "flac"
    M4A = "m4a"
    MP3 = "mp3"
    OGG = "ogg"
    OPUS = "opus"
    WAV = "wav"

    def __str__(self) -> str:
        return str(self.value)
