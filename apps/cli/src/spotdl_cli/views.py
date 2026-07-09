"""``*View`` presentation models — the stable CLI/TUI-facing contract (CONTRACT B).

These frozen dataclasses decouple the CLI and the Plan 9 TUI from the *shape* of
the generated client models: a client regeneration re-runs the ``from_generated``
mappers here, but never ripples into every command and screen. ``SpotdlClient``
is the only place that maps a generated model to a View; Plan 9's view-models
build on this layer and add no transport or client code of their own.

Every optional generated field (``Union[..., Unset]``) is normalized to a plain
``None`` / empty-list here, so consumers never import or reason about the
generator's ``UNSET`` sentinel.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TypeVar

from spotdl_cli._generated.api.models.admin_stats_response import AdminStatsResponse
from spotdl_cli._generated.api.models.admin_user_response import AdminUserResponse
from spotdl_cli._generated.api.models.album_out import AlbumOut
from spotdl_cli._generated.api.models.album_ref_out import AlbumRefOut
from spotdl_cli._generated.api.models.artist_out import ArtistOut
from spotdl_cli._generated.api.models.config_response import ConfigResponse
from spotdl_cli._generated.api.models.download_batch_out import DownloadBatchOut
from spotdl_cli._generated.api.models.download_defaults import DownloadDefaults
from spotdl_cli._generated.api.models.download_job_out import DownloadJobOut
from spotdl_cli._generated.api.models.download_list_response import DownloadListResponse
from spotdl_cli._generated.api.models.entity_envelope import EntityEnvelope
from spotdl_cli._generated.api.models.feature_flags import FeatureFlags
from spotdl_cli._generated.api.models.lyrics_out import LyricsOut
from spotdl_cli._generated.api.models.match_out import MatchOut
from spotdl_cli._generated.api.models.paged_users import PagedUsers
from spotdl_cli._generated.api.models.pat_created_response import PatCreatedResponse
from spotdl_cli._generated.api.models.playlist_out import PlaylistOut
from spotdl_cli._generated.api.models.report_response import ReportResponse
from spotdl_cli._generated.api.models.search_response import SearchResponse
from spotdl_cli._generated.api.models.token_response import TokenResponse
from spotdl_cli._generated.api.models.track_out import TrackOut
from spotdl_cli._generated.api.models.user_response import UserResponse
from spotdl_cli._generated.api.types import Unset

# Re-export the generated WebSocket frame union so the framework-free view-models
# (which must not import ``spotdl_cli._generated``, CONTRACT I) can name it through
# ``spotdl_cli.views`` — the single presentation-facing surface. The ``as X`` alias
# form marks these as intentional re-exports (ruff keeps them, no F401).
from spotdl_cli._generated.ws_models import WsBatchFinished as WsBatchFinished
from spotdl_cli._generated.ws_models import WsHello as WsHello
from spotdl_cli._generated.ws_models import WsJobCancelled as WsJobCancelled
from spotdl_cli._generated.ws_models import WsJobFailed as WsJobFailed
from spotdl_cli._generated.ws_models import WsJobFinished as WsJobFinished
from spotdl_cli._generated.ws_models import WsJobQueued as WsJobQueued
from spotdl_cli._generated.ws_models import WsJobStarted as WsJobStarted
from spotdl_cli._generated.ws_models import WsMessage as WsMessage
from spotdl_cli._generated.ws_models import WsProgress as WsProgress

_T = TypeVar("_T")


def _opt(value: _T | Unset | None) -> _T | None:
    """Collapse the generator's ``UNSET`` sentinel (and ``None``) to ``None``."""
    if isinstance(value, Unset) or value is None:
        return None
    return value


def _seq(value: Iterable[_T] | Unset | None) -> list[_T]:
    """Collapse an optional/``UNSET`` list to a concrete ``list`` (empty if absent)."""
    if isinstance(value, Unset) or value is None:
        return []
    return list(value)


