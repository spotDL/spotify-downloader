"""``/api/v1/auth`` — email+password sessions (register/login/refresh/logout/me).

A thin HTTP shell over :class:`~spotdl_server.services.auth.AuthService`: it maps
request bodies to service calls and the returned ``TokenPair`` / ``User`` to the
response schemas. No business logic, no ORM import (the ``User`` it receives is
serialized by ``UserResponse.model_validate`` without naming the ORM type). This
router is mounted only when ``settings.auth_active()`` (never in EMBEDDED mode).
Domain failures (bad credentials, reuse, duplicate email) are raised by the
service as ``SpotdlError`` subclasses and rendered by the shared error envelope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from spotdl_server.api.deps import get_auth_service, get_settings, require_user
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from spotdl_server.auth.context import AuthContext
from spotdl_server.services.auth import AuthService, TokenPair
from spotdl_server.settings import Settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"], responses=ERROR_RESPONSES)


def _token_response(pair: TokenPair, settings: Settings) -> TokenResponse:
    """Map an issued :class:`TokenPair` to the wire ``TokenResponse``."""
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
        user=UserResponse.model_validate(pair.user),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Create an account (no email verification in v1) and issue its first tokens."""
    pair = await service.register(
        email=body.email, password=body.password, display_name=body.display_name
    )
    return _token_response(pair, settings)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Verify credentials and issue a fresh token pair (a new refresh family)."""
    pair = await service.login(email=body.email, password=body.password)
    return _token_response(pair, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Rotate the refresh token (reuse of a spent one revokes the whole family)."""
    pair = await service.refresh(refresh_token=body.refresh_token)
    return _token_response(pair, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    _ctx: AuthContext = Depends(require_user),
    service: AuthService = Depends(get_auth_service),
) -> Response:
    """Revoke the presented refresh token's whole family (idempotent)."""
    await service.logout(refresh_token=body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(
    ctx: AuthContext = Depends(require_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Return the authenticated profile (works for both a JWT and a PAT)."""
    assert ctx.user_id is not None  # require_user guarantees an identity
    user = await service.get_me(ctx.user_id)
    return UserResponse.model_validate(user)
