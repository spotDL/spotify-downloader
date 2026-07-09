"""Rate-limit tiers, request classification, and client-IP extraction (CONTRACT).

Four fixed-window tiers (spec §6.4). The middleware runs *before* routing and
dependencies, so classification is a pure function of the request's method, path,
and ``Authorization`` header plus a boolean the caller computes (``authenticated``
— whether the credential locally verifies). No DB is touched in the hot path:

* a *verified* JWT → key ``"user:" + sub`` (decoded here WITHOUT signature
  verification — the caller already verified the signature; this only reads the
  claim for keying);
* everything else (anonymous, a bare-prefix PAT the hot path cannot verify, or
  any other unverifiable credential) → key ``"ip:" + client_ip``. A PAT is never
  keyed on its own text: doing so let a client mint a fresh, uncapped bucket per
  forged token, so PATs are treated as anonymous here (a genuine PAT is verified
  downstream in the auth dependency, which does touch the DB).

Tier decision order (spec §6.4): (1) authenticated + safe method → ``authed_read``;
(2) authenticated + mutating method → ``authed_write``; (3) anonymous + an
``AUTH_PATHS`` path → ``anon_auth`` (the credential-guessing throttle);
(4) anonymous otherwise (any method) → ``anon_read`` (the catch-all — an
anonymous write is budgeted here and then 401'd downstream, never reaching an
authed budget).

This module is a leaf utility: it imports neither FastAPI nor SQLAlchemy nor
``services``. It reads request attributes duck-typed (``method``, ``url.path``,
``headers``, ``client``), so a lightweight Starlette ``Request`` scope is enough
to test it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

import jwt

if TYPE_CHECKING:
    from starlette.requests import Request


class Tier(StrEnum):
    """The four rate-limit tiers (spec §6.4)."""

    ANON_READ = "anon_read"
    ANON_AUTH = "anon_auth"
    AUTHED_READ = "authed_read"
    AUTHED_WRITE = "authed_write"


# (limit, window_s) per tier — CONTRACT.
TIERS: dict[Tier, tuple[int, int]] = {
    Tier.ANON_READ: (120, 60),
    Tier.ANON_AUTH: (20, 60),
    Tier.AUTHED_READ: (600, 60),
    Tier.AUTHED_WRITE: (60, 60),
}

# The OAuth callback lives under this prefix (``/{provider}/callback``); every
# sub-path is treated as an auth endpoint for the brute-force throttle.
OAUTH_CALLBACK_PREFIX = "/api/v1/auth/oauth"

# Public auth endpoints throttled at anon_auth (credential-guessing guard). The
# OAuth prefix is a member; sub-paths under it are matched by prefix in
# :func:`_is_auth_path`.
AUTH_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        OAUTH_CALLBACK_PREFIX,
    }
)

_SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})


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


def _jwt_sub(token: str) -> str | None:
    """Return the ``sub`` claim of ``token`` without verifying its signature.

    Used only to *key* an already-verified JWT (the caller checked the signature
    when computing ``authenticated``); a decode failure yields ``None`` so the
    caller falls back to an IP key.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None


def _is_auth_path(path: str) -> bool:
    """Whether ``path`` is a public auth endpoint (throttled at anon_auth)."""
    if path in AUTH_PATHS:
        return True
    return path.startswith(OAUTH_CALLBACK_PREFIX + "/")


def client_ip(request: Request, header: str | None) -> str:
    """Resolve the caller's IP for keying (CONTRACT — spec §6.4).

    When ``header`` is configured (e.g. ``"cf-connecting-ip"`` or
    ``"x-forwarded-for"``) and present, split its value on ``","``, strip each
    part, and use index 0 (the original client in a proxy chain). If the header
    is unset, absent, or empty after stripping, fall back to the socket peer
    (``request.client.host``); a missing peer yields ``"unknown"``.
    """
    if header:
        value = request.headers.get(header)
        if value:
            first = value.split(",")[0].strip()
            if first:
                return first
    client = request.client
    if client is not None and client.host:
        return client.host
    return "unknown"


def _derive_key(request: Request, *, authenticated: bool, client_ip_header: str | None) -> str:
    """Compute the rate-limit key (no DB): verified-user sub, or IP.

    Only a caller-verified JWT is keyed to its identity (``user:`` + sub).
    Everything else — anonymous, an unverifiable JWT, or a bare-prefix PAT the
    hot path cannot verify — is keyed by IP, so no attacker-supplied token text
    can mint a fresh, uncapped bucket by varying per request.
    """
    token = _bearer_token(request)
    if authenticated and token is not None:
        sub = _jwt_sub(token)
        if sub:
            return "user:" + sub
    return "ip:" + client_ip(request, client_ip_header)


def classify(
    request: Request,
    *,
    authenticated: bool,
    client_ip_header: str | None = None,
) -> tuple[Tier, str]:
    """Return the ``(tier, key)`` for ``request`` per the spec §6.4 decision order.

    ``authenticated`` is supplied by the caller (the middleware), which verifies a
    JWT signature locally or trusts the ``spdl_pat_`` prefix — this function does
    no verification and no DB work. ``client_ip_header`` (an extension beyond the
    minimal CONTRACT signature so the pure function stays app-free and testable)
    names the trusted proxy header for IP keying; ``None`` uses the socket peer.
    """
    key = _derive_key(request, authenticated=authenticated, client_ip_header=client_ip_header)
    if authenticated:
        if request.method.upper() in _SAFE_METHODS:
            return Tier.AUTHED_READ, key
        return Tier.AUTHED_WRITE, key
    if _is_auth_path(request.url.path):
        return Tier.ANON_AUTH, key
    return Tier.ANON_READ, key
