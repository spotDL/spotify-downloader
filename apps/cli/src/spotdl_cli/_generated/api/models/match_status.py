from enum import Enum


class MatchStatus(str, Enum):
    AUTO = "auto"
    COMMUNITY_VERIFIED = "community_verified"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return str(self.value)
