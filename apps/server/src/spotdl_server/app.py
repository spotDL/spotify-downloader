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
from typing import TYPE_CHECKING, cast

import httpx
from fastapi import FastAPI, Request, Response
from spotdl_core.providers import ProviderRegistry, build_default_registry

from spotdl_server import __version__
from spotdl_server.api.deps import provider_context
from spotdl_server.api.errors import register_exception_handlers
from spotdl_server.api.middleware import RateLimitMiddleware
from spotdl_server.api.progress_hub import ProgressHub
from spotdl_server.api.routers import (
    admin,
    auth,
    downloads,
    entities,
    meta,
    oauth,
    progress_ws,
    reports,
    resolve,
    search,
    submissions,
    tokens,
    votes,
)
from spotdl_server.auth.clock import SystemClock
from spotdl_server.db.engine import build_engine, build_sessionmaker
from spotdl_server.downloads.worker import DownloadWorkerPool
from spotdl_server.observability import (
    RequestObservabilityMiddleware,
    configure_logging,
    init_sentry,
    render_latest,
)
from spotdl_server.ratelimit import build_rate_limiter
from spotdl_server.services.batch import BatchFinalizer
from spotdl_server.settings import DeploymentMode, Settings
from spotdl_server.webui import mount_webui

if TYPE_CHECKING:
    from spotdl_server.downloads.worker import Engine, Finalizer


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

    # The process-scoped rate-limit backend (spec §6.4). Built once here (no
    # module-level singleton): a Redis backend when ``redis_url`` is set and the
    # ``redis`` extra is installed, else the in-memory default bound to the same
    # clock. Closed on shutdown. Read per request by ``RateLimitMiddleware`` — and
    # only when the middleware was mounted (``rate_limit_active()``).
    app.state.rate_limiter = build_rate_limiter(settings.redis_url, app.state.clock)

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

    # The download queue's runtime collaborators (Plan 7): the progress hub, the
    # asyncio worker pool, and the batch finalizer — built once here (no
    # module-level singletons) and drained/closed on shutdown. Mounted only in
    # selfhost/embedded (hosted never runs a local engine — spec §4). The engine
    # is either an injected fake (the offline test seam) or the real Plan 4 engine
    # built lazily from the download config. ``pool.start()`` recovers orphaned
    # jobs and spawns the workers.
    downloads_on = settings.downloads_enabled()
    if downloads_on:
        from spotdl_core.download import build_default_engine

        download_engine = app.state.injected_download_engine
        engine_impl = download_engine or build_default_engine(settings.download_config())
        hub = ProgressHub()
        finalizer = BatchFinalizer(sessionmaker=app.state.sessionmaker, settings=settings)
        # The engine (real or injected fake) and the finalizer satisfy the pool's
        # structural ``Engine`` / ``Finalizer`` Protocols at runtime (duck-typed);
        # cast at this wiring seam so the nominal check is happy.
        pool = DownloadWorkerPool(
            sessionmaker=app.state.sessionmaker,
            engine=cast("Engine", engine_impl),
            hub=hub,
            settings=settings,
            finalizer=cast("Finalizer", finalizer),
            clock=app.state.clock,
        )
        app.state.download_hub = hub
        app.state.download_pool = pool
        await pool.start()
    try:
        yield
    finally:
        if downloads_on:  # graceful drain before the DB engine is disposed
            await app.state.download_pool.shutdown()
        if injected is None:  # caller-owned registries are NOT closed by the app
            await app.state.registry.aclose()
        await app.state.http.aclose()
        await app.state.rate_limiter.aclose()
        await engine.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    registry: ProviderRegistry | None = None,
    download_engine: object | None = None,
) -> FastAPI:
    """Create the spotDL server app.

    ``registry`` is the injection seam (Plan 8): pass a registry to have the app
    use it without owning its lifetime; omit it to have the app build and close
    the default registry. ``download_engine`` is the parallel seam for the Plan 7
    download engine (a ``FakeDownloadEngine`` in the offline suite); omit it and
    the lifespan builds the real Plan 4 engine when downloads are enabled.
    """
    settings = settings or Settings()
    # Fail fast on a nonsensical download-auth configuration (mirrors Plan 6's
    # ``require_auth_secret``): a selfhost operator who sets
    # ``downloads_require_auth`` while auth is inactive would get a silently-open
    # download surface, so refuse to build the app at all.
    settings.require_download_auth_consistency()
    # Observability (CONTRACT A5): configure JSON logging and optional Sentry
    # before anything else so startup/registration itself logs in the one format.
    configure_logging(settings)
    init_sentry(settings)

    app = FastAPI(title="spotdl-server", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.injected_registry = registry
    app.state.injected_download_engine = download_engine
    register_exception_handlers(app)

    # Rate limiting is a *mount-time* decision (spec §6.4): the middleware is added
    # only when active (hosted-only default, or an explicit ``rate_limit_enabled``).
    # When inactive it is not mounted at all, so no per-request conditional runs
    # and every route behaves exactly as if rate limiting did not exist. The
    # backend + clock it reads live on ``app.state`` (built in the lifespan).
    if settings.rate_limit_active():
        app.add_middleware(RateLimitMiddleware)

    # The correlation-id / access-log / HTTP-metrics middleware is added last so
    # it is the outermost layer: it assigns the request id and measures latency
    # around every other middleware (including rate-limit rejections). CONTRACT A3.
    app.add_middleware(RequestObservabilityMiddleware)

    # Prometheus exposition (CONTRACT A2). A mount-time decision like every other
    # surface: served when ``metrics_enabled`` (the default), absent (404) when
    # not. Kept out of the OpenAPI schema so the committed openapi.json is stable.
    if settings.metrics_enabled:

        async def metrics_endpoint(_request: Request) -> Response:
            body, content_type = render_latest()
            return Response(body, media_type=content_type)

        app.add_route("/metrics", metrics_endpoint, include_in_schema=False)

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
        app.include_router(admin.router)
        # The OAuth router additionally requires at least one configured provider
        # (id + secret). Mount-time gate — never a per-request conditional.
        if settings.enabled_oauth_providers():
            app.include_router(oauth.router)

    # Download surface (Plan 7): mounted only in selfhost/embedded — hosted never
    # mounts the router (nor builds the pool/hub/engine in the lifespan). Mount-
    # time mode gate (spec §4), not a per-request conditional.
    if settings.downloads_enabled():
        app.include_router(downloads.router)
        app.include_router(progress_ws.router)

    # Serve the bundled SPA when its assets were embedded into the wheel (Plan
    # 10). Mounted last so the catch-all fallback never shadows an API route; a
    # no-op when absent (API-only installs are unaffected). The SPA self-gates on
    # GET /config, so it mounts in every deployment mode.
    mount_webui(app)

    return app
