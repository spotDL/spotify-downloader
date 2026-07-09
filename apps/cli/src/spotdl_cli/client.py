"""``SpotdlClient`` — the one façade the CLI and the Plan 9 TUI use (CONTRACT B).

``SpotdlClient`` sits on a :class:`Transport` seam (a remote HTTPS server or an
in-process embedded server) and exposes small, typed methods that map 1:1 to the
generated client operations, translating every non-2xx ``ErrorEnvelope`` into a
typed :class:`~spotdl_cli.errors.ApiError` and every success into a hand-written
``*View`` (see :mod:`spotdl_cli.views`).

Task 2 scope: the request/response methods that only need the HTTP transport
(config, resolve, search, entities, matches, lyrics, and the auth calls). Task 5
adds ``RemoteTransport``'s ``wss`` half and ``from_config``'s CONTRACT C
resolution-transport selection (probe + embedded fallback + ``--offline``), which
depends on the embedded transport built by Task 4 (resolved through the
``_embedded_factory`` seam). The embedded download methods and the WebSocket
``progress`` stream remain deferred to Plan 8 Task 7 and raise
``NotImplementedError`` here so the method surface (the seam Plan 9 builds on) is
already fixed.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import UUID

import httpx
from httpx_ws import WebSocketDisconnect
from spotdl_server.app import create_app
from spotdl_server.downloads.savefile import SaveFileV2
from spotdl_server.settings import DeploymentMode, Settings

from spotdl_cli._generated.api.api.auth import login_api_v1_auth_login_post as _login_ep
from spotdl_cli._generated.api.api.auth import me_api_v1_auth_me_get as _me_ep
from spotdl_cli._generated.api.api.downloads import (
    cancel_download_api_v1_downloads_job_id_delete as _cancel_dl_ep,
)
from spotdl_cli._generated.api.api.downloads import (
    get_batch_api_v1_downloads_batches_batch_id_get as _get_batch_ep,
)
from spotdl_cli._generated.api.api.downloads import (
    get_batch_save_file_api_v1_downloads_batches_batch_id_save_file_get as _save_file_ep,
)
from spotdl_cli._generated.api.api.downloads import (
    get_download_api_v1_downloads_job_id_get as _get_dl_ep,
)
from spotdl_cli._generated.api.api.downloads import (
    list_downloads_api_v1_downloads_get as _list_dl_ep,
)
from spotdl_cli._generated.api.api.downloads import (
    submit_download_api_v1_downloads_post as _submit_dl_ep,
)
from spotdl_cli._generated.api.api.entities import get_album_api_v1_albums_id_get as _album_ep
from spotdl_cli._generated.api.api.entities import get_artist_api_v1_artists_id_get as _artist_ep
from spotdl_cli._generated.api.api.entities import (
    get_playlist_api_v1_playlists_id_get as _playlist_ep,
)
from spotdl_cli._generated.api.api.entities import get_track_api_v1_tracks_id_get as _track_ep
from spotdl_cli._generated.api.api.entities import (
    get_track_lyrics_api_v1_tracks_id_lyrics_get as _lyrics_ep,
)
from spotdl_cli._generated.api.api.entities import (
    get_track_matches_api_v1_tracks_id_matches_get as _matches_ep,
)
from spotdl_cli._generated.api.api.meta import config_api_v1_config_get as _config_ep
from spotdl_cli._generated.api.api.resolve import resolve_api_v1_resolve_post as _resolve_ep
from spotdl_cli._generated.api.api.search import search_api_v1_search_get as _search_ep
from spotdl_cli._generated.api.api.submissions import (
    submit_match_api_v1_tracks_id_matches_post as _submit_match_ep,
)
from spotdl_cli._generated.api.api.tokens import create_token_api_v1_auth_tokens_post as _pat_ep
from spotdl_cli._generated.api.api.tokens import (
    revoke_token_api_v1_auth_tokens_token_id_delete as _revoke_ep,
)
from spotdl_cli._generated.api.client import Client
from spotdl_cli._generated.api.models.config_response import ConfigResponse
from spotdl_cli._generated.api.models.create_pat_request import CreatePatRequest
from spotdl_cli._generated.api.models.download_batch_out import DownloadBatchOut
from spotdl_cli._generated.api.models.download_job_out import DownloadJobOut
from spotdl_cli._generated.api.models.download_list_response import DownloadListResponse
from spotdl_cli._generated.api.models.download_status import DownloadStatus
from spotdl_cli._generated.api.models.download_submit_request import DownloadSubmitRequest
from spotdl_cli._generated.api.models.download_submit_response import DownloadSubmitResponse
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli._generated.api.models.error_envelope import ErrorEnvelope
from spotdl_cli._generated.api.models.error_envelope_detail_type_0 import ErrorEnvelopeDetailType0
from spotdl_cli._generated.api.models.login_request import LoginRequest
from spotdl_cli._generated.api.models.lyrics_response import LyricsResponse
from spotdl_cli._generated.api.models.match_out import MatchOut
from spotdl_cli._generated.api.models.matches_response import MatchesResponse
from spotdl_cli._generated.api.models.output_format import OutputFormat
from spotdl_cli._generated.api.models.overwrite_mode import OverwriteMode
from spotdl_cli._generated.api.models.pat_created_response import PatCreatedResponse
from spotdl_cli._generated.api.models.resolve_request import ResolveRequest
from spotdl_cli._generated.api.models.resolve_response import ResolveResponse
from spotdl_cli._generated.api.models.search_response import SearchResponse
from spotdl_cli._generated.api.models.submit_match_request import SubmitMatchRequest
from spotdl_cli._generated.api.models.token_response import TokenResponse
from spotdl_cli._generated.api.models.track_out import TrackOut
from spotdl_cli._generated.api.models.user_response import UserResponse
from spotdl_cli._generated.api.types import UNSET, Response, Unset
from spotdl_cli._generated.ws_models import WsHello, WsMessage
from spotdl_cli.errors import ApiError
from spotdl_cli.fallback import select_resolution_transport
from spotdl_cli.transport import EmbeddedTransport, RemoteTransport, Transport
from spotdl_cli.views import (
    AlbumView,
    ArtistView,
    BatchView,
    ConfigView,
    DownloadPage,
    DownloadSubmit,
    EntityView,
    JobView,
    LyricsView,
    MatchView,
    PatCreated,
    PlaylistView,
    Tokens,
    TrackView,
    UserView,
)

DEFAULT_API_URL = "https://api.spotdl.dev"
"""The community server (domain owned by the project; see the domain decision).

