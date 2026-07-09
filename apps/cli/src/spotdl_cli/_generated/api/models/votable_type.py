from enum import Enum


class VotableType(str, Enum):
    ENTITY_LINK = "entity_link"
    LYRICS = "lyrics"
    MATCH = "match"

    def __str__(self) -> str:
        return str(self.value)
