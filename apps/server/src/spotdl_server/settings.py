from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(StrEnum):
    HOSTED = "hosted"
    SELFHOST = "selfhost"
    EMBEDDED = "embedded"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPOTDL_")

    mode: DeploymentMode = DeploymentMode.SELFHOST

    # SQLite file location for the selfhost/embedded default database.
    data_dir: Path = Path("~/.local/share/spotdl").expanduser()
    # Explicit database URL override (e.g. postgresql+asyncpg://...). Must name
    # an async driver when set. When None, a SQLite file under data_dir is used.
    database_url: str | None = None
    db_echo: bool = False

    def effective_database_url(self) -> str:
        """Resolve the async database URL used to build the engine.

        Returns the explicit ``database_url`` override when set (asserting it
        names an async driver), otherwise a ``sqlite+aiosqlite`` URL pointing at
        ``spotdl.db`` inside ``data_dir``.
        """
        if self.database_url is not None:
            assert "+aiosqlite" in self.database_url or "+asyncpg" in self.database_url, (
                "database_url must name an async driver "
                "(sqlite+aiosqlite:// or postgresql+asyncpg://)"
            )
            return self.database_url
        return f"sqlite+aiosqlite:///{self.data_dir / 'spotdl.db'}"
