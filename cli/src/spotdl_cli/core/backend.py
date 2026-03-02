"""Backend lifecycle manager for local and remote modes."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING

import httpx

from spotdl_cli.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


class BackendManager:
    """Manages the local backend lifecycle and creates httpx clients.

    In local mode, the backend FastAPI app is imported in-process and
    called via ``httpx.ASGITransport`` — no separate server needed.

    In remote mode, a standard HTTP transport is used against ``api_url``.
    """

    def __init__(self) -> None:
        self._app: FastAPI | None = None
        self._lifespan_stack: AsyncExitStack | None = None
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    async def start(self) -> None:
        """Start the local backend (import app, run lifespan/migrations)."""
        if self._started:
            return

        settings = get_settings()
        if settings.backend_mode != "local":
            self._started = True
            return

        # Set env vars BEFORE importing the backend so pydantic-settings picks them up
        db_path = settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
        os.environ.setdefault("DEPLOYMENT_MODE", "self-hosted")
        os.environ.setdefault("ENVIRONMENT", "production")
        os.environ.setdefault("LOG_LEVEL", "WARNING")

        # Clear the backend's lru_cache so it picks up our env vars
        from spotdl.config import get_settings as backend_get_settings

        backend_get_settings.cache_clear()

        # Import and create the app
        from spotdl.main import create_app

        self._app = create_app()

        # Trigger the lifespan (runs DB init/migrations)
        self._lifespan_stack = AsyncExitStack()
        await self._lifespan_stack.__aenter__()

        # The lifespan is an async context manager on the app
        # We need to manually enter it via the app's router lifespan
        lifespan_cm = self._app.router.lifespan_context(self._app)
        await self._lifespan_stack.enter_async_context(lifespan_cm)

        self._started = True
        logger.info("Local backend started (db: %s)", db_path)

    async def stop(self) -> None:
        """Stop the local backend (exit lifespan, close DB)."""
        if not self._started:
            return

        if self._lifespan_stack is not None:
            await self._lifespan_stack.aclose()
            self._lifespan_stack = None

        self._app = None
        self._started = False
        logger.info("Local backend stopped")

    def create_client(self) -> httpx.AsyncClient:
        """Return an httpx.AsyncClient with the appropriate transport.

        - local mode: ASGITransport against the in-process app
        - remote mode: standard HTTP transport against api_url
        """
        settings = get_settings()

        if settings.backend_mode == "local" and self._app is not None:
            transport = httpx.ASGITransport(app=self._app)
            return httpx.AsyncClient(
                transport=transport,
                base_url="http://localhost",
                timeout=httpx.Timeout(settings.api_timeout),
            )

        # Remote mode
        return httpx.AsyncClient(
            base_url=settings.api_url,
            timeout=httpx.Timeout(settings.api_timeout),
            headers={"Authorization": f"Bearer {settings.auth_token}"}
            if settings.auth_token
            else {},
        )


# Singleton
_backend_manager: BackendManager | None = None


def get_backend_manager() -> BackendManager:
    """Get the global BackendManager instance."""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager
