"""FastAPI dependency providers wiring ``app.state`` into services.

No module-level singletons: the async engine, ``async_sessionmaker`` and
``ProviderRegistry`` are built in the lifespan and stored on ``app.state``; these
dependencies read them from the request and compose per-request sessions and
services. ``get_session`` owns the unit of work — it commits on success and rolls
back on failure, so services and repositories never commit themselves.

``provider_context(settings)`` builds the immutable :class:`ProviderContext` the
default registry's factories receive; it is used only when no registry is
injected into ``create_app`` (production / self-host), reading provider
credentials from the environment via the core config helpers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from spotdl_core.providers import ProviderContext, ProviderRegistry, SpotifyConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spotdl_server.services.resolve import ResolveService
from spotdl_server.settings import Settings


def provider_context(settings: Settings) -> ProviderContext:
    """Build the provider context for the default registry.

    Provider credentials are read from the environment (the ``SPOTDL_SPOTIFY_*``
    family via :meth:`SpotifyConfig.from_env`); ``settings`` is accepted so the
    signature is stable as configuration surface grows in later plans.
    """
    _ = settings  # reserved for future settings-sourced provider configuration
    return ProviderContext(spotify=SpotifyConfig.from_env())


def get_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    """The lifespan-built session factory stored on ``app.state``."""
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    return sessionmaker


def get_registry(request: Request) -> ProviderRegistry:
    """The lifespan-built (or injected) provider registry on ``app.state``."""
    registry: ProviderRegistry = request.app.state.registry
    return registry


async def get_session(
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(get_sessionmaker),
) -> AsyncIterator[AsyncSession]:
    """Yield a session that owns the request's unit of work.

    Commits when the handler returns cleanly; rolls back on any exception so a
    failed request never persists a partial write.
    """
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_resolve_service(
    session: AsyncSession = Depends(get_session),
    registry: ProviderRegistry = Depends(get_registry),
) -> ResolveService:
    """Compose a :class:`ResolveService` from the request's session + registry."""
    return ResolveService(session=session, registry=registry)
