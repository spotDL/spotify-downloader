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

import httpx
from fastapi import Depends, Request
from spotdl_core.providers import ProviderContext, ProviderRegistry, SpotifyConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spotdl_server.auth.clock import Clock, ensure_utc
from spotdl_server.auth.context import ANONYMOUS, AuthContext
from spotdl_server.auth.oauth_providers import OAuthProviderClient, build_oauth_client
from spotdl_server.auth.tokens import TokenService, is_pat, sha256_hex
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.repositories.tokens import ApiTokenRepository, RefreshTokenRepository
from spotdl_server.repositories.users import OAuthIdentityRepository, UserRepository
from spotdl_server.services.auth import AuthService
from spotdl_server.services.entities import EntityService
from spotdl_server.services.errors import AuthRequired, Forbidden
from spotdl_server.services.oauth import OAuthService
from spotdl_server.services.resolve import ResolveService
from spotdl_server.services.search import SearchService
from spotdl_server.settings import Settings


def provider_context(settings: Settings) -> ProviderContext:
    """Build the provider context for the default registry.

    Provider credentials are read from the environment (the ``SPOTDL_SPOTIFY_*``
    family via :meth:`SpotifyConfig.from_env`); ``settings`` is accepted so the
    signature is stable as configuration surface grows in later plans.
    """
    _ = settings  # reserved for future settings-sourced provider configuration
    return ProviderContext(spotify=SpotifyConfig.from_env())


def get_settings(request: Request) -> Settings:
    """The ``Settings`` stored on ``app.state`` at ``create_app`` time.

    Deployment mode is fixed at startup, so reading it per request is a cheap,
    consistent lookup — the feature flags in ``GET /config`` derive from it.
    """
    settings: Settings = request.app.state.settings
    return settings


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


def get_search_service(
    session: AsyncSession = Depends(get_session),
    registry: ProviderRegistry = Depends(get_registry),
) -> SearchService:
    """Compose a :class:`SearchService` from the request's session + registry."""
    return SearchService(session=session, registry=registry)


def get_entity_service(
    session: AsyncSession = Depends(get_session),
) -> EntityService:
    """Compose a read-only :class:`EntityService` from the request's session."""
    return EntityService(session=session)


# --------------------------------------------------------------------------
# Auth wiring (Plan 6). ``clock`` + secret are process-scoped: the ``Clock`` is
# built once in the lifespan and stored on ``app.state``; the signing secret and
# TTLs come from ``Settings``. The auth context is resolved per request and
# *never raises* — gating is the job of ``require_user`` / ``require_admin``.
# --------------------------------------------------------------------------


def get_clock(request: Request) -> Clock:
    """The lifespan-built :class:`Clock` on ``app.state`` (a ``FakeClock`` in tests)."""
    clock: Clock = request.app.state.clock
    return clock


def get_token_service(
    request: Request,
    clock: Clock = Depends(get_clock),
) -> TokenService:
    """Build the request's :class:`TokenService` from settings + the shared clock.

    The signing secret comes from ``settings.require_auth_secret()`` (never
    hardcoded); it raises if auth is active but unconfigured, so a misconfigured
    server fails loudly at the first auth request instead of minting junk tokens.
    """
    settings = get_settings(request)
    return TokenService(
        secret=settings.require_auth_secret(),
        clock=clock,
        access_ttl_s=settings.access_token_ttl_seconds,
        refresh_ttl_s=settings.refresh_token_ttl_seconds,
    )


def _bearer_token(request: Request) -> str | None:
    """Extract the ``Authorization: Bearer <token>`` value, or ``None``."""
    header = request.headers.get("Authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


async def get_auth_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
    token_service: TokenService = Depends(get_token_service),
    clock: Clock = Depends(get_clock),
) -> AuthContext:
    """Resolve the caller's identity from the ``Authorization`` header.

    Three branches, and it **never raises** (any failure degrades to
    ``ANONYMOUS`` so the public read surface is unaffected):

    * a ``spdl_pat_`` PAT → hash-lookup, reject revoked/expired/disabled, load the
      owner, best-effort ``last_used_at`` touch → a ``pat`` context;
    * otherwise a JWT → ``verify_access`` (bad/expired/malformed all yield
      ``None``) → a ``user`` context whose ``is_admin`` mirrors the claim;
    * no header (or an unusable one) → ``ANONYMOUS``.
    """
    token = _bearer_token(request)
    if token is None:
        return ANONYMOUS

    if is_pat(token):
        api_tokens = ApiTokenRepository(session)
        row = await api_tokens.get_by_hash(sha256_hex(token))
        if row is None or row.revoked_at is not None:
            return ANONYMOUS
        now = clock.now()
        if row.expires_at is not None and ensure_utc(row.expires_at) <= now:
            return ANONYMOUS
        user = await UserRepository(session).get(row.user_id)
        if user is None or not user.is_active:
            return ANONYMOUS
        await api_tokens.touch_last_used(row, now=now)
        return AuthContext(kind="pat", user_id=user.id, is_admin=user.is_admin, token_id=row.id)

    claims = token_service.verify_access(token)
    if claims is None:
        return ANONYMOUS
    return AuthContext(kind="user", user_id=claims.user_id, is_admin=claims.is_admin)


