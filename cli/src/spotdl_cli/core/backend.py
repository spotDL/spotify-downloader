"""Backend lifecycle manager for local and remote modes."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from enum import StrEnum
from typing import TYPE_CHECKING, Callable

import httpx

from spotdl_cli.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


class BackendState(StrEnum):
    """Backend lifecycle states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class BackendManager:
    """Manages the local backend lifecycle and creates httpx clients.

    In local mode, the backend FastAPI app is imported in-process and
    called via ``httpx.ASGITransport`` — no separate server needed.

    In remote mode, a standard HTTP transport is used against ``api_url``.
    """

    def __init__(self) -> None:
        self._app: FastAPI | None = None
        self._lifespan_stack: AsyncExitStack | None = None
        self._state: BackendState = BackendState.STOPPED
        self._error_message: str | None = None
        self._state_callbacks: list[Callable[[BackendState], None]] = []

    @property
    def state(self) -> BackendState:
        return self._state

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @property
    def is_started(self) -> bool:
        return self._state == BackendState.RUNNING

    def on_state_change(self, callback: Callable[[BackendState], None]) -> None:
        """Register a callback for state changes."""
        self._state_callbacks.append(callback)

    def _set_state(self, state: BackendState) -> None:
        self._state = state
        for cb in self._state_callbacks:
            try:
                cb(state)
            except Exception:
                logger.debug("State change callback error", exc_info=True)

    async def start(self) -> None:
        """Start the local backend (import app, run lifespan/migrations)."""
        if self._state == BackendState.RUNNING:
            return

        settings = get_settings()
        if settings.backend_mode != "local":
            self._set_state(BackendState.RUNNING)
            return

        self._set_state(BackendState.STARTING)

        try:
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

            self._set_state(BackendState.RUNNING)
            logger.info("Local backend started (db: %s)", db_path)
        except Exception as e:
            self._error_message = str(e)
            self._set_state(BackendState.ERROR)
            raise

    async def stop(self) -> None:
        """Stop the local backend (exit lifespan, close DB)."""
        if self._state == BackendState.STOPPED:
            return

        self._set_state(BackendState.STOPPING)

        if self._lifespan_stack is not None:
            await self._lifespan_stack.aclose()
            self._lifespan_stack = None

        self._app = None
        self._set_state(BackendState.STOPPED)
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
