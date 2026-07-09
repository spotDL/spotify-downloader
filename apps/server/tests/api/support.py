"""Offline API-test harness: a real app + fake registry + in-schema SQLite.

The whole Plan 5+ API suite is offline. :func:`api_client` builds the app via the
``create_app(settings, registry=..., download_engine=...)`` seams (the same seams
Plan 8's embedded transport uses), **pre-creates the full §6.1 schema** on the
app's SQLite file (a real deploy migrates before boot — and Plan 7's download
pool runs a crash-recovery query the instant the lifespan starts, so the tables
must exist first), enters the lifespan so ``app.state`` holds a real engine/
session factory/registry/download pool, and yields an ``httpx`` client speaking to
the app over ``ASGITransport``. ``raise_app_exceptions=False`` so the registered
error-envelope handlers produce responses (a 500 catch-all included) instead of
the exception propagating into the test.

The download engine is the offline ``FakeDownloadEngine`` seam (no network / ffmpeg
/ real engine); pass an explicit ``download_engine`` to script progress/outcomes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from spotdl_core.providers import ProviderRegistry
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.db.engine import build_engine
from spotdl_server.settings import DeploymentMode, Settings

from tests.conftest import FakeDownloadEngine


@asynccontextmanager
async def api_client(
    registry: ProviderRegistry,
    *,
    data_dir: Path,
    mode: DeploymentMode = DeploymentMode.SELFHOST,
    download_engine: Any | None = None,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an ``httpx`` client bound to a fully wired app over ASGITransport."""
    settings = Settings(mode=mode, data_dir=data_dir)

    # Pre-create the schema before the lifespan starts: Plan 7's download pool
    # recovers orphaned jobs (a ``download_jobs`` query) the instant it boots.
    pre_engine = build_engine(settings)
    async with pre_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await pre_engine.dispose()

    if download_engine is None and settings.downloads_enabled():
        download_engine = FakeDownloadEngine(config=settings.download_config())

    app = create_app(settings, registry=registry, download_engine=download_engine)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
