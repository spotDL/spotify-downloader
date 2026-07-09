"""``AuthViewModel`` — PAT login/register/status/rotate/revoke/logout (CONTRACT A/F).

When ``session.can_auth`` is False (offline/embedded, spec §4) every method
short-circuits to the copy-locked ``OFFLINE_AUTH_MESSAGE`` with **no** client call.
Login/register run the ``login/register → create_pat → store → me`` flow, minting a
named PAT and persisting it in the credential store keyed by server origin. ``rotate``
mints a fresh PAT authenticated by the current one and replaces it; ``revoke`` forgets
the local PAT (server-side revoke when the stored ``token_id`` allows — the same
signed-out effect as ``logout``, framed as dropping the token).
"""

from __future__ import annotations

import contextlib
import socket
from collections.abc import Awaitable
from uuid import UUID

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.protocol import CredentialStore, SpotdlClientProtocol
from spotdl_cli.viewmodels.types import AuthSnapshot
from spotdl_cli.views import Tokens, UserView

# EXACT literal (CONTRACT A) — copy-locked by test_vm_auth so the offline copy can
# never drift.
OFFLINE_AUTH_MESSAGE = "sign-in needs the community server; it's unavailable offline"


class AuthViewModel:
    def __init__(
        self,
        client: SpotdlClientProtocol,
        creds: CredentialStore,
        *,
        origin: str,
        session: SessionSnapshot,
    ) -> None:
        self._client = client
        self._creds = creds
        self._origin = origin
        self._session = session

    async def status(self) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        token = self._creds.get_token(self._origin)
        if token is None:
            return Loadable.ready(self._guest())
        result = await guard(self._client.me(token=token))
        if result.error is not None:
            # a transport failure propagates; a stale/invalid token reads as guest
            if result.error.code is None:
                return Loadable.failed(result.error)
            return Loadable.ready(self._guest())
        assert result.data is not None
        return Loadable.ready(self._signed_in(result.data, token))

    async def login(self, email: str, password: str) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        return await guard(self._sign_in(self._client.login_password(email, password)))

    async def register(self, email: str, password: str) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        return await guard(self._sign_in(self._client.register(email, password)))

    async def rotate(self) -> Loadable[AuthSnapshot]:
        """Mint a fresh PAT (authenticated by the current one) and replace it."""
        if not self._session.can_auth:
            return self._offline()
        token = self._creds.get_token(self._origin)
        if token is None:
            return Loadable.ready(self._guest())
        return await guard(self._rotate(token))

    async def revoke(self) -> Loadable[AuthSnapshot]:
        """Revoke the PAT server-side when its id is stored, then forget it locally.

        The server call is best-effort: any failure (offline server, stale token)
        still ends in the signed-out local state — identical to ``logout``.
        """
        if not self._session.can_auth:
            return self._offline()
        token = self._creds.get_token(self._origin)
        token_id = self._creds.get_token_id(self._origin)
        if token is not None and token_id is not None:
            with contextlib.suppress(Exception):
                await self._client.revoke_pat(UUID(token_id), access_token=token)
        self._creds.delete_token(self._origin)
        return Loadable.ready(self._guest())

    async def logout(self) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        self._creds.delete_token(self._origin)
        return Loadable.ready(self._guest())

    async def _sign_in(self, tokens_coro: Awaitable[Tokens]) -> AuthSnapshot:
        tokens = await tokens_coro
        pat = await self._client.create_pat(name=self._pat_name(), access_token=tokens.access_token)
        self._creds.store_token(self._origin, pat.token, tokens.user.email)
        user = await self._client.me(token=pat.token)
        return self._signed_in(user, pat.token)

    async def _rotate(self, current: str) -> AuthSnapshot:
        pat = await self._client.create_pat(name=self._pat_name(), access_token=current)
        user = await self._client.me(token=pat.token)
        self._creds.store_token(self._origin, pat.token, user.email)
        return self._signed_in(user, pat.token)

    def _signed_in(self, user: UserView, token: str) -> AuthSnapshot:
        return AuthSnapshot(
            logged_in=True,
            email=user.email,
            server_origin=self._origin,
            is_admin=user.is_admin,
            masked_token=_mask(token),
        )

    def _guest(self) -> AuthSnapshot:
        return AuthSnapshot(False, None, self._origin)

    def _pat_name(self) -> str:
        return f"spotdl-tui {socket.gethostname()}"

    def _offline(self) -> Loadable[AuthSnapshot]:
        return Loadable.failed(ErrorDisplay(OFFLINE_AUTH_MESSAGE, code=None, severity="error"))


def _mask(token: str) -> str:
    """Mask a PAT for display: keep a short prefix, hide the rest."""
    return f"{token[:6]}••••••••" if token else ""
