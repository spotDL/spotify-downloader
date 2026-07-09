from enum import Enum


class DeploymentMode(str, Enum):
    EMBEDDED = "embedded"
    HOSTED = "hosted"
    SELFHOST = "selfhost"

    def __str__(self) -> str:
        return str(self.value)
