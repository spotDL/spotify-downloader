from enum import Enum


class OverwriteMode(str, Enum):
    FORCE = "force"
    METADATA = "metadata"
    SKIP = "skip"

    def __str__(self) -> str:
        return str(self.value)