OVERRIDABLE via config / ``SPOTDL_API_URL`` / ``--api-url``. Never a localhost
stub, and localhost is never the shipped default.
"""

# The ``Transport`` seam and its implementors (``RemoteTransport``,
# ``EmbeddedTransport``) live in :mod:`spotdl_cli.transport`; they are re-exported
# here so ``spotdl_cli.client.RemoteTransport`` (and ``Transport``) stay importable.
__all__ = [
    "DEFAULT_API_URL",
    "EmbeddedTransport",
    "RemoteTransport",
    "SpotdlClient",
    "Transport",
    "embedded_client",
]

WS_PROTOCOL_VERSION = 1
"""The download-progress WebSocket protocol version this client speaks.

Mirrors the server's ``WS_PROTOCOL_VERSION`` (``apps/server/ws-protocol.json`` →
``ws_protocol_version``); ``progress()`` rejects a server ``WsHello`` whose
``protocol_version`` differs. The generated ``ws_models`` carry the union shape
but no version constant, so it is pinned here alongside the check that uses it.
"""


class UnsupportedProtocol(Exception):
    """The server's WS ``protocol_version`` does not match ``WS_PROTOCOL_VERSION``."""

    def __init__(self, server_version: int) -> None:
        self.server_version = server_version
        super().__init__(
            f"server speaks WS progress protocol v{server_version}, "
            f"this client speaks v{WS_PROTOCOL_VERSION}; upgrade spotdl"
        )