@dataclass(frozen=True, slots=True)
class AlbumRefView:
    """The lightweight album reference embedded in a track."""

    id: str
    name: str
    album_artist: str | None = None
    cover_url: str | None = None
    track_count: int | None = None
    year: int | None = None

    @classmethod
    def from_generated(cls, ref: AlbumRefOut) -> AlbumRefView:
        return cls(
            id=ref.id,
            name=ref.name,
            album_artist=_opt(ref.album_artist),
            cover_url=_opt(ref.cover_url),
            track_count=_opt(ref.track_count),
            year=_opt(ref.year),
        )


@dataclass(frozen=True, slots=True)
class TrackView:
    """A canonical track (metadata only; matches/lyrics are separate resources)."""

    id: str
    name: str
    artists: list[str]
    duration_ms: int
    album: AlbumRefView | None = None
    disc_number: int | None = None
    explicit: bool | None = None
    genres: list[str] = field(default_factory=list)
    isrc: str | None = None
    popularity: int | None = None
    track_number: int | None = None
    year: int | None = None

    @classmethod
    def from_generated(cls, track: TrackOut) -> TrackView:
        album = _opt(track.album)
        return cls(
            id=track.id,
            name=track.name,
            artists=list(track.artists),
            duration_ms=track.duration_ms,
            album=AlbumRefView.from_generated(album) if isinstance(album, AlbumRefOut) else None,
            disc_number=_opt(track.disc_number),
            explicit=_opt(track.explicit),
            genres=_seq(track.genres),
            isrc=_opt(track.isrc),
            popularity=_opt(track.popularity),
            track_number=_opt(track.track_number),
            year=_opt(track.year),
        )


@dataclass(frozen=True, slots=True)
class SearchResultView:
    """``GET /search``: the ranked track list plus the ``degraded_sources`` the
    resolution layer reported for the query (a non-empty list means one or more
    metadata providers fell back — the caller surfaces a "degraded" hint)."""

    tracks: list[TrackView]
    degraded_sources: list[str] = field(default_factory=list)

    @classmethod
    def from_generated(cls, response: SearchResponse) -> SearchResultView:
        return cls(
            tracks=[TrackView.from_generated(t) for t in response.results],
            degraded_sources=list(response.degraded_sources),
        )


@dataclass(frozen=True, slots=True)
class AlbumView:
    """A full album with its track list."""

    id: str
    name: str
    album_artist: str | None = None
    cover_url: str | None = None
    track_count: int | None = None
    year: int | None = None
    tracks: list[TrackView] = field(default_factory=list)

    @classmethod
    def from_generated(cls, album: AlbumOut) -> AlbumView:
        return cls(
            id=album.id,
            name=album.name,
            album_artist=_opt(album.album_artist),
            cover_url=_opt(album.cover_url),
            track_count=_opt(album.track_count),
            year=_opt(album.year),
            tracks=[TrackView.from_generated(t) for t in _seq(album.tracks)],
        )


@dataclass(frozen=True, slots=True)
class ArtistView:
    """An artist with an optional top-track list."""

    id: str
    name: str
    genres: list[str] = field(default_factory=list)
    image_url: str | None = None
    tracks: list[TrackView] = field(default_factory=list)

    @classmethod
    def from_generated(cls, artist: ArtistOut) -> ArtistView:
        return cls(
            id=artist.id,
            name=artist.name,
            genres=_seq(artist.genres),
            image_url=_opt(artist.image_url),
            tracks=[TrackView.from_generated(t) for t in _seq(artist.tracks)],
        )


@dataclass(frozen=True, slots=True)
class PlaylistView:
    """A playlist with its track list."""

    id: str
    name: str
    cover_url: str | None = None
    description: str | None = None
    owner: str | None = None
    tracks: list[TrackView] = field(default_factory=list)

    @classmethod
    def from_generated(cls, playlist: PlaylistOut) -> PlaylistView:
        return cls(
            id=playlist.id,
            name=playlist.name,
            cover_url=_opt(playlist.cover_url),
            description=_opt(playlist.description),
            owner=_opt(playlist.owner),
            tracks=[TrackView.from_generated(t) for t in _seq(playlist.tracks)],
        )


