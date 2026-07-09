"""The rate-limit middleware — HTTP glue that applies the tier classifier.

Like ``api/deps.py``, this sits *outside* the router→service→repository layers by
design: it may import FastAPI/Starlette, ``spotdl_server.ratelimit``, and the
``spotdl_server.auth`` value types. It is added to the app **only** when
``settings.rate_limit_active()`` (hosted-only default), so when rate limiting is
off the middleware is not even mounted and requests behave exactly as if it did
not exist (a startup decision, never a per-request ``if``).

Per request it: (1) computes ``authenticated`` locally — only a JWT whose
signature+expiry verify against the configured secret counts; a bare
``spdl_pat_`` prefix is NOT trusted (PATs can only be verified against the DB,
which is off-limits in the hot path, so a forged prefix would otherwise let any
client self-elevate to an authed tier), so an unverifiable PAT is treated as
anonymous; (2) classifies the request into a ``(tier, key)`` via
:func:`~spotdl_server.ratelimit.tiers.classify`; (3) records one ``hit`` against
the process-scoped limiter on ``app.state.rate_limiter``. A blocked request gets
the Plan 5 ``rate_limited`` envelope + a ``Retry-After`` header; an allowed one
proceeds and carries ``X-RateLimit-*`` headers.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from spotdl_server.api.errors import ErrorCode, ErrorEnvelope
from spotdl_server.auth.clock import Clock
from spotdl_server.auth.tokens import TokenService, is_pat
from spotdl_server.ratelimit.base import RateLimiter
from spotdl_server.ratelimit.tiers import TIERS, classify
from spotdl_server.settings import Settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiting keyed per tier (spec §6.4)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        state = request.app.state
        limiter: RateLimiter = state.rate_limiter
        settings: Settings = state.settings
        clock: Clock = state.clock

        authenticated = _is_authenticated(_bearer_token(request), settings, clock)
        tier, key = classify(
            request,
            authenticated=authenticated,
            client_ip_header=settings.client_ip_header,
        )
        limit, window_s = TIERS[tier]
        result = await limiter.hit(key, limit=limit, window_s=window_s)

        if not result.allowed:
            retry_after = result.retry_after if result.retry_after is not None else window_s
            return _rate_limited_response(limit, window_s, retry_after)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response


def _bearer_token(request: Request) -> str | None:
    """Extract the ``Authorization: Bearer <token>`` value, or ``None``."""
    header = request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _is_authenticated(token: str | None, settings: Settings, clock: Clock) -> bool:
    """Whether ``token`` is a credential the caller may treat as authenticated.

    Only a JWT that passes local signature+expiry verification against the
    configured secret counts as authenticated. A PAT is deliberately NOT trusted
    here: it can only be verified against the DB (off-limits in the hot path), so
    a bare ``spdl_pat_`` prefix is attacker-forgeable. Trusting it would let any
    client self-elevate to an authed tier — and, because PATs were keyed on a
    hash of the token text, mint a fresh uncapped bucket per forged token. An
    unverifiable PAT is therefore treated exactly like an anonymous request
    (IP-scoped, anon tier); a genuine PAT is fully verified downstream in the
    auth dependency. When no secret is configured (rate limiting can be active
    without auth), a JWT cannot be verified and is treated as anonymous.
    """
    if token is None:
        return False
    if is_pat(token):
        return False
    if settings.auth_secret_key is None:
        return False
    service = TokenService(
        secret=settings.auth_secret_key.get_secret_value(),
        clock=clock,
        access_ttl_s=settings.access_token_ttl_seconds,
        refresh_ttl_s=settings.refresh_token_ttl_seconds,
    )
    return service.verify_access(token) is not None


def _rate_limited_response(limit: int, window_s: int, retry_after: int) -> JSONResponse:
    """The Plan 5 ``rate_limited`` envelope + a ``Retry-After`` header (429)."""
    envelope = ErrorEnvelope(
        code=ErrorCode.RATE_LIMITED,
        message="rate limit exceeded",
        detail={"limit": limit, "window": window_s, "retry_after": retry_after},
    )
    return JSONResponse(
        status_code=429,
        content=envelope.model_dump(mode="json"),  # StrEnum ``code`` -> its wire value
        headers={"Retry-After": str(retry_after)},
    )
