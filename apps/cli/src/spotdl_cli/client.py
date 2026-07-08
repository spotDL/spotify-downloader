from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings


@asynccontextmanager
async def embedded_client() -> AsyncIterator[httpx.AsyncClient]:
    """An httpx client talking to an in-process embedded-mode server."""
    app = create_app(Settings(mode=DeploymentMode.EMBEDDED))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://embedded") as client:
        yield client
