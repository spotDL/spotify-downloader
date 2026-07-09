"""``AuthViewModel`` — PAT login/register/status/logout (CONTRACT A/F).

When ``session.can_auth`` is False (offline/embedded, spec §4) every method
short-circuits to the copy-locked ``OFFLINE_AUTH_MESSAGE`` with **no** client call.
Login/register run the ``login/register → create_pat → store → me`` flow, minting a
named PAT and persisting it in the credential store keyed by server origin.
"""

from __future__ import annotations

import socket
from collections.abc import Awaitable

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.protocol import CredentialStore, SpotdlClientProtocol
from spotdl_cli.viewmodels.types import AuthSnapshot
from spotdl_cli.views import Tokens

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
            return Loadable.ready(AuthSnapshot(False, None, self._origin))
        result = await guard(self._client.me(token=token))
        if result.error is not None:
            # a transport failure propagates; a stale/invalid token reads as guest
            if result.error.code is None:
                return Loadable.failed(result.error)
            return Loadable.ready(AuthSnapshot(False, None, self._origin))
        assert result.data is not None
        return Loadable.ready(AuthSnapshot(True, result.data.email, self._origin))

    async def login(self, email: str, password: str) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        return await guard(self._sign_in(self._client.login_password(email, password)))

    async def register(self, email: str, password: str) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        return await guard(self._sign_in(self._client.register(email, password)))

    async def logout(self) -> Loadable[AuthSnapshot]:
        if not self._session.can_auth:
            return self._offline()
        self._creds.delete_token(self._origin)
        return Loadable.ready(AuthSnapshot(False, None, self._origin))

    async def _sign_in(self, tokens_coro: Awaitable[Tokens]) -> AuthSnapshot:
        tokens = await tokens_coro
        pat = await self._client.create_pat(
            name=f"spotdl-tui {socket.gethostname()}", access_token=tokens.access_token
        )
        self._creds.store_token(self._origin, pat.token, tokens.user.email)
        user = await self._client.me(token=pat.token)
        return AuthSnapshot(True, user.email, self._origin)

    def _offline(self) -> Loadable[AuthSnapshot]:
        return Loadable.failed(ErrorDisplay(OFFLINE_AUTH_MESSAGE, code=None, severity="error"))