@dataclass(frozen=True, slots=True)
class EntityView:
    """A resolved entity tagged by ``type``; exactly one payload field is set.

    Mirrors the server's ``EntityEnvelope`` plus the ``degraded_sources`` reported
    alongside a resolve, so a command can render "using degraded metadata" hints.
    """

    type: str
    track: TrackView | None = None
    album: AlbumView | None = None
    artist: ArtistView | None = None
    playlist: PlaylistView | None = None
    degraded_sources: list[str] = field(default_factory=list)

    @classmethod
    def from_generated(
        cls, envelope: EntityEnvelope, *, degraded_sources: Iterable[str] = ()
    ) -> EntityView:
        track = _opt(envelope.track)
        album = _opt(envelope.album)
        artist = _opt(envelope.artist)
        playlist = _opt(envelope.playlist)
        return cls(
            type=envelope.type_.value,
            track=TrackView.from_generated(track) if isinstance(track, TrackOut) else None,
            album=AlbumView.from_generated(album) if isinstance(album, AlbumOut) else None,
            artist=ArtistView.from_generated(artist) if isinstance(artist, ArtistOut) else None,
            playlist=PlaylistView.from_generated(playlist)
            if isinstance(playlist, PlaylistOut)
            else None,
            degraded_sources=list(degraded_sources),
        )


@dataclass(frozen=True, slots=True)
class FeatureFlagsView:
    """The per-mode feature switches surfaced by ``GET /config``."""

    auth: bool
    downloads: bool
    library: bool
    voting: bool

    @classmethod
    def from_generated(cls, flags: FeatureFlags) -> FeatureFlagsView:
        return cls(
            auth=flags.auth,
            downloads=flags.downloads,
            library=flags.library,
            voting=flags.voting,
        )


@dataclass(frozen=True, slots=True)
class DownloadDefaultsView:
    """Server-advertised download defaults (``GET /config``)."""

    add_unavailable: bool
    bitrate: str
    concurrency: int
    create_skip_file: bool
    detect_formats: list[str]
    id3_separator: str
    max_filename_length: int | None
    output_format: str
    output_template: str
    playlist_numbering: bool
    respect_skip_file: bool
    restrict: str
    retain_track_cover: bool
    scan_existing: bool
    skip_explicit: bool

    @classmethod
    def from_generated(cls, defaults: DownloadDefaults) -> DownloadDefaultsView:
        return cls(
            add_unavailable=defaults.add_unavailable,
            bitrate=defaults.bitrate,
            concurrency=defaults.concurrency,
            create_skip_file=defaults.create_skip_file,
            detect_formats=list(defaults.detect_formats),
            id3_separator=defaults.id3_separator,
            max_filename_length=defaults.max_filename_length,
            output_format=defaults.output_format,
            output_template=defaults.output_template,
            playlist_numbering=defaults.playlist_numbering,
            respect_skip_file=defaults.respect_skip_file,
            restrict=defaults.restrict,
            retain_track_cover=defaults.retain_track_cover,
            scan_existing=defaults.scan_existing,
            skip_explicit=defaults.skip_explicit,
        )


@dataclass(frozen=True, slots=True)
class ConfigView:
    """``GET /config``: deployment mode, feature flags, matcher version, defaults."""

    mode: str
    matcher_version: str
    oauth_providers: list[str]
    features: FeatureFlagsView
    download_defaults: DownloadDefaultsView | None = None

    @classmethod
    def from_generated(cls, config: ConfigResponse) -> ConfigView:
        defaults = _opt(config.download_defaults)
        return cls(
            mode=config.mode.value,
            matcher_version=config.matcher_version,
            oauth_providers=list(config.oauth_providers),
            features=FeatureFlagsView.from_generated(config.features),
            download_defaults=DownloadDefaultsView.from_generated(defaults)
            if isinstance(defaults, DownloadDefaults)
            else None,
        )


@dataclass(frozen=True, slots=True)
class MatchView:
    """A community/auto audio match for a track."""

    id: str
    status: str
    score: float
    net_score: int
    upvotes: int
    downvotes: int
    matcher_version: str
    target_provider: str
    target_id: str
    target_url: str
    candidate_name: str | None = None
    candidate_artists: list[str] = field(default_factory=list)
    candidate_duration_ms: int | None = None

    @classmethod
    def from_generated(cls, match: MatchOut) -> MatchView:
        return cls(
            id=match.id,
            status=match.status.value,
            score=match.score,
            net_score=match.net_score,
            upvotes=match.upvotes,
            downvotes=match.downvotes,
            matcher_version=match.matcher_version,
            target_provider=match.target_provider.value,
            target_id=match.target_id,
            target_url=match.target_url,
            candidate_name=_opt(match.candidate_name),
            candidate_artists=_seq(match.candidate_artists),
            candidate_duration_ms=_opt(match.candidate_duration_ms),
        )


