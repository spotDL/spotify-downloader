from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from spotdl_server.settings import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Build a fresh async engine from settings.

    No module-level singleton: callers own the engine's lifecycle (the FastAPI
    lifespan builds one and disposes it on shutdown). For the SQLite default the
    parent ``data_dir`` is created so the file can be opened.
    """
    if settings.database_url is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    return create_async_engine(
        settings.effective_database_url(),
        echo=settings.db_echo,
        future=True,
    )


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
