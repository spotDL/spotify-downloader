"""Token minting, hashing, and verification (CONTRACT — spec §6.2).

Three token kinds, all pure and DB-free here (persistence + rotation/reuse
detection live in later tasks):

* **Access token** — a short-lived (15 min default) HS256 JWT. Stateless: it
  carries ``is_admin`` so the auth dependency needn't hit the DB per request,
  and it is *never* blacklisted — revocation rides on the refresh family plus
  the short TTL.
* **Refresh token** — an opaque ``secrets.token_urlsafe(32)`` string (not a
  JWT), stored only as a sha256 hex digest. Rotating + reuse-detecting.
* **PAT** — a personal access token for the CLI: ``spdl_pat_`` + an opaque
  secret. The literal ``spdl_pat_`` prefix is how the auth dependency tells a
  PAT from a JWT; only the sha256 digest and a short display prefix are stored.

All time — ``iat``/``exp`` on mint and expiry on verify — flows through the
injected :class:`~spotdl_server.auth.clock.Clock`, so tests fully control expiry
through a fake clock. This module imports neither FastAPI nor SQLAlchemy.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from spotdl_server.auth.clock import Clock

_PAT_PREFIX = "spdl_pat_"
_PAT_DISPLAY_CHARS = 6
_JWT_ALG = "HS256"
_ACCESS_TYPE = "access"


def sha256_hex(token: str) -> str:
    """Return the sha256 hex digest of ``token`` (how tokens are stored)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    """Mint a fresh opaque refresh token (url-safe, ~43 chars). Not a JWT."""
    return secrets.token_urlsafe(32)


def new_pat() -> tuple[str, str]:
    """Mint a personal access token.

    Returns ``(full, token_prefix)`` where ``full`` is the once-shown secret
    (``spdl_pat_`` + a url-safe secret) and ``token_prefix`` is the persisted
    display handle (``spdl_pat_`` + the first six secret characters).
    """
    secret = secrets.token_urlsafe(32)
    full = _PAT_PREFIX + secret
    prefix = _PAT_PREFIX + secret[:_PAT_DISPLAY_CHARS]
    return full, prefix


def is_pat(token: str) -> bool:
    """Return whether ``token`` is a PAT (has the ``spdl_pat_`` prefix)."""
    return token.startswith(_PAT_PREFIX)


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """The verified identity carried by a valid access JWT."""

    user_id: UUID
    is_admin: bool


class TokenService:
    """Mints and verifies access JWTs; computes refresh-token expiry.

    The signing ``secret`` comes from ``Settings`` (never hardcoded) and the
    ``clock`` is injected so expiry is deterministic in tests. TTLs default to
    the contract values (15 min access, 30 day refresh) and are overridable for
    focused tests and future tuning.
    """

    def __init__(
        self,
        *,
        secret: str,
        clock: Clock,
        access_ttl_s: int = 900,
        refresh_ttl_s: int = 2_592_000,
    ) -> None:
        self._secret = secret
        self._clock = clock
        self._access_ttl_s = access_ttl_s
        self._refresh_ttl_s = refresh_ttl_s

    def mint_access(self, *, user_id: UUID, is_admin: bool) -> str:
        """Mint a signed HS256 access JWT for ``user_id`` per the claims contract.

        ``iat``/``exp`` are derived from ``clock.now()`` so a fake clock fully
        controls the token's lifetime.
        """
        issued = int(self._clock.now().timestamp())
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "iat": issued,
            "exp": issued + self._access_ttl_s,
            "type": _ACCESS_TYPE,
            "is_admin": is_admin,
        }
        return jwt.encode(payload, self._secret, algorithm=_JWT_ALG)

    def verify_access(self, token: str) -> AccessClaims | None:
        """Verify an access JWT, returning its claims or ``None`` if invalid.

        Returns ``None`` — never raises — for a bad signature, wrong secret,
        malformed token, missing required claim, a non-``access`` ``type``, an
        unparseable ``sub``, or an expired token. Callers treat ``None`` as
        unauthenticated (no exception leaks to the client as a 500).

        Expiry is evaluated against the injected :class:`Clock`, not PyJWT's
        internal wall clock: PyJWT exposes no now-injection seam, so signature
        and required-claim checks run through :func:`jwt.decode` while the
        ``exp`` comparison is done here, keeping the ``Clock`` the single
        time-control seam the contract mandates (``FakeClock`` controls expiry).
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret,
                algorithms=[_JWT_ALG],
                options={"require": ["exp", "sub", "type"], "verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return None

        if payload.get("type") != _ACCESS_TYPE:
            return None

        if int(self._clock.now().timestamp()) >= int(payload["exp"]):
            return None

        try:
            user_id = UUID(str(payload["sub"]))
        except (ValueError, TypeError):
            return None

        return AccessClaims(user_id=user_id, is_admin=bool(payload.get("is_admin", False)))

    def refresh_expiry(self) -> datetime:
        """Return the absolute expiry for a refresh token minted *now*."""
        return self._clock.now() + timedelta(seconds=self._refresh_ttl_s)