def _detail_dict(envelope: ErrorEnvelope) -> dict[str, Any] | None:
    detail = envelope.detail
    if isinstance(detail, ErrorEnvelopeDetailType0):
        return detail.to_dict()
    return None


def _or_unset(value: str | None) -> str | Unset:
    """Map ``None`` (an unset flag/config value) to the generator's ``UNSET``.

    A ``None`` request field means "fall back to the server's configured default"
    (CONTRACT: ``DownloadSubmitRequest`` engine fields), which the wire format
    expresses by omission, i.e. ``UNSET``.
    """
    return UNSET if value is None else value


def _unwrap(resp: Response[Any]) -> Any:
    """Return the parsed success body, or raise ``ApiError`` for a non-2xx envelope."""
    status = int(resp.status_code)
    if status < 400:
        return resp.parsed

    parsed = resp.parsed
    envelope = parsed if isinstance(parsed, ErrorEnvelope) else None
    if envelope is None:
        # Endpoints whose OpenAPI only documents 2xx (e.g. GET /config) parse an
        # error body to None; recover the envelope from the raw response.
        try:
            envelope = ErrorEnvelope.from_dict(json.loads(resp.content))
        except (ValueError, KeyError):
            raise ApiError(
                ErrorCode.INTERNAL_ERROR, message=f"HTTP {status}", status=status
            ) from None
    raise ApiError(
        envelope.code,
        message=envelope.message,
        detail=_detail_dict(envelope),
        status=status,
    )


def _embedded_settings(cfg: Any) -> Settings:
    """Derive the embedded-server ``Settings`` from the CLI config.

    Honours a ``data_dir`` from the config (so the shared ``spotdl.db`` lives
    where the user configured it); everything else follows the EMBEDDED-mode
    defaults (no auth, downloads on — spec §4).
    """
    data_dir = getattr(cfg, "data_dir", None)
    if data_dir is not None:
        return Settings(mode=DeploymentMode.EMBEDDED, data_dir=data_dir)
    return Settings(mode=DeploymentMode.EMBEDDED)


def _load_credential_token(api_url: str) -> str | None:
    """Best-effort PAT lookup for ``api_url`` from the credentials store (CONTRACT D).

    The store lives in a sibling module (``spotdl_cli.credentials``, Plan 8 Task 3),
    keyed by server origin. Resolved lazily so this module doesn't hard-depend on it;
    when absent, no token is injected (anonymous access).
    """
    try:
        credentials = importlib.import_module("spotdl_cli.credentials")
    except ModuleNotFoundError:
        return None
    getter = getattr(credentials, "get_token", None)
    if getter is None:
        return None
    token = getter(api_url)
    return token if isinstance(token, str) else None


