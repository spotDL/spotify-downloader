"""``/api/v1/auth/oauth`` — GitHub/Discord login (dual-mode callback).

A thin HTTP shell over :class:`~spotdl_server.services.oauth.OAuthService`. Two
routes per provider: ``/{provider}/authorize`` (send the browser to the provider,
or hand a client the URL as JSON) and ``/{provider}/callback`` (finish the flow).
An unknown or unconfigured provider is a 404. No business logic, no ORM import.

**Dual-mode callback (CONTRACT).** The provider redirects the *browser* to the
callback as a top-level navigation, so a raw JSON body there would strand the
SPA. Mode is chosen per request:

* **JSON mode** — when ``web_auth_redirect_enabled`` is explicitly ``False`` *or*
  the request's ``Accept`` prefers ``application/json`` (the CLI / generated
  clients / existing tests): the documented ``TokenResponse`` (200) or the shared
  ``ErrorEnvelope`` — semantics unchanged for JSON consumers.
* **Browser-handoff mode** — otherwise (a plain browser navigation): a 302 to
  ``{spa_base}/auth/callback/{provider}`` carrying the token pair (or an
  ``#error=`` code) in the URL **fragment**, never the query string, so tokens
  never reach server/proxy logs or ``Referer`` headers.
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from spotdl_core.providers import ProviderAuthError, SpotdlError

from spotdl_server.api.deps import build_oauth_clients, get_oauth_service, get_settings
from spotdl_server.api.errors import _status_and_code
from spotdl_server.api.routers import ERROR_RESPONSES
from spotdl_server.api.schemas import AuthorizeUrlResponse, TokenResponse, UserResponse
from spotdl_server.auth.oauth_providers import OAuthProviderClient
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.services.auth import TokenPair
from spotdl_server.services.errors import InvalidToken
from spotdl_server.services.oauth import OAuthService
from spotdl_server.settings import Settings

router = APIRouter(prefix="/api/v1/auth/oauth", tags=["oauth"], responses=ERROR_RESPONSES)

# Pinned handoff error value for a failed CSRF ``state`` check (SPA renders it).
_STATE_MISMATCH_ERROR = "oauth_state_mismatch"


def _enabled_provider(
    provider: str, clients: dict[OAuthProvider, OAuthProviderClient]
) -> OAuthProvider:
    """Resolve ``provider`` to an *enabled* :class:`OAuthProvider`, else 404.

    An unrecognised value or one whose credentials are not configured (absent
    from ``clients``) is indistinguishable to the caller — both are a 404.
    """
    try:
        resolved = OAuthProvider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="unknown oauth provider") from exc
    if resolved not in clients:
        raise HTTPException(status_code=404, detail="oauth provider not enabled")
    return resolved


def _quality(accept: str, media: str) -> float | None:
    """Return the q-value ``accept`` assigns to ``media`` (``None`` if absent)."""
    for part in accept.split(","):
        token = part.strip()
        if not token:
            continue
        media_type, _, params = token.partition(";")
        if media_type.strip().lower() != media:
            continue
        quality = 1.0
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.strip().lower() == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        return quality
    return None


def _prefers_json(accept: str) -> bool:
    """Whether ``application/json`` is at least as preferred as ``text/html``."""
    json_q = _quality(accept, "application/json")
    if json_q is None:
        return False
    html_q = _quality(accept, "text/html")
    return html_q is None or json_q >= html_q


def _json_mode(request: Request, settings: Settings) -> bool:
    """Pick JSON mode (True) vs browser-handoff (False) for this callback."""
    if settings.web_auth_redirect_enabled is False:
        return True
    return _prefers_json(request.headers.get("accept", ""))


def _token_response(pair: TokenPair, settings: Settings) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
        user=UserResponse.model_validate(pair.user),
    )


def _handoff_base(provider: OAuthProvider, settings: Settings) -> str:
    """SPA callback URL (same-origin relative when ``spa_base_url`` is unset)."""
    spa_base = (settings.spa_base_url or "").rstrip("/")
    return f"{spa_base}/auth/callback/{provider.value}"


def _handoff_success(pair: TokenPair, provider: OAuthProvider, settings: Settings) -> Response:
    fragment = urlencode(
        {
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_seconds,
        }
    )
    return RedirectResponse(f"{_handoff_base(provider, settings)}#{fragment}", status_code=302)


def _handoff_error(exc: SpotdlError, provider: OAuthProvider, settings: Settings) -> Response:
    if isinstance(exc, InvalidToken):
        error = _STATE_MISMATCH_ERROR
    else:
        _status, code, _detail = _status_and_code(exc)
        error = code.value
    fragment = urlencode({"error": error})
    return RedirectResponse(f"{_handoff_base(provider, settings)}#{fragment}", status_code=302)


@router.get("/{provider}/authorize")
async def authorize(
    provider: str,
    json: bool = False,
    service: OAuthService = Depends(get_oauth_service),
    clients: dict[OAuthProvider, OAuthProviderClient] = Depends(build_oauth_clients),
) -> Response:
    """Start the flow: 307 to the provider, or the URL as JSON (``?json=true``)."""
    resolved = _enabled_provider(provider, clients)
    url = service.authorize_url(resolved)
    if json:
        return JSONResponse(AuthorizeUrlResponse(authorize_url=url).model_dump(mode="json"))
    return RedirectResponse(url, status_code=307)


@router.get("/{provider}/callback", response_model=None)
async def callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    service: OAuthService = Depends(get_oauth_service),
    settings: Settings = Depends(get_settings),
    clients: dict[OAuthProvider, OAuthProviderClient] = Depends(build_oauth_clients),
) -> Response:
    """Finish the flow per the dual-mode contract (JSON body vs browser handoff).

    ``code``/``state``/``error`` are all optional because a provider consent
    denial is a standard OAuth2 redirect (``?error=access_denied&state=...`` with
    *no* ``code``): requiring ``code`` would 422 that real browser navigation
    before the dual-mode logic runs, stranding the user with a raw JSON body. A
    provider-supplied ``error`` (or a callback missing ``code``/``state``) is
    routed through the same ``_handoff_error``/JSON-envelope path as every other
    domain failure, as a ``provider_auth_error``.
    """
    resolved = _enabled_provider(provider, clients)
    json_mode = _json_mode(request, settings)
    try:
        if error is not None:
            raise ProviderAuthError(f"{resolved.value} authorization denied: {error}")
        if code is None or state is None:
            raise ProviderAuthError(f"{resolved.value} callback missing code/state")
        pair = await service.complete(resolved, code=code, state=state)
    except SpotdlError as exc:
        if json_mode:
            raise  # the shared envelope handler renders 401/400/502
        return _handoff_error(exc, resolved, settings)
    if json_mode:
        return JSONResponse(_token_response(pair, settings).model_dump(mode="json"))
    return _handoff_success(pair, resolved, settings)