def require_user(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Require any authenticated caller (user or PAT); 401 ``AUTH_REQUIRED`` else."""
    if not ctx.authenticated:
        raise AuthRequired()
    return ctx


async def require_admin(
    ctx: AuthContext = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    """Require an active admin, re-loading the user so a stale claim cannot act.

    The access token embeds ``is_admin``, but a demoted or disabled admin whose
    ≤15-min token has not yet expired must still be blocked — so admin routes
    verify against the live row (403 ``FORBIDDEN`` unless ``is_admin`` and
    ``is_active``).
    """
    user = await UserRepository(session).get(ctx.user_id) if ctx.user_id else None
    if user is None or not (user.is_admin and user.is_active):
        raise Forbidden()
    return ctx


def get_auth_service(
    session: AsyncSession = Depends(get_session),
    token_service: TokenService = Depends(get_token_service),
    clock: Clock = Depends(get_clock),
) -> AuthService:
    """Compose the :class:`AuthService` from the request's session + auth wiring."""
    return AuthService(
        session=session,
        token_service=token_service,
        clock=clock,
        users=UserRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )


# --------------------------------------------------------------------------
# OAuth wiring (Plan 6, Task 6). The shared ``httpx.AsyncClient`` is built once
# in the lifespan and stored on ``app.state.http`` (closed on shutdown); the
# provider-client dict is assembled per request from the enabled providers so a
# test can override :func:`build_oauth_clients` with fakes and never touch the
# network. The oauth router is mounted only when at least one provider is
# configured, so these dependencies only ever run for a live provider.
# --------------------------------------------------------------------------


def get_http_client(request: Request) -> httpx.AsyncClient:
    """The lifespan-built shared :class:`httpx.AsyncClient` on ``app.state``."""
    http: httpx.AsyncClient = request.app.state.http
    return http


def build_oauth_clients(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
) -> dict[OAuthProvider, OAuthProviderClient]:
    """Assemble the enabled provider clients keyed by :class:`OAuthProvider`.

    Credentials come from ``Settings`` (never hardcoded); each client shares the
    process-wide ``httpx`` client so connection pooling and ``respx`` interception
    both work. Only providers with both an id and a secret appear
    (``settings.enabled_oauth_providers()``), so the dict doubles as the router's
    enabled-provider set (an absent key → 404).
    """
    settings = get_settings(request)
    clients: dict[OAuthProvider, OAuthProviderClient] = {}
    for provider in settings.enabled_oauth_providers():
        if provider is OAuthProvider.GITHUB:
            assert settings.github_client_id and settings.github_client_secret
            client_id = settings.github_client_id
            client_secret = settings.github_client_secret.get_secret_value()
        else:  # OAuthProvider.DISCORD (the only other enabled value)
            assert settings.discord_client_id and settings.discord_client_secret
            client_id = settings.discord_client_id
            client_secret = settings.discord_client_secret.get_secret_value()
        clients[provider] = build_oauth_client(
            provider, client_id=client_id, client_secret=client_secret, http=http
        )
    return clients


def get_oauth_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
    token_service: TokenService = Depends(get_token_service),
    clock: Clock = Depends(get_clock),
    clients: dict[OAuthProvider, OAuthProviderClient] = Depends(build_oauth_clients),
) -> OAuthService:
    """Compose the :class:`OAuthService` from the request's session + auth wiring."""
    settings = get_settings(request)
    return OAuthService(
        session=session,
        token_service=token_service,
        clock=clock,
        users=UserRepository(session),
        identities=OAuthIdentityRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
        clients=clients,
        auth_secret=settings.require_auth_secret(),
        redirect_base_url=settings.oauth_redirect_base_url or "",
    )