class SpotdlClient:
    """The single client object the CLI and TUI drive.

    ``resolution`` is the remote-or-embedded transport used for metadata; the
    ``downloads`` transport is ALWAYS embedded (Plan 8 Task 4/7). Construct it
    directly with transports (as tests do), or via :meth:`from_config`, which
    applies the connectivity policy (Plan 8 Task 5).
    """

    def __init__(self, *, resolution: Transport, downloads: Transport) -> None:
        self._resolution = resolution
        self._downloads = downloads

    @classmethod
    @asynccontextmanager
    async def from_config(
        cls,
        cfg: Any,
        *,
        offline: bool = False,
        need_downloads: bool = False,
        require_remote: bool = False,
        _embedded_factory: Callable[[bool], Transport] | None = None,
    ) -> AsyncIterator[SpotdlClient]:
        """Wire transports from config and apply the fallback policy (CONTRACT C).

        The resolution transport is chosen by :func:`select_resolution_transport`
        (remote-when-reachable, else the offline embedded server; ``require_remote``
        forbids the fallback). The downloads transport is ALWAYS embedded (rule 3).

        The embedded transport itself is built by ``EmbeddedTransport`` (Plan 8
        Task 4); it is resolved through the ``_embedded_factory`` seam so this
        selection layer stays independent of that construction (tests inject a
        fake; the default resolves the sibling module lazily).
        """
        api_url = str(getattr(cfg, "api_url", None) or DEFAULT_API_URL)
        is_offline = offline or bool(getattr(cfg, "offline", False))
        token = _load_credential_token(api_url)

        def _real_embedded_factory(enable_downloads: bool) -> Transport:
            return EmbeddedTransport(_embedded_settings(cfg), enable_downloads=enable_downloads)

        build_embedded = (
            _embedded_factory if _embedded_factory is not None else _real_embedded_factory
        )

        embedded: Transport | None = None

        def make_embedded() -> Transport:
            nonlocal embedded
            if embedded is None:
                embedded = build_embedded(need_downloads)
            return embedded

        resolution = await select_resolution_transport(
            offline=is_offline,
            api_url=api_url,
            require_remote=require_remote,
            make_remote=lambda: RemoteTransport(api_url, token=token),
            make_embedded=make_embedded,
        )
        downloads = make_embedded()  # CONTRACT C rule 3: downloads are always embedded
        # EmbeddedTransport construction is sync; its server boots here (fakes
        # injected by tests have no ``start`` and are skipped).
        if embedded is not None and hasattr(embedded, "start"):
            await embedded.start()
        try:
            yield cls(resolution=resolution, downloads=downloads)
        finally:
            await resolution.aclose()
            if embedded is not None and embedded is not resolution:
                await embedded.aclose()

    @classmethod
    @asynccontextmanager
    async def _embedded(cls, cfg: Any, *, need_downloads: bool) -> AsyncIterator[SpotdlClient]:
        """Yield a client backed by a single shared :class:`EmbeddedTransport`.

        The one transport fills both the resolution and download slots: the
        metadata and download surfaces are the same in-process server, so they
        share the app, lifespan, and (single-process-owned) download pool.
        """
        settings = _embedded_settings(cfg)
        transport = EmbeddedTransport(settings, enable_downloads=need_downloads)
        await transport.start()
        try:
            yield cls(resolution=transport, downloads=transport)
        finally:
            await transport.aclose()

    def _client(self, transport: Transport, *, token: str | None = None) -> Client:
        """Wrap a transport's ``AsyncClient`` in a generated ``Client``.

        Injecting the transport's client keeps the same generated code driving
        both the remote (real ``AsyncClient``) and embedded (ASGI transport) paths.
        A per-call ``token`` sets the Bearer header for authenticated endpoints.
        """
        ac = transport.http_client()
        if token is not None:
            ac.headers["Authorization"] = f"Bearer {token}"
        return Client(base_url=transport.http_base).set_async_httpx_client(ac)

    # ---- metadata (resolution transport) ------------------------------------

    async def config(self) -> ConfigView:
        resp = await _config_ep.asyncio_detailed(client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, ConfigResponse)
        return ConfigView.from_generated(result)

    async def resolve(self, query: str) -> EntityView:
        resp = await _resolve_ep.asyncio_detailed(
            client=self._client(self._resolution), body=ResolveRequest(query=query)
        )
        result = _unwrap(resp)
        assert isinstance(result, ResolveResponse)
        return EntityView.from_generated(result.entity, degraded_sources=result.degraded_sources)

    async def search(self, q: str, *, limit: int = 10) -> list[TrackView]:
        resp = await _search_ep.asyncio_detailed(
            client=self._client(self._resolution), q=q, limit=limit
        )
        result = _unwrap(resp)
        assert isinstance(result, SearchResponse)
        return [TrackView.from_generated(t) for t in result.results]

    async def track(self, id: UUID) -> TrackView:
        resp = await _track_ep.asyncio_detailed(id=id, client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, TrackOut)
        return TrackView.from_generated(result)

    async def album(self, id: UUID) -> AlbumView:
        from spotdl_cli._generated.api.models.album_out import AlbumOut

        resp = await _album_ep.asyncio_detailed(id=id, client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, AlbumOut)
        return AlbumView.from_generated(result)

    async def artist(self, id: UUID) -> ArtistView:
        from spotdl_cli._generated.api.models.artist_out import ArtistOut

        resp = await _artist_ep.asyncio_detailed(id=id, client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, ArtistOut)
        return ArtistView.from_generated(result)

    async def playlist(self, id: UUID) -> PlaylistView:
        from spotdl_cli._generated.api.models.playlist_out import PlaylistOut

        resp = await _playlist_ep.asyncio_detailed(id=id, client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, PlaylistOut)
        return PlaylistView.from_generated(result)

    async def matches(self, track_id: UUID) -> list[MatchView]:
        resp = await _matches_ep.asyncio_detailed(
            id=track_id, client=self._client(self._resolution)
        )
        result = _unwrap(resp)
        assert isinstance(result, MatchesResponse)
        return [MatchView.from_generated(m) for m in result.matches]

    async def submit_match(self, track_id: UUID, url: str) -> MatchView:
        resp = await _submit_match_ep.asyncio_detailed(
            id=track_id,
            client=self._client(self._resolution),
            body=SubmitMatchRequest(url=url),
        )
        result = _unwrap(resp)
        assert isinstance(result, MatchOut)
        return MatchView.from_generated(result)

    async def vote_match(self, id: UUID, value: Literal["up", "down", "retract"]) -> MatchView:
        # The vote endpoint returns a VoteResponse (tallies), not a MatchOut, so
        # the CONTRACT B return type needs reconciling; deferred to the voting task.
        raise NotImplementedError("vote_match is wired in a later Plan 8 task")

    async def lyrics(self, track_id: UUID) -> list[LyricsView]:
        resp = await _lyrics_ep.asyncio_detailed(id=track_id, client=self._client(self._resolution))
        result = _unwrap(resp)
        assert isinstance(result, LyricsResponse)
        return [LyricsView.from_generated(lyric) for lyric in result.lyrics]

    async def vote_lyrics(self, id: UUID, value: Literal["up", "down", "retract"]) -> LyricsView:
        # See vote_match: the endpoint returns a VoteResponse, not a LyricsOut.
        raise NotImplementedError("vote_lyrics is wired in a later Plan 8 task")

    # ---- auth (resolution/community transport) ------------------------------

    async def login_password(self, email: str, password: str) -> Tokens:
        resp = await _login_ep.asyncio_detailed(
            client=self._client(self._resolution),
            body=LoginRequest(email=email, password=password),
        )
        result = _unwrap(resp)
        assert isinstance(result, TokenResponse)
        return Tokens.from_generated(result)

    async def create_pat(self, name: str, *, access_token: str) -> PatCreated:
        resp = await _pat_ep.asyncio_detailed(
            client=self._client(self._resolution, token=access_token),
            body=CreatePatRequest(name=name),
        )
        result = _unwrap(resp)
        assert isinstance(result, PatCreatedResponse)
        return PatCreated.from_generated(result)

    async def me(self, *, token: str) -> UserView:
        resp = await _me_ep.asyncio_detailed(client=self._client(self._resolution, token=token))
        result = _unwrap(resp)
        assert isinstance(result, UserResponse)
        return UserView.from_generated(result)

    async def revoke_pat(self, token_id: UUID, *, access_token: str) -> None:
        """Revoke one of the caller's PATs (``DELETE /auth/tokens/{id}``).

        ADDITIVE facade helper (not in the CONTRACT B method list): the ``auth
        logout`` command (Plan 8 Task 6) uses it for the best-effort server-side
        revoke of a token it minted. Raises :class:`ApiError` on a non-2xx
        envelope; the caller treats failure as non-fatal.
        """
        resp = await _revoke_ep.asyncio_detailed(
            token_id=token_id, client=self._client(self._resolution, token=access_token)
        )
        _unwrap(resp)

    # ---- downloads (ALWAYS the embedded transport) --------------------------

    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        body = DownloadSubmitRequest(
            query=req.query,
            bitrate=_or_unset(req.bitrate),
            embed_lyrics=req.embed_lyrics,
            generate_lrc=req.generate_lrc,
            generate_m3u=req.generate_m3u,
            generate_save_file=req.generate_save_file,
            m3u_template=_or_unset(req.m3u_template),
            output_format=OutputFormat(req.output_format) if req.output_format else UNSET,
            output_template=_or_unset(req.output_template),
            overwrite=OverwriteMode(req.overwrite) if req.overwrite else UNSET,
            sponsor_block=req.sponsor_block,
            update_archive=req.update_archive,
        )
        resp = await _submit_dl_ep.asyncio_detailed(client=self._client(self._downloads), body=body)
        result = _unwrap(resp)
        assert isinstance(result, DownloadSubmitResponse)
        return BatchView.from_generated(result.batch)

    async def list_downloads(
        self,
        *,
        status: str | None = None,
        batch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DownloadPage:
        resp = await _list_dl_ep.asyncio_detailed(
            client=self._client(self._downloads),
            status=DownloadStatus(status) if status is not None else UNSET,
            batch_id=batch_id if batch_id is not None else UNSET,
            limit=limit,
            offset=offset,
        )
        result = _unwrap(resp)
        assert isinstance(result, DownloadListResponse)
        return DownloadPage.from_generated(result)

    async def get_download(self, job_id: UUID) -> JobView:
        resp = await _get_dl_ep.asyncio_detailed(
            job_id=job_id, client=self._client(self._downloads)
        )
        result = _unwrap(resp)
        assert isinstance(result, DownloadJobOut)
        return JobView.from_generated(result)

    async def cancel_download(self, job_id: UUID) -> JobView:
        resp = await _cancel_dl_ep.asyncio_detailed(
            job_id=job_id, client=self._client(self._downloads)
        )
        result = _unwrap(resp)
        assert isinstance(result, DownloadJobOut)
        return JobView.from_generated(result)

    async def get_batch(self, batch_id: UUID) -> BatchView:
        resp = await _get_batch_ep.asyncio_detailed(
            batch_id=batch_id, client=self._client(self._downloads)
        )
        result = _unwrap(resp)
        assert isinstance(result, DownloadBatchOut)
        return BatchView.from_generated(result)

    async def fetch_save_file(self, batch_id: UUID) -> SaveFileV2:
        """Fetch a batch's ``.spotdl`` v2 document (raw JSON → typed ``SaveFileV2``)."""
        resp = await _save_file_ep.asyncio_detailed(
            batch_id=batch_id, client=self._client(self._downloads)
        )
        result = _unwrap(resp)
        return SaveFileV2.model_validate(result)

    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[WsMessage]]:
        """Stream WS progress frames (parsed into ``ws_models.WsMessage``).

        One code path for local and remote. Consumes the opening ``WsHello`` and
        raises :class:`UnsupportedProtocol` if the server's ``protocol_version``
        differs from :data:`WS_PROTOCOL_VERSION`; the handshake frame is not
        yielded, so callers see only job events until the socket closes.
        """
        async with self._downloads.ws_connect("/ws/progress") as session:

            async def _frames() -> AsyncIterator[WsMessage]:
                while True:
                    try:
                        raw = await session.receive_text()
                    except WebSocketDisconnect:
                        return
                    message = WsMessage.model_validate_json(raw)
                    inner = message.root
                    if isinstance(inner, WsHello):
                        version = inner.protocol_version or WS_PROTOCOL_VERSION
                        if version != WS_PROTOCOL_VERSION:
                            raise UnsupportedProtocol(version)
                        continue
                    yield message

            yield _frames()


@asynccontextmanager
async def embedded_client() -> AsyncIterator[httpx.AsyncClient]:
    """An httpx client talking to an in-process embedded-mode server.

    Kept for the skeleton ``status`` command until Plan 8 Task 4 replaces it with
    ``EmbeddedTransport``.
    """
    app = create_app(Settings(mode=DeploymentMode.EMBEDDED))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://embedded") as client:
        yield client