@dataclass(frozen=True, slots=True)
class LyricsView:
    """A lyrics variant (plain or synced) for a track."""

    id: str
    kind: str
    source: str
    text: str
    upvotes: int
    downvotes: int
    net_score: int

    @classmethod
    def from_generated(cls, lyrics: LyricsOut) -> LyricsView:
        return cls(
            id=lyrics.id,
            kind=lyrics.kind.value,
            source=lyrics.source.value,
            text=lyrics.text,
            upvotes=lyrics.upvotes,
            downvotes=lyrics.downvotes,
            net_score=lyrics.net_score,
        )


@dataclass(frozen=True, slots=True)
class UserView:
    """The authenticated profile (``GET /auth/me``)."""

    id: str
    email: str
    is_admin: bool
    created_at: datetime.datetime
    display_name: str | None = None

    @classmethod
    def from_generated(cls, user: UserResponse) -> UserView:
        return cls(
            id=str(user.id),
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            display_name=_opt(user.display_name),
        )


@dataclass(frozen=True, slots=True)
class Tokens:
    """A minted session (``POST /auth/login``): access JWT + refresh + profile."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    user: UserView

    @classmethod
    def from_generated(cls, tokens: TokenResponse) -> Tokens:
        token_type = _opt(tokens.token_type)
        return cls(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
            token_type=token_type if token_type is not None else "bearer",
            user=UserView.from_generated(tokens.user),
        )


@dataclass(frozen=True, slots=True)
class PatCreated:
    """A freshly minted PAT (``POST /auth/tokens``) — includes the secret once."""

    id: str
    name: str
    token: str
    token_prefix: str
    created_at: datetime.datetime
    expires_at: datetime.datetime | None = None

    @classmethod
    def from_generated(cls, pat: PatCreatedResponse) -> PatCreated:
        return cls(
            id=str(pat.id),
            name=pat.name,
            token=pat.token,
            token_prefix=pat.token_prefix,
            created_at=pat.created_at,
            expires_at=_opt(pat.expires_at),
        )


@dataclass(frozen=True, slots=True)
class JobView:
    """A single download job's state (``GET /downloads/{id}``)."""

    id: str
    status: str
    progress: float
    track_name: str | None = None
    artists: list[str] = field(default_factory=list)
    output_path: str | None = None
    output_format: str | None = None
    output_template: str | None = None
    bitrate: str | None = None
    batch_id: str | None = None
    track_id: str | None = None
    list_position: int | None = None
    error_message: str | None = None
    error_step: str | None = None
    skip_reason: str | None = None
    created_at: datetime.datetime | None = None
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None

    @classmethod
    def from_generated(cls, job: DownloadJobOut) -> JobView:
        return cls(
            id=str(job.id),
            status=job.status.value,
            progress=job.progress,
            track_name=_opt(job.track_name),
            artists=list(job.artists),
            output_path=_opt(job.output_path),
            output_format=_opt(job.output_format),
            output_template=_opt(job.output_template),
            bitrate=_opt(job.bitrate),
            batch_id=str(_opt(job.batch_id)) if _opt(job.batch_id) is not None else None,
            track_id=str(_opt(job.track_id)) if _opt(job.track_id) is not None else None,
            list_position=_opt(job.list_position),
            error_message=_opt(job.error_message),
            error_step=_opt(job.error_step),
            skip_reason=_opt(job.skip_reason),
            created_at=job.created_at,
            started_at=_opt(job.started_at),
            finished_at=_opt(job.finished_at),
        )


