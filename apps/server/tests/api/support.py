"""Offline API-test harness: a real app + fake registry + in-schema SQLite.

The whole Plan 5 API suite is offline. :func:`api_client` builds the app via the
``create_app(settings, registry=...)`` seam (the same seam Plan 8's embedded
transport uses), enters the lifespan so ``app.state`` holds a real engine/session
factory/registry, creates the full §6.1 schema on that lifespan-built engine
(no Alembic needed for a metadata read test), and yields an ``httpx`` client
speaking to the app over ``ASGITransport``. ``raise_app_exceptions=False`` so the
registered error-envelope handlers produce responses (a 500 catch-all included)
instead of the exception propagating into the test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from spotdl_core.providers import ProviderRegistry
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.settings import DeploymentMode, Settings


@asynccontextmanager
async def api_client(
    registry: ProviderRegistry,
    *,
    data_dir: Path,
    mode: DeploymentMode = DeploymentMode.SELFHOST,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an ``httpx`` client bound to a fully wired app over ASGITransport."""
    settings = Settings(mode=mode, data_dir=data_dir)
    app = create_app(settings, registry=registry)
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
