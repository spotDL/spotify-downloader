"""``SpotdlClient`` — the one façade the CLI and the Plan 9 TUI use (CONTRACT B).

``SpotdlClient`` sits on a :class:`Transport` seam (a remote HTTPS server or an
in-process embedded server) and exposes small, typed methods that map 1:1 to the
generated client operations, translating every non-2xx ``ErrorEnvelope`` into a
typed :class:`~spotdl_cli.errors.ApiError` and every success into a hand-written
``*View`` (see :mod:`spotdl_cli.views`).

Task 2 scope: the request/response methods that only need the HTTP transport
(config, resolve, search, entities, matches, lyrics, and the auth calls). The
connectivity/fallback wiring (``from_config``), the embedded download methods,
and the WebSocket ``progress`` stream are deferred to Plan 8 Tasks 4-7 and raise
``NotImplementedError`` here so the method surface (the seam Plan 9 builds on) is
already fixed.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal
from uuid import UUID

import httpx
from spotdl_server.app import create_app
from spotdl_server.settings import DeploymentMode, Settings

from spotdl_cli._generated.api.api.auth import login_api_v1_auth_login_post as _login_ep
from spotdl_cli._generated.api.api.auth import me_api_v1_auth_me_get as _me_ep
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
from spotdl_cli._generated.api.client import Client
from spotdl_cli._generated.api.models.config_response import ConfigResponse
from spotdl_cli._generated.api.models.create_pat_request import CreatePatRequest
from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli._generated.api.models.error_envelope import ErrorEnvelope
from spotdl_cli._generated.api.models.error_envelope_detail_type_0 import ErrorEnvelopeDetailType0
from spotdl_cli._generated.api.models.login_request import LoginRequest
from spotdl_cli._generated.api.models.lyrics_response import LyricsResponse
from spotdl_cli._generated.api.models.match_out import MatchOut
from spotdl_cli._generated.api.models.matches_response import MatchesResponse
from spotdl_cli._generated.api.models.pat_created_response import PatCreatedResponse
from spotdl_cli._generated.api.models.resolve_request import ResolveRequest
from spotdl_cli._generated.api.models.resolve_response import ResolveResponse
from spotdl_cli._generated.api.models.search_response import SearchResponse
from spotdl_cli._generated.api.models.submit_match_request import SubmitMatchRequest
from spotdl_cli._generated.api.models.token_response import TokenResponse
from spotdl_cli._generated.api.models.track_out import TrackOut
from spotdl_cli._generated.api.models.user_response import UserResponse
from spotdl_cli._generated.api.types import Response
from spotdl_cli.errors import ApiError
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


def _detail_dict(envelope: ErrorEnvelope) -> dict[str, Any] | None:
    detail = envelope.detail
    if isinstance(detail, ErrorEnvelopeDetailType0):
        return detail.to_dict()
    return None


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
    ) -> AsyncIterator[SpotdlClient]:
        """Wire transports from config and apply the fallback policy (CONTRACT C).

        Task 4 wires the **fully-embedded** path: one in-process
        :class:`~spotdl_cli.transport.EmbeddedTransport` (loopback when
        ``need_downloads`` so WS progress works, ASGI fast path otherwise) drives
        both the resolution and the always-embedded download surface. The remote
        metadata path (``RemoteTransport`` + PAT) and the remote-vs-embedded
        selection/probe/fallback (``offline`` / ``require_remote``) land in Task 5.
        """
        if require_remote:
            raise NotImplementedError(
                "Remote selection + fallback (CONTRACT C) is wired in Plan 8 Task 5"
            )
        async with cls._embedded(cfg, need_downloads=need_downloads) as client:
            yield client

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

    # ---- downloads (ALWAYS the embedded transport) --------------------------
    # Deferred to Plan 8 Task 7 (embedded transport + WS progress).

    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        raise NotImplementedError("submit_download is wired in Plan 8 Task 7")

    async def list_downloads(self, **filters: Any) -> DownloadPage:
        raise NotImplementedError("list_downloads is wired in Plan 8 Task 7")

    async def get_download(self, job_id: UUID) -> JobView:
        raise NotImplementedError("get_download is wired in Plan 8 Task 7")

    async def cancel_download(self, job_id: UUID) -> JobView:
        raise NotImplementedError("cancel_download is wired in Plan 8 Task 7")

    async def get_batch(self, batch_id: UUID) -> BatchView:
        raise NotImplementedError("get_batch is wired in Plan 8 Task 7")

    async def fetch_save_file(self, batch_id: UUID) -> dict[str, Any]:
        # Task 7 models the response as SaveFileV2 (no generated model — the
        # save-file endpoint returns raw JSON).
        raise NotImplementedError("fetch_save_file is wired in Plan 8 Task 7")

    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[Any]]:
        """Stream WS progress frames (parsed into ``ws_models.WsMessage``).

        Deferred to Plan 8 Task 7 (one WS code path for local and remote).
        """
        raise NotImplementedError("SpotdlClient.progress is wired in Plan 8 Task 7")
        yield  # pragma: no cover  (marks this an async generator for asynccontextmanager)


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
