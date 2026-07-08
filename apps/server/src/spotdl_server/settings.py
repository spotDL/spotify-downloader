from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(StrEnum):
    HOSTED = "hosted"
    SELFHOST = "selfhost"
    EMBEDDED = "embedded"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPOTDL_")

    mode: DeploymentMode = DeploymentMode.SELFHOST