@dataclass(frozen=True, slots=True)
class BatchView:
    """A download batch and its jobs (``POST /downloads`` / ``.../batches/{id}``)."""

    batch_id: str
    kind: str
    finalized: bool
    total_jobs: int
    counts: dict[str, int]
    jobs: list[JobView]
    name: str | None = None

    @classmethod
    def from_generated(cls, batch: DownloadBatchOut) -> BatchView:
        return cls(
            batch_id=str(batch.batch_id),
            kind=batch.kind.value,
            finalized=batch.finalized,
            total_jobs=batch.total_jobs,
            counts=dict(batch.counts.additional_properties),
            jobs=[JobView.from_generated(j) for j in batch.jobs],
            name=_opt(batch.name),
        )


@dataclass(frozen=True, slots=True)
class DownloadPage:
    """A page of download jobs (``GET /downloads``)."""

    jobs: list[JobView]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_generated(cls, page: DownloadListResponse) -> DownloadPage:
        return cls(
            jobs=[JobView.from_generated(j) for j in page.jobs],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


@dataclass(frozen=True, slots=True)
class DownloadSubmit:
    """A download request (input to ``submit_download``).

    A hand-written presentation-side request model that the download command
    (Task 7) builds from flags/config and ``SpotdlClient`` maps onto the generated
    ``DownloadSubmitRequest``. Kept here so the CLI never constructs generated
    models directly.
    """

    query: str
    bitrate: str | None = None
    output_format: str | None = None
    output_template: str | None = None
    overwrite: str | None = None
    embed_lyrics: bool = True
    generate_lrc: bool = False
    generate_m3u: bool = False
    m3u_template: str | None = None
    generate_save_file: bool = False
    sponsor_block: bool = False
    update_archive: bool = False


@dataclass(frozen=True, slots=True)
class ReportView:
    """A metadata-correction report (``POST /reports`` / the admin queue) — CONTRACT H.

    ``subject_type`` is the plain string value of the server's ``EntityType`` (a
    view-facing ``str``, never the generated enum). The reporter-facing response
    shape omits the reporter identity, so ``reporter`` is always ``None`` here.
    """

    id: str
    subject_type: str
    subject_id: str
    status: str
    created_at: datetime.datetime
    field: str | None = None
    proposed_value: str | None = None
    reason: str | None = None
    reporter: str | None = None

    @classmethod
    def from_generated(cls, report: ReportResponse) -> ReportView:
        return cls(
            id=str(report.id),
            subject_type=report.subject_type.value,
            subject_id=str(report.subject_id),
            status=report.status.value,
            created_at=report.created_at,
            field=_opt(report.field),
            proposed_value=_opt(report.proposed_value),
            reason=_opt(report.reason),
            reporter=None,
        )


@dataclass(frozen=True, slots=True)
class StatsView:
    """Aggregate community-health counts (``GET /admin/stats``) — CONTRACT H.

    Mirrors the server ``AdminStatsResponse`` field-for-field; the admin
    view-model projects the subset its ``StatsRow`` display type needs.
    """

    users_total: int
    matches_total: int
    community_verified_matches: int
    rejected_matches: int
    reports_total: int
    reports_pending: int
    votes_total: int

    @classmethod
    def from_generated(cls, stats: AdminStatsResponse) -> StatsView:
        return cls(
            users_total=stats.users_total,
            matches_total=stats.matches_total,
            community_verified_matches=stats.community_verified_matches,
            rejected_matches=stats.rejected_matches,
            reports_total=stats.reports_total,
            reports_pending=stats.reports_pending,
            votes_total=stats.votes_total,
        )


@dataclass(frozen=True, slots=True)
class AdminUserView:
    """One row of the admin user roster (``GET /admin/users``) — CONTRACT H."""

    id: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime.datetime
    display_name: str | None = None

    @classmethod
    def from_generated(cls, user: AdminUserResponse) -> AdminUserView:
        return cls(
            id=str(user.id),
            email=user.email,
            is_admin=user.is_admin,
            is_active=user.is_active,
            created_at=user.created_at,
            display_name=_opt(user.display_name),
        )


@dataclass(frozen=True, slots=True)
class PagedUsersView:
    """A page of admin users plus the full ``total`` for pagination (``GET /admin/users``)."""

    items: tuple[AdminUserView, ...]
    total: int

    @classmethod
    def from_generated(cls, paged: PagedUsers) -> PagedUsersView:
        return cls(
            items=tuple(AdminUserView.from_generated(user) for user in paged.items),
            total=paged.total,
        )
