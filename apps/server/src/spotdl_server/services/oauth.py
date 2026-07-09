"""OAuthService — GitHub/Discord login-or-register + identity linking (spec §6.2).

The orchestration seam for ``/api/v1/auth/oauth``: it drives the pure provider
clients (:mod:`spotdl_server.auth.oauth_providers`) through the authorization-code
flow, then reconciles the returned account against our ``users`` /
``oauth_identities`` tables to log the caller in, link an OAuth identity onto an
existing password account, or create a fresh OAuth-only account. On success it
mints our own access JWT + a new refresh family (identical issuance to
:class:`~spotdl_server.services.auth.AuthService`) and returns a
:class:`~spotdl_server.services.auth.TokenPair`.

**Stateless CSRF ``state``.** There is deliberately no DB row for OAuth ``state``:
:func:`sign_state` packs a random nonce and an expiry into a base64url payload and
HMAC-signs it with the auth secret; :func:`verify_state` recomputes the MAC in
constant time and checks expiry against the injected :class:`Clock`. A tampered,
forged, or expired ``state`` raises :class:`InvalidToken` (the callback renders it
as an ``invalid_token`` / ``oauth_state_mismatch`` failure).

Time flows exclusively through the injected ``Clock`` (state expiry, token
expiry) and the service never commits — the ``get_session`` dependency owns the
unit of work. Nothing here imports FastAPI.

**Note on the CONTRACT signature (documented deviation).** The task brief lists
``OAuthService.__init__`` without a signing secret or redirect base, and
``sign_state(clock, ttl=600)`` / ``verify_state(state, clock)`` without a secret.
Both operations *require* the auth secret, and the redirect URI (embedded in the
authorize URL and replayed on token exchange) is derived from
``settings.oauth_redirect_base_url``; per the "secrets come from ``Settings``
only" rule the secret cannot be a module constant or captured in a closure. So
``auth_secret`` + ``redirect_base_url`` are added as explicit injected
constructor arguments (sourced from ``Settings`` in the dependency), and the
state functions take ``secret`` as a keyword — the smallest change that keeps the
brief's stateless-HMAC design while honouring the secrets rule.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.auth.clock import Clock
from spotdl_server.auth.oauth_providers import OAuthProviderClient, OAuthUserInfo
from spotdl_server.auth.tokens import TokenService, new_refresh_token, sha256_hex
from spotdl_server.db.enums import OAuthProvider
from spotdl_server.db.models import User
from spotdl_server.repositories.tokens import RefreshTokenRepository
from spotdl_server.repositories.users import OAuthIdentityRepository, UserRepository
from spotdl_server.services.auth import TokenPair, normalize_email
from spotdl_server.services.errors import InvalidToken, OAuthEmailRequired

_STATE_TTL_SECONDS = 600
_NONCE_BYTES = 16
_EXP_BYTES = 8
_CALLBACK_PATH = "/api/v1/auth/oauth/{provider}/callback"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _mac(secret: str, payload: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()


def sign_state(*, secret: str, clock: Clock, ttl: int = _STATE_TTL_SECONDS) -> str:
    """Return a signed, self-describing ``state`` token (no DB row).

    Format: ``base64url(nonce || exp) + "." + hmac_sha256(secret, payload)`` where
    ``exp`` is an 8-byte big-endian unix expiry ``now + ttl``. The nonce makes
    each state unique/unguessable; the MAC makes it unforgeable.
    """
    nonce = secrets.token_bytes(_NONCE_BYTES)
    exp = int(clock.now().timestamp()) + ttl
    payload = _b64url_encode(nonce + exp.to_bytes(_EXP_BYTES, "big"))
    return f"{payload}.{_mac(secret, payload)}"


def verify_state(state: str, *, secret: str, clock: Clock) -> None:
    """Verify a ``state`` token, raising :class:`InvalidToken` if it is unusable.

    Rejects (all as the same :class:`InvalidToken`, no distinction leaked): a
    malformed token, a bad/forged signature (constant-time compared), or an
    expired one (checked against the injected clock).
    """
    payload, sep, signature = state.partition(".")
    if not sep or not payload or not signature:
        raise InvalidToken("invalid oauth state")
    if not hmac.compare_digest(signature, _mac(secret, payload)):
        raise InvalidToken("invalid oauth state")
    try:
        raw = _b64url_decode(payload)
        exp = int.from_bytes(raw[_NONCE_BYTES : _NONCE_BYTES + _EXP_BYTES], "big")
    except (ValueError, IndexError) as exc:  # pragma: no cover - MAC makes this unreachable
        raise InvalidToken("invalid oauth state") from exc
    if int(clock.now().timestamp()) >= exp:
        raise InvalidToken("oauth state expired")


class OAuthService:
    """Complete a provider login into one of our sessions (login/link/register)."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        token_service: TokenService,
        clock: Clock,
        users: UserRepository,
        identities: OAuthIdentityRepository,
        refresh_tokens: RefreshTokenRepository,
        clients: dict[OAuthProvider, OAuthProviderClient],
        auth_secret: str,
        redirect_base_url: str,
    ) -> None:
        self._session = session
        self._token_service = token_service
        self._clock = clock
        self._users = users
        self._identities = identities
        self._refresh_tokens = refresh_tokens
        self._clients = clients
        self._auth_secret = auth_secret
        self._redirect_base_url = redirect_base_url

    def authorize_url(self, provider: OAuthProvider) -> str:
        """Sign a fresh ``state`` and return the provider's authorize URL."""
        state = sign_state(secret=self._auth_secret, clock=self._clock)
        client = self._clients[provider]
        return client.authorize_url(state=state, redirect_uri=self._redirect_uri(provider))

    async def complete(self, provider: OAuthProvider, *, code: str, state: str) -> TokenPair:
        """Verify ``state``, exchange ``code``, then log in / link / register.

        Steps: (1) verify the CSRF ``state`` (bad → :class:`InvalidToken`);
        (2) exchange the code for the provider token and read the account;
        (3) resolve it to a local user — existing identity, else link onto a
        matching-email account, else (an email is required) create one; and
        (4) mint our access JWT + a new refresh family.
        """
        verify_state(state, secret=self._auth_secret, clock=self._clock)
        client = self._clients[provider]
        provider_token = await client.exchange_code(
            code=code, redirect_uri=self._redirect_uri(provider)
        )
        info = await client.fetch_user_info(access_token=provider_token)
        user = await self._resolve_user(provider, info)
        return await self._issue_pair(user)

    def _redirect_uri(self, provider: OAuthProvider) -> str:
        base = self._redirect_base_url.rstrip("/")
        return base + _CALLBACK_PATH.format(provider=provider.value)

    async def _resolve_user(self, provider: OAuthProvider, info: OAuthUserInfo) -> User:
        """Map provider account facts to a local user (login / link / register)."""
        identity = await self._identities.get_by_provider_account(
            provider, info.provider_account_id
        )
        if identity is not None:
            existing = await self._users.get(identity.user_id)
            if existing is not None:
                return existing

        normalized = normalize_email(info.email) if info.email else None
        if normalized is not None:
            by_email = await self._users.get_by_email(normalized)
            if by_email is not None:
                await self._identities.link(
                    user_id=by_email.id,
                    provider=provider,
                    provider_account_id=info.provider_account_id,
                    provider_username=info.username,
                )
                return by_email

        if normalized is None:
            # No usable email and no existing identity: we refuse to synthesize a
            # placeholder address, so the account cannot be created (spec §6.2).
            raise OAuthEmailRequired()

        user = await self._users.create(
            email=normalized, password_hash=None, display_name=info.username
        )
        await self._identities.link(
            user_id=user.id,
            provider=provider,
            provider_account_id=info.provider_account_id,
            provider_username=info.username,
        )
        return user

    async def _issue_pair(self, user: User) -> TokenPair:
        """Mint an access JWT and open a brand-new refresh family for ``user``."""
        refresh_plain = new_refresh_token()
        await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=sha256_hex(refresh_plain),
            family_id=uuid4(),
            expires_at=self._token_service.refresh_expiry(),
        )
        access = self._token_service.mint_access(user_id=user.id, is_admin=user.is_admin)
        return TokenPair(access_token=access, refresh_token=refresh_plain, user=user)
