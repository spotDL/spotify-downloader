"""``FakeSpotdlClient`` + ``*View`` builders — the offline test double (Plan 9).

The fake implements :class:`~spotdl_cli.viewmodels.protocol.SpotdlClientProtocol`
from injectable canned ``views.*`` data and a controllable WebSocket frame source
(``push_ws`` / ``close_ws``). Every view-model test runs against it — no real client,
embedded server, network, or terminal.
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from spotdl_cli.errors import ApiError
from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.views import (
    AdminUserView,
    AlbumRefView,
    AlbumView,
    ArtistView,
    BatchView,
    ConfigView,
    DownloadDefaultsView,
    DownloadPage,
    DownloadSubmit,
    EntityView,
    FeatureFlagsView,
    JobView,
    LyricsView,
    MatchView,
    PagedUsersView,
    PatCreated,
    PlaylistView,
    ReportView,
    SearchResultView,
    StatsView,
    Tokens,
    TrackView,
    UserView,
    WsBatchFinished,
    WsHello,
    WsJobCancelled,
    WsJobFailed,
    WsJobFinished,
    WsJobQueued,
    WsJobStarted,
    WsMessage,
    WsProgress,
)

_EPOCH = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


# --- view builders (minimal args, sensible defaults) -------------------------


def make_features(
    *, auth: bool = True, downloads: bool = True, library: bool = True, voting: bool = True
) -> FeatureFlagsView:
    return FeatureFlagsView(auth=auth, downloads=downloads, library=library, voting=voting)


def make_config(
    *,
    mode: str = "self_host",
    matcher_version: str = "m1",
    features: FeatureFlagsView | None = None,
    with_defaults: bool = False,
) -> ConfigView:
    defaults = (
        DownloadDefaultsView(
            add_unavailable=False,
            bitrate="auto",
            concurrency=4,
            create_skip_file=False,
            detect_formats=["mp3"],
            id3_separator="/",
            max_filename_length=None,
            output_format="mp3",
            output_template="{title}.{output-ext}",
            playlist_numbering=False,
            respect_skip_file=False,
            restrict="none",
            retain_track_cover=False,
            scan_existing=False,
            skip_explicit=False,
        )
        if with_defaults
        else None
    )
    return ConfigView(
        mode=mode,
        matcher_version=matcher_version,
        oauth_providers=[],
        features=features if features is not None else make_features(),
        download_defaults=defaults,
    )


def make_track(
    *,
    id: UUID | None = None,
    name: str = "Song",
    artists: list[str] | None = None,
    duration_ms: int = 185_000,
    explicit: bool | None = False,
    album: AlbumRefView | None = None,
) -> TrackView:
    return TrackView(
        id=str(id or uuid4()),
        name=name,
        artists=artists if artists is not None else ["Artist"],
        duration_ms=duration_ms,
        album=album if album is not None else AlbumRefView(id=str(uuid4()), name="Album"),
        explicit=explicit,
    )


def make_match(
    *,
    id: UUID | None = None,
    status: str = "auto",
    score: float = 0.9,
    net_score: int = 3,
    upvotes: int = 4,
    downvotes: int = 1,
    provider: str = "youtube",
    url: str = "https://youtu.be/x",
) -> MatchView:
    return MatchView(
        id=str(id or uuid4()),
        status=status,
        score=score,
        net_score=net_score,
        upvotes=upvotes,
        downvotes=downvotes,
        matcher_version="m1",
        target_provider=provider,
        target_id="x",
        target_url=url,
    )


def make_lyrics(
    *,
    id: UUID | None = None,
    kind: str = "plain",
    source: str = "genius",
    text: str = "line one\nline two",
    net_score: int = 2,
) -> LyricsView:
    return LyricsView(
        id=str(id or uuid4()),
        kind=kind,
        source=source,
        text=text,
        upvotes=net_score,
        downvotes=0,
        net_score=net_score,
    )


def make_album(
    *, id: UUID | None = None, name: str = "Discovery", tracks: list[TrackView] | None = None
) -> AlbumView:
    return AlbumView(
        id=str(id or uuid4()),
        name=name,
        album_artist="Daft Punk",
        track_count=len(tracks) if tracks is not None else 1,
        year=2001,
        tracks=tracks if tracks is not None else [make_track()],
    )


def make_artist(
    *, id: UUID | None = None, name: str = "Daft Punk", tracks: list[TrackView] | None = None
) -> ArtistView:
    return ArtistView(
        id=str(id or uuid4()),
        name=name,
        genres=["french house"],
        tracks=tracks if tracks is not None else [make_track()],
    )


def make_playlist(
    *, id: UUID | None = None, name: str = "Mix", tracks: list[TrackView] | None = None
) -> PlaylistView:
    return PlaylistView(
        id=str(id or uuid4()),
        name=name,
        owner="curator",
        tracks=tracks if tracks is not None else [make_track()],
    )


def make_user(*, email: str = "user@example.com", is_admin: bool = False) -> UserView:
    return UserView(id=str(uuid4()), email=email, is_admin=is_admin, created_at=_EPOCH)


def make_admin_user(
    *,
    email: str = "user@example.com",
    display_name: str | None = None,
    is_admin: bool = False,
    is_active: bool = True,
) -> AdminUserView:
    return AdminUserView(
        id=str(uuid4()),
        email=email,
        is_admin=is_admin,
        is_active=is_active,
        created_at=_EPOCH,
        display_name=display_name,
    )


def make_tokens(*, access_token: str = "access-jwt", user: UserView | None = None) -> Tokens:
    return Tokens(
        access_token=access_token,
        refresh_token="refresh",
        expires_in=3600,
        token_type="bearer",
        user=user if user is not None else make_user(),
    )


def make_pat(*, token: str = "pat-secret", name: str = "spotdl-tui host") -> PatCreated:
    return PatCreated(
        id=str(uuid4()), name=name, token=token, token_prefix=token[:6], created_at=_EPOCH
    )


def make_job(
    *,
    id: UUID | None = None,
    status: str = "queued",
    progress: float = 0.0,
    batch_id: UUID | None = None,
    track_name: str = "Song",
    artists: list[str] | None = None,
    output_path: str | None = None,
    skip_reason: str | None = None,
) -> JobView:
    return JobView(
        id=str(id or uuid4()),
        status=status,
        progress=progress,
        track_name=track_name,
        artists=artists if artists is not None else ["Artist"],
        output_path=output_path,
        skip_reason=skip_reason,
        batch_id=str(batch_id) if batch_id is not None else None,
    )


def make_batch(*, batch_id: UUID | None = None, jobs: list[JobView] | None = None) -> BatchView:
    job_list = jobs if jobs is not None else [make_job()]
    return BatchView(
        batch_id=str(batch_id or uuid4()),
        kind="track",
        finalized=False,
        total_jobs=len(job_list),
        counts={},
        jobs=job_list,
    )


def make_download_page(*, jobs: list[JobView] | None = None) -> DownloadPage:
    job_list = jobs if jobs is not None else []
    return DownloadPage(jobs=job_list, total=len(job_list), limit=50, offset=0)


def make_report(
    *,
    id: UUID | None = None,
    subject_type: str = "track",
    status: str = "pending",
    reason: str | None = "wrong title",
) -> ReportView:
    return ReportView(
        id=str(id or uuid4()),
        subject_type=subject_type,
        subject_id=str(uuid4()),
        status=status,
        created_at=_EPOCH,
        reason=reason,
    )


def make_session(
    *,
    mode: str = "self_host",
    can_download: bool = True,
    can_auth: bool = True,
    can_vote: bool = True,
    library: bool = True,
    is_admin: bool = False,
    user_email: str | None = None,
    server_origin: str = "https://api.example.test",
    transport_label: str = "remote · api.example.test",
    matcher_version: str = "m1",
    degraded: bool = False,
) -> SessionSnapshot:
    return SessionSnapshot(
        mode=mode,
        can_download=can_download,
        can_auth=can_auth,
        can_vote=can_vote,
        library=library,
        is_admin=is_admin,
        user_email=user_email,
        server_origin=server_origin,
        transport_label=transport_label,
        matcher_version=matcher_version,
        degraded=degraded,
    )


def make_stats() -> StatsView:
    return StatsView(
        users_total=10,
        matches_total=20,
        community_verified_matches=5,
        rejected_matches=2,
        reports_total=7,
        reports_pending=3,
        votes_total=42,
    )


# --- WebSocket frame builders ------------------------------------------------


def ws_hello(*, protocol_version: int = 1) -> WsMessage:
    return WsMessage(WsHello(protocol_version=protocol_version))


def ws_queued(job_id: UUID, batch_id: UUID, *, track_name: str = "Song") -> WsMessage:
    return WsMessage(
        WsJobQueued(
            job_id=job_id,
            batch_id=batch_id,
            track_name=track_name,
            list_length=1,
            list_position=0,
        )
    )


def ws_started(job_id: UUID, batch_id: UUID) -> WsMessage:
    return WsMessage(WsJobStarted(job_id=job_id, batch_id=batch_id))


def ws_progress(
    job_id: UUID,
    batch_id: UUID,
    *,
    phase: str = "download",
    percent: int = 50,
    overall: float = 0.5,
) -> WsMessage:
    return WsMessage(
        WsProgress(job_id=job_id, batch_id=batch_id, phase=phase, percent=percent, overall=overall)
    )


def ws_finished(
    job_id: UUID,
    batch_id: UUID,
    *,
    output_path: str = "/music/song.mp3",
    skipped: bool = False,
    skip_reason: str | None = None,
) -> WsMessage:
    return WsMessage(
        WsJobFinished(
            job_id=job_id,
            batch_id=batch_id,
            status="completed",
            output_path=output_path,
            skipped=skipped,
            skip_reason=skip_reason,
        )
    )


def ws_failed(
    job_id: UUID, batch_id: UUID, *, step: str = "download", error: str = "boom"
) -> WsMessage:
    return WsMessage(WsJobFailed(job_id=job_id, batch_id=batch_id, step=step, error=error))


def ws_cancelled(job_id: UUID, batch_id: UUID) -> WsMessage:
    return WsMessage(WsJobCancelled(job_id=job_id, batch_id=batch_id))


def ws_batch_finished(
    batch_id: UUID,
    *,
    completed: int = 1,
    failed: int = 0,
    skipped: int = 0,
    cancelled: int = 0,
) -> WsMessage:
    return WsMessage(
        WsBatchFinished(
            batch_id=batch_id,
            completed=completed,
            failed=failed,
            skipped=skipped,
            cancelled=cancelled,
            m3u_paths=[],
            save_file_path=None,
        )
    )


# --- the fake client ---------------------------------------------------------


class FakeSpotdlClient:
    """An in-memory ``SpotdlClientProtocol`` driven by canned data + a WS queue."""

    def __init__(
        self,
        *,
        config: ConfigView | None = None,
        download_config: ConfigView | None = None,
    ) -> None:
        self.config_view = config if config is not None else make_config()
        self.download_config_view = (
            download_config if download_config is not None else make_config()
        )
        # per-key canned returns (tests override); keyed by method name where a
        # single canned value suffices, or by entity id for the lookup methods.
        self.search_results: list[TrackView] = []
        self.search_degraded: list[str] = []
        self.resolve_result: EntityView | None = None
        self.tracks: dict[str, TrackView] = {}
        self.albums: dict[str, AlbumView] = {}
        self.artists: dict[str, ArtistView] = {}
        self.playlists: dict[str, PlaylistView] = {}
        self.matches_by_track: dict[str, list[MatchView]] = {}
        self.lyrics_by_track: dict[str, list[LyricsView]] = {}
        self.vote_match_result: MatchView | None = None
        self.vote_lyrics_result: LyricsView | None = None
        self.submit_match_result: MatchView | None = None
        self.users_by_token: dict[str, UserView] = {}
        self.login_result: Tokens | None = None
        self.register_result: Tokens | None = None
        self.pat_result: PatCreated | None = None
        self.submit_download_result: BatchView | None = None
        # An empty queue by default so any section screen loads without setup;
        # tests seed a specific page by assigning this.
        self.download_page: DownloadPage = make_download_page(jobs=[])
        self.jobs: dict[str, JobView] = {}
        self.batches: dict[str, BatchView] = {}
        self.report_result: ReportView | None = None
        self.my_reports_list: list[ReportView] = []
        self.admin_reports_list: list[ReportView] = []
        self.admin_users_list: list[AdminUserView] = []
        self.stats_result: StatsView | None = None
        # inject a raise: method-name -> exception
        self.errors: dict[str, ApiError] = {}
        # call log: (method, args, kwargs)
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self._ws_queue: asyncio.Queue[WsMessage | None] = asyncio.Queue()

    # -- recording + error injection --
    def _record(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append((name, args, kwargs))

    def _maybe_raise(self, name: str) -> None:
        exc = self.errors.get(name)
        if exc is not None:
            raise exc

    def called(self, name: str) -> bool:
        return any(call[0] == name for call in self.calls)

    # -- WebSocket source --
    def push_ws(self, frame: WsMessage) -> None:
        self._ws_queue.put_nowait(frame)

    def close_ws(self) -> None:
        self._ws_queue.put_nowait(None)

    # -- metadata --
    async def config(self) -> ConfigView:
        self._record("config")
        self._maybe_raise("config")
        return self.config_view

    async def download_config(self) -> ConfigView:
        self._record("download_config")
        self._maybe_raise("download_config")
        return self.download_config_view

    async def resolve(self, query: str) -> EntityView:
        self._record("resolve", query)
        self._maybe_raise("resolve")
        assert self.resolve_result is not None
        return self.resolve_result

    async def search(self, q: str, *, limit: int = 10) -> SearchResultView:
        self._record("search", q, limit=limit)
        self._maybe_raise("search")
        return SearchResultView(tracks=self.search_results, degraded_sources=self.search_degraded)

    async def track(self, id: UUID) -> TrackView:
        self._record("track", id)
        self._maybe_raise("track")
        return self.tracks[str(id)]

    async def album(self, id: UUID) -> AlbumView:
        self._record("album", id)
        self._maybe_raise("album")
        return self.albums[str(id)]

    async def artist(self, id: UUID) -> ArtistView:
        self._record("artist", id)
        self._maybe_raise("artist")
        return self.artists[str(id)]

    async def playlist(self, id: UUID) -> PlaylistView:
        self._record("playlist", id)
        self._maybe_raise("playlist")
        return self.playlists[str(id)]

    async def matches(self, track_id: UUID) -> list[MatchView]:
        self._record("matches", track_id)
        self._maybe_raise("matches")
        return self.matches_by_track.get(str(track_id), [])

    async def submit_match(self, track_id: UUID, url: str) -> MatchView:
        self._record("submit_match", track_id, url)
        self._maybe_raise("submit_match")
        assert self.submit_match_result is not None
        return self.submit_match_result

    async def vote_match(self, id: UUID, value: str) -> MatchView:
        self._record("vote_match", id, value)
        self._maybe_raise("vote_match")
        assert self.vote_match_result is not None
        return self.vote_match_result

    async def lyrics(self, track_id: UUID) -> list[LyricsView]:
        self._record("lyrics", track_id)
        self._maybe_raise("lyrics")
        return self.lyrics_by_track.get(str(track_id), [])

    async def vote_lyrics(self, id: UUID, value: str) -> LyricsView:
        self._record("vote_lyrics", id, value)
        self._maybe_raise("vote_lyrics")
        assert self.vote_lyrics_result is not None
        return self.vote_lyrics_result

    # -- auth --
    async def me(self, *, token: str) -> UserView:
        self._record("me", token=token)
        self._maybe_raise("me")
        user = self.users_by_token.get(token)
        if user is None:
            raise ApiError(_invalid_token_code(), message="invalid token")
        return user

    async def login_password(self, email: str, password: str) -> Tokens:
        self._record("login_password", email, password)
        self._maybe_raise("login_password")
        assert self.login_result is not None
        return self.login_result

    async def register(self, email: str, password: str) -> Tokens:
        self._record("register", email, password)
        self._maybe_raise("register")
        assert self.register_result is not None
        return self.register_result

    async def create_pat(self, name: str, *, access_token: str) -> PatCreated:
        self._record("create_pat", name, access_token=access_token)
        self._maybe_raise("create_pat")
        assert self.pat_result is not None
        return self.pat_result

    # -- downloads --
    async def submit_download(self, req: DownloadSubmit) -> BatchView:
        self._record("submit_download", req)
        self._maybe_raise("submit_download")
        assert self.submit_download_result is not None
        return self.submit_download_result

    async def list_downloads(self, **filters: object) -> DownloadPage:
        self._record("list_downloads", **filters)
        self._maybe_raise("list_downloads")
        return self.download_page

    async def get_download(self, job_id: UUID) -> JobView:
        self._record("get_download", job_id)
        self._maybe_raise("get_download")
        return self.jobs[str(job_id)]

    async def cancel_download(self, job_id: UUID) -> JobView:
        self._record("cancel_download", job_id)
        self._maybe_raise("cancel_download")
        return self.jobs[str(job_id)]

    async def get_batch(self, batch_id: UUID) -> BatchView:
        self._record("get_batch", batch_id)
        self._maybe_raise("get_batch")
        return self.batches[str(batch_id)]

    # -- reports + admin --
    async def submit_report(
        self,
        subject_type: str,
        subject_id: UUID,
        *,
        field: str | None = None,
        proposed_value: str | None = None,
        reason: str | None = None,
    ) -> ReportView:
        self._record(
            "submit_report",
            subject_type,
            subject_id,
            field=field,
            proposed_value=proposed_value,
            reason=reason,
        )
        self._maybe_raise("submit_report")
        assert self.report_result is not None
        return self.report_result

    async def my_reports(self) -> list[ReportView]:
        self._record("my_reports")
        self._maybe_raise("my_reports")
        return self.my_reports_list

    async def admin_reports(self, *, status: str = "pending") -> list[ReportView]:
        self._record("admin_reports", status=status)
        self._maybe_raise("admin_reports")
        return self.admin_reports_list

    async def approve_report(self, id: UUID, *, note: str | None = None) -> ReportView:
        self._record("approve_report", id, note=note)
        self._maybe_raise("approve_report")
        assert self.report_result is not None
        return self.report_result

    async def reject_report(self, id: UUID, *, note: str | None = None) -> ReportView:
        self._record("reject_report", id, note=note)
        self._maybe_raise("reject_report")
        assert self.report_result is not None
        return self.report_result

    async def admin_stats(self) -> StatsView:
        self._record("admin_stats")
        self._maybe_raise("admin_stats")
        assert self.stats_result is not None
        return self.stats_result

    async def admin_users(self, *, limit: int = 50, offset: int = 0) -> PagedUsersView:
        self._record("admin_users", limit=limit, offset=offset)
        self._maybe_raise("admin_users")
        page = self.admin_users_list[offset : offset + limit]
        return PagedUsersView(items=tuple(page), total=len(self.admin_users_list))

    # -- WebSocket --
    @asynccontextmanager
    async def progress(self) -> AsyncIterator[AsyncIterator[WsMessage]]:
        self._record("progress")

        async def _frames() -> AsyncIterator[WsMessage]:
            while True:
                frame = await self._ws_queue.get()
                if frame is None:
                    return
                yield frame

        yield _frames()


def _invalid_token_code() -> object:
    """The ``ErrorCode.INVALID_TOKEN`` value (imported lazily to keep the fake thin)."""
    from spotdl_cli._generated.api.models.error_code import ErrorCode

    return ErrorCode.INVALID_TOKEN
