from typing import Any

from fastapi import FastAPI

from spotdl_server import __version__
from spotdl_server.settings import DeploymentMode, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="spotdl-server", version=__version__)
    app.state.settings = settings

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/config")
    async def config() -> dict[str, Any]:
        return {
            "mode": settings.mode.value,
            "features": {"downloads": settings.mode is not DeploymentMode.HOSTED},
        }

    return app
