"""The root/session view-model: feature-gating + auth indicator (CONTRACT A/F).

``AppStateViewModel.load`` fetches the resolution ``config()`` and the download
(embedded) ``download_config()`` — and ``me()`` when a token is stored — into one
immutable :class:`SessionSnapshot`. Screens read the snapshot and gate sections by
hiding, never by leaking a per-request server error (CONTRACT F).
"""

from __future__ import annotations

from dataclasses import dataclass

from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.base import Loadable, guard
from spotdl_cli.viewmodels.protocol import CredentialStore, SpotdlClientProtocol


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    """The feature flags + identity the whole TUI reads (CONTRACT F)."""

    mode: str
    can_download: bool
    can_auth: bool
    can_vote: bool
    is_admin: bool
    user_email: str | None
    server_origin: str
    transport_label: str
    matcher_version: str
    degraded: bool


class AppStateViewModel:
    def __init__(
        self,
        client: SpotdlClientProtocol,
        creds: CredentialStore,
        *,
        server_origin: str,
        transport_label: str,
    ) -> None:
        self._client = client
        self._creds = creds
        self._server_origin = server_origin
        self._transport_label = transport_label

    async def load(self) -> Loadable[SessionSnapshot]:
        """Fetch config + download_config (+ optional ``me``) into a snapshot."""
        return await guard(self._build())

    async def refresh_auth(self) -> Loadable[SessionSnapshot]:
        """Re-evaluate the snapshot after a login/logout/register."""
        return await guard(self._build())

    async def _build(self) -> SessionSnapshot:
        config = await self._client.config()
        download = await self._client.download_config()
        is_admin, user_email = await self._identity(can_auth=config.features.auth)
        return SessionSnapshot(
            mode=config.mode,
            can_download=download.features.downloads,
            can_auth=config.features.auth,
            can_vote=config.features.voting,
            is_admin=is_admin,
            user_email=user_email,
            server_origin=self._server_origin,
            transport_label=self._transport_label,
            matcher_version=config.matcher_version,
            degraded=False,
        )

    async def _identity(self, *, can_auth: bool) -> tuple[bool, str | None]:
        """Resolve ``(is_admin, email)`` from a stored token, or guest defaults.

        A stored-but-rejected token (auth ``ApiError``) degrades to guest rather
        than failing the whole load; a transport failure propagates to ``guard``.
        """
        token = self._creds.get_token(self._server_origin)
        if token is None or not can_auth:
            return False, None
        try:
            user = await self._client.me(token=token)
        except ApiError:
            return False, None
        return user.is_admin, user.email
