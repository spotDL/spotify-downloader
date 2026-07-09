from enum import Enum


class VoteRequestValue(str, Enum):
    DOWN = "down"
    RETRACT = "retract"
    UP = "up"

    def __str__(self) -> str:
        return str(self.value)
