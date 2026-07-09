"""FastAPI application factory + lifespan.

``create_app`` builds the app; the lifespan owns the process-scoped resources
(async engine, session factory, provider registry) on ``app.state`` and closes
them on shutdown — no module-level singletons (spec §6 / Plan 5 Global
Constraints).

The ``registry=`` keyword is the single fake/embedded-CLI injection seam
(Plan 8): when a registry is passed, the lifespan uses it and does **not** close
it (the caller owns its lifetime); when omitted, the app builds the default
registry from :func:`provider_context` and closes it on shutdown. Plan 5 tests
build apps as ``create_app(settings, registry=build_fake_registry(...))`` and
Plan 8's ``EmbeddedTransport`` passes its own registry the same way.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from spotdl_core.providers import ProviderRegistry, build_default_registry

from spotdl_server import __version__
from spotdl_server.api.deps import provider_context
from spotdl_server.api.errors import register_exception_handlers
from spotdl_server.api.routers import (
    auth,
    entities,
    meta,
    oauth,
    reports,
    resolve,
    search,
    submissions,
    tokens,
    votes,
)
from spotdl_server.auth.clock import SystemClock
from spotdl_server.db.engine import build_engine, build_sessionmaker
from spotdl_server.settings import DeploymentMode, Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build engine, session factory and registry; dispose on shutdown.

    Only resources the app itself created are closed: an injected registry
    (``app.state.injected_registry``) is left open for its owner.
    """
    settings: Settings = app.state.settings

    # The injectable time seam for the community layer (token expiry, refresh
    # rotation, PAT expiry). Built once here per the no-module-level-singletons
    # rule; tests swap a FakeClock onto ``app.state.clock`` after startup.
    app.state.clock = SystemClock()

    # Fail fast in HOSTED: a hosted server with auth active but no signing secret
    # would mint junk tokens, so refuse to start. Self-host/embedded stay lenient
    # (a self-hoster only needs a secret if they actually enable accounts), and
    # the per-request ``get_token_service`` still raises if a secret is missing.
    if settings.mode is DeploymentMode.HOSTED and settings.auth_active():
        settings.require_auth_secret()

    engine = build_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)

    # Shared outbound HTTP client for OAuth provider calls (Task 6). Built once
    # here (no module-level singleton) and closed on shutdown; the oauth
    # dependencies read it from ``app.state`` and respx intercepts it in tests.
    app.state.http = httpx.AsyncClient()

    injected: ProviderRegistry | None = app.state.injected_registry
    app.state.registry = injected or build_default_registry(provider_context(settings))
    try:
        yield
    finally:
        if injected is None:  # caller-owned registries are NOT closed by the app
            await app.state.registry.aclose()
        await app.state.http.aclose()
        await engine.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    registry: ProviderRegistry | None = None,
) -> FastAPI:
    """Create the spotDL server app.

    ``registry`` is the injection seam (Plan 8): pass a registry to have the app
    use it without owning its lifetime; omit it to have the app build and close
    the default registry.
    """
    settings = settings or Settings()
    app = FastAPI(title="spotdl-server", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.injected_registry = registry
    register_exception_handlers(app)

    # The Plan 5 surface is entirely read-only and available in every deployment
    # mode, so these routers mount unconditionally. Mode gating is a *mount-time*
    # decision, not a per-request ``if``: the download router (Plan 7) will be
    # mounted only for non-HOSTED modes via the seam below — it is deliberately
    # NOT created in this plan.
    app.include_router(meta.router)
    app.include_router(resolve.router)
    app.include_router(search.router)
    app.include_router(entities.router)

    # Community routers mount only when auth is active (spec §4: never in EMBEDDED
    # / loopback mode). Mount-time gate — not a per-request conditional.
    if settings.auth_active():
        app.include_router(auth.router)
        app.include_router(tokens.router)
        app.include_router(votes.router)
        app.include_router(submissions.router)
        app.include_router(reports.router)
        # The OAuth router additionally requires at least one configured provider
        # (id + secret). Mount-time gate — never a per-request conditional.
        if settings.enabled_oauth_providers():
            app.include_router(oauth.router)
    # if settings.mode is not DeploymentMode.HOSTED:
    #     app.include_router(downloads_router)  # Plan 7

    return app
