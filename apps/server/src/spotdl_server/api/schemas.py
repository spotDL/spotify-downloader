"""API request/response models — the OpenAPI CONTRACT (spec §6.2).

These Pydantic models define the wire shape the Plan 8 clients are generated
against, so their field names, types, and nesting are a **contract** and must not
drift. Enum-typed fields reuse the core / server ``StrEnum`` vocabularies
(:class:`~spotdl_core.model.EntityType`, :class:`ProviderId`, :class:`MatchStatus`,
:class:`LyricsKind`) and :class:`~spotdl_server.settings.DeploymentMode` so the
generated clients get real enums, not bare strings.

The models are pure boundary shapes: they carry **no** ORM rows and **no** FastAPI
types. Each ``*Out`` model is built from a frozen service DTO
(:mod:`spotdl_server.services.dto`) via ``from_attributes`` — the single
DTO → response mapping seam. The routers only ever hand a DTO to a ``from_*``
classmethod; they never construct nested response models by hand.

**EntityEnvelope shape (documented choice).** ``POST /resolve`` and the resolve
of a dynamic ref return an entity whose type is only known at runtime, so the
envelope is a **tagged object**: a ``type`` discriminator plus one populated
optional field (``track`` / ``album`` / ``artist`` / ``playlist``) matching that
type; the other three are ``null``. This is stable and unambiguous for client
code generation (a single object type keyed by ``type``). The typed entity GETs
(``GET /tracks/{id}`` etc.) return the bare ``*Out`` model directly — their type
is fixed by the path, so no envelope is needed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from spotdl_core.download import OutputFormat, OverwriteMode
from spotdl_core.matching import MATCHER_V5_DEFAULT
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId

from spotdl_server.db.enums import BatchKind, DownloadStatus, ReportStatus, VotableType
from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
    MetadataSourceView,
    PlaylistView,
    ResolveResult,
    SearchResult,
    TrackView,
)
from spotdl_server.services.voting import VoteOutcome
from spotdl_server.settings import DeploymentMode, Settings

# --------------------------------------------------------------------------
# Requests
# --------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    """Body of ``POST /resolve``: a URL, ``provider:type:id`` ref, or free text."""

    query: str


# --------------------------------------------------------------------------
# Auth requests (spec §6.2)
# --------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Body of ``POST /auth/register``.

    ``password`` policy (argon2id, so bcrypt's 72-byte trap does not apply — the
    max only bounds hashing cost): 8–128 characters, enforced here so a weak or
    abusively long password is rejected before it reaches the service.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None


class LoginRequest(BaseModel):
    """Body of ``POST /auth/login`` (no length policy — only register enforces it)."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Body of ``POST /auth/refresh`` and ``POST /auth/logout``: the opaque token."""

    refresh_token: str


class CreatePatRequest(BaseModel):
    """Body of ``POST /auth/tokens``: mint a personal access token for the CLI.

    ``name`` is a required non-blank label (1–255 chars, matching the column
    width). ``expires_in_days`` is optional — when omitted the PAT never expires
    (``expires_at = NULL``); when given it must be a positive integer and the
    router converts it to an absolute ``expires_at`` via the shared clock.
    """

    name: str = Field(min_length=1, max_length=255)
    expires_in_days: int | None = Field(default=None, gt=0, le=3650)


# --------------------------------------------------------------------------
# Community submissions + reports (spec §6.2)
# --------------------------------------------------------------------------


class SubmitMatchRequest(BaseModel):
    """Body of ``POST /tracks/{id}/matches``: the audio-target URL to submit.

    A single non-blank URL string; core's ``parse`` validates its shape and the
    submission service enforces that it names an audio-provider *track* (a 400
    ``unsupported_url`` / ``not_an_audio_target`` otherwise).
    """

    url: str = Field(min_length=1)


class CreateReportRequest(BaseModel):
    """Body of ``POST /reports``: a metadata correction against a canonical entity.

    ``subject_type`` is a real :class:`~spotdl_core.model.EntityType` (an unknown
    value is a 422 before the service runs); ``field`` / ``proposed_value`` /
    ``reason`` are all optional (a free-form report just carries a ``reason``).
    """

    subject_type: EntityType
    subject_id: UUID
    field: str | None = Field(default=None, max_length=64)
    proposed_value: str | None = None
    reason: str | None = None


class ReportResponse(BaseModel):
    """A metadata-correction report as returned by ``POST /reports`` / ``GET /reports/me``.

    Built straight from the ``Report`` ORM row via ``from_attributes`` — the router
    hands the service's ``Report`` to :meth:`model_validate`; it never names the
    ORM type. The admin-only review fields (``reviewed_by`` / ``reviewed_at`` /
    ``review_note``) are intentionally absent from the reporter-facing shape.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_type: EntityType
    subject_id: UUID
    field: str | None = None
    proposed_value: str | None = None
    reason: str | None = None
    status: ReportStatus
    created_at: datetime


# --------------------------------------------------------------------------
# Minimal admin (spec §6.2 "Admin (minimal)")
# --------------------------------------------------------------------------


class AdminReviewRequest(BaseModel):
    """Body of ``POST /admin/reports/{id}/approve`` and ``.../reject``.

    A single optional reviewer ``note`` (audit trail); the verb (approve vs
    reject) is the route, not a mutable field, so the queue stays append-only.
    """

    note: str | None = Field(default=None, max_length=2000)


class AdminUserResponse(BaseModel):
    """A user as it appears in the admin user list (``GET /admin/users`` element).

    Built straight from the ``User`` ORM row via ``from_attributes``; the router
    never names the ORM type. Unlike the auth-facing :class:`UserResponse` this
    exposes the moderation-relevant ``is_active`` flag. The password hash is
    intentionally absent.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None = None
    is_admin: bool
    is_active: bool
    created_at: datetime


class PagedUsers(BaseModel):
    """``GET /admin/users`` body: a page of users plus the full ``total`` count."""

    items: list[AdminUserResponse]
    total: int


class PagedReports(BaseModel):
    """``GET /admin/reports`` body: a page of reports plus the in-status ``total``."""

    items: list[ReportResponse]
    total: int


class AdminStatsResponse(BaseModel):
    """``GET /admin/stats`` body: aggregate community-health counts.

    Mirrors the service's :class:`~spotdl_server.services.admin.AdminStats`
    dataclass field-for-field (built via ``from_attributes``).
    """

    model_config = ConfigDict(from_attributes=True)

    users_total: int
    matches_total: int
    community_verified_matches: int
    rejected_matches: int
    votes_total: int
    reports_pending: int
    reports_total: int


# --------------------------------------------------------------------------
# Entity response models
# --------------------------------------------------------------------------


class AlbumRefOut(BaseModel):
    """Album metadata as it appears nested inside a :class:`TrackOut`.

    An ``AlbumRef``-like shape (no track listing) plus the canonical ``id`` so a
    client can follow it to ``GET /albums/{id}``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    album_artist: str | None = None
    year: int | None = None
    track_count: int | None = None
    cover_url: str | None = None


class TrackOut(BaseModel):
    """A canonical track (metadata only; matches/lyrics are separate resources)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    artists: list[str]
    duration_ms: int
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    year: int | None = None
    genres: list[str] = []
    popularity: int | None = None
    date: str | None = None
    publisher: str | None = None
    copyright_text: str | None = None
    cover_url: str | None = None
    """Album cover thumbnail, present even on nested listing rows (``album`` dropped)."""
    provider: str | None = None
    """Source-provider ref (search previews): resolve via ``{provider}:track:{provider_id}``."""
    provider_id: str | None = None
    album: AlbumRefOut | None = None

    @classmethod
    def from_view(cls, view: TrackView) -> TrackOut:
        return cls.model_validate(view)


class AlbumOut(BaseModel):
    """A canonical album with its (metadata-only) track listing."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    album_artist: str | None = None
    year: int | None = None
    track_count: int | None = None
    cover_url: str | None = None
    label: str | None = None
    copyright_text: str | None = None
    popularity: int | None = None
    genres: list[str] = []
    # Display label only (album/single/ep/compilation) — NOT an entity type.
    album_type: str | None = None
    # Source-provider ref (search previews): resolve via ``{provider}:album:{provider_id}``.
    provider: str | None = None
    provider_id: str | None = None
    tracks: list[TrackOut] = []

    @classmethod
    def from_view(cls, view: AlbumView) -> AlbumOut:
        return cls.model_validate(view)


class ArtistOut(BaseModel):
    """A canonical artist with its (metadata-only) top tracks."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    genres: list[str] = []
    image_url: str | None = None
    popularity: int | None = None
    followers: int | None = None
    bio: str | None = None
    country: str | None = None
    # Hero-backdrop art, distinct from the ``image_url`` avatar.
    header_url: str | None = None
    # Source-provider ref (search previews): resolve via ``{provider}:artist:{provider_id}``.
    provider: str | None = None
    provider_id: str | None = None
    tracks: list[TrackOut] = []

    @classmethod
    def from_view(cls, view: ArtistView) -> ArtistOut:
        return cls.model_validate(view)


class PlaylistOut(BaseModel):
    """A canonical playlist with its ordered (metadata-only) track listing."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    owner: str | None = None
    cover_url: str | None = None
    # Source-provider ref (search previews): resolve via ``{provider}:playlist:{provider_id}``.
    provider: str | None = None
    provider_id: str | None = None
    tracks: list[TrackOut] = []

    @classmethod
    def from_view(cls, view: PlaylistView) -> PlaylistOut:
        return cls.model_validate(view)


class EntityEnvelope(BaseModel):
    """A resolved entity tagged by ``type``; exactly one payload field is set."""

    type: EntityType
    track: TrackOut | None = None
    album: AlbumOut | None = None
    artist: ArtistOut | None = None
    playlist: PlaylistOut | None = None


class ResolveResponse(BaseModel):
    """``POST /resolve`` result: the tagged entity + the sources that degraded."""

    entity: EntityEnvelope
    degraded_sources: list[str]

    @classmethod
    def from_result(cls, result: ResolveResult) -> ResolveResponse:
        envelope = EntityEnvelope(
            type=EntityType(result.entity_type),
            track=TrackOut.from_view(result.track) if result.track is not None else None,
            album=AlbumOut.from_view(result.album) if result.album is not None else None,
            artist=ArtistOut.from_view(result.artist) if result.artist is not None else None,
            playlist=(
                PlaylistOut.from_view(result.playlist) if result.playlist is not None else None
            ),
        )
        return cls(entity=envelope, degraded_sources=list(result.degraded_sources))


class SearchResponse(BaseModel):
    """``GET /search`` result: sectioned universal search + degraded sources.

    ``results`` is the ranked track list (kept as-is for existing clients);
    ``albums`` / ``artists`` / ``playlists`` are the other lightweight preview
    sections (each defaults empty). Every section carries preview views — the
    client resolves a ref for the full canonical graph.
    """

    results: list[TrackOut]
    albums: list[AlbumOut] = []
    artists: list[ArtistOut] = []
    playlists: list[PlaylistOut] = []
    degraded_sources: list[str]

    @classmethod
    def from_result(cls, result: SearchResult) -> SearchResponse:
        return cls(
            results=[TrackOut.from_view(t) for t in result.tracks],
            albums=[AlbumOut.from_view(a) for a in result.albums],
            artists=[ArtistOut.from_view(a) for a in result.artists],
            playlists=[PlaylistOut.from_view(p) for p in result.playlists],
            degraded_sources=list(result.degraded_sources),
        )


# --------------------------------------------------------------------------
# Matches + lyrics sub-resources
# --------------------------------------------------------------------------


class MatchOut(BaseModel):
    """One ranked audio target for a track (``GET /tracks/{id}/matches`` element)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    target_provider: ProviderId
    target_id: str
    target_url: str
    score: float
    matcher_version: str
    status: MatchStatus
    upvotes: int
    downvotes: int
    net_score: int
    candidate_name: str | None = None
    candidate_artists: list[str] = []
    candidate_duration_ms: int | None = None

    @classmethod
    def from_view(cls, view: MatchView) -> MatchOut:
        return cls.model_validate(view)


class MatchesResponse(BaseModel):
    """``GET /tracks/{id}/matches``: the track id + its ranked matches."""

    track_id: str
    matches: list[MatchOut]


class LyricsOut(BaseModel):
    """One lyrics variant for a track (``GET /tracks/{id}/lyrics`` element)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: ProviderId
    kind: LyricsKind
    text: str
    upvotes: int
    downvotes: int
    net_score: int

    @classmethod
    def from_view(cls, view: LyricsView) -> LyricsOut:
        return cls.model_validate(view)


class LyricsResponse(BaseModel):
    """``GET /tracks/{id}/lyrics``: the track id + its lyrics variants."""

    track_id: str
    lyrics: list[LyricsOut]


# --------------------------------------------------------------------------
# Metadata sources (spec §Phase 3 — the per-provider provenance breakdown)
# --------------------------------------------------------------------------


class MetadataSourceOut(BaseModel):
    """One provider's contribution to a canonical entity (``.../{id}/sources`` element).

    The merged canonical row still displays Spotify-first; this is the per-source
    provenance the "Metadata Sources" panel renders. Only the fields relevant to the
    entity type are populated (``followers`` for an artist, ``label``/``year`` for an
    album, ``isrc`` for a track, …); the rest stay ``null``/empty.
    """

    model_config = ConfigDict(from_attributes=True)

    provider: ProviderId
    entity_type: EntityType
    fetched_at: datetime
    name: str | None = None
    cover_url: str | None = None
    isrc: str | None = None
    popularity: int | None = None
    followers: int | None = None
    genres: list[str] = []
    label: str | None = None
    year: int | None = None
    album_name: str | None = None
    artist_names: list[str] = []

    @classmethod
    def from_view(cls, view: MetadataSourceView) -> MetadataSourceOut:
        return cls.model_validate(view)


class SourcesResponse(BaseModel):
    """``GET /{tracks|albums|artists|playlists}/{id}/sources``: the entity's provenance.

    ``sources`` lists every provider snapshot linked to the canonical entity, ordered
    Spotify-first (``SOURCE_PRIORITY``), so the UI can show which providers contributed
    which fields to the merged row.
    """

    entity_type: EntityType
    entity_id: str
    sources: list[MetadataSourceOut]


# --------------------------------------------------------------------------
# Voting (spec §6.2)
# --------------------------------------------------------------------------


class VoteRequest(BaseModel):
    """Body of the vote endpoints: ``up`` (+1), ``down`` (-1), or ``retract``.

    A closed ``Literal`` so anything else is a 422 before the service runs — the
    only three verbs the state machine accepts.
    """

    value: Literal["up", "down", "retract"]


class VoteResponse(BaseModel):
    """The vote outcome: the votable's fresh tallies, derived status, and the
    caller's own vote (``+1`` / ``-1`` / ``null`` after a retract).

    Mirrors the service's :class:`~spotdl_server.services.voting.VoteOutcome`;
    ``status`` is ``null`` for lyrics (which have no status column).
    """

    votable_type: VotableType
    votable_id: UUID
    upvotes: int
    downvotes: int
    net_score: int
    status: str | None = None
    your_vote: int | None = None

    @classmethod
    def from_outcome(cls, outcome: VoteOutcome) -> VoteResponse:
        return cls(
            votable_type=outcome.votable_type,
            votable_id=outcome.votable_id,
            upvotes=outcome.upvotes,
            downvotes=outcome.downvotes,
            net_score=outcome.net_score,
            status=outcome.status,
            your_vote=outcome.your_vote,
        )


# --------------------------------------------------------------------------
# Auth responses (spec §6.2)
# --------------------------------------------------------------------------


class UserResponse(BaseModel):
    """The authenticated profile (``GET /auth/me`` body; nested in tokens).

    Built straight from the ``User`` ORM row via ``from_attributes`` — the router
    hands the service's ``User`` to :meth:`model_validate`; it never touches ORM
    types by name. The password hash is intentionally absent.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None = None
    is_admin: bool
    created_at: datetime


class PatResponse(BaseModel):
    """A personal access token as it appears in listings (``GET /auth/tokens``).

    Built straight from the ``ApiToken`` ORM row via ``from_attributes``; the
    router never names the ORM type. The secret and its ``token_hash`` are
    intentionally absent — only the display ``token_prefix`` and metadata are
    ever listable (the full token is shown once, on create).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    token_prefix: str
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class PatCreatedResponse(BaseModel):
    """``POST /auth/tokens`` body: the newly minted PAT, **including the secret**.

    This is the only response that carries ``token`` (the full ``spdl_pat_``
    secret); it is shown exactly once and never returned again — thereafter a
    client sees only :class:`PatResponse` (prefix + metadata). The client must
    store ``token`` now (e.g. the CLI writes it to its config).
    """

    id: UUID
    name: str
    token_prefix: str
    token: str
    created_at: datetime
    expires_at: datetime | None = None


class AuthorizeUrlResponse(BaseModel):
    """``GET /auth/oauth/{provider}/authorize?json=true`` body.

    Returned to clients that open their own browser (the CLI, native apps): the
    fully-formed provider authorize URL — carrying our signed ``state`` — for the
    client to navigate to, instead of the default 307 redirect.
    """

    authorize_url: str


class TokenResponse(BaseModel):
    """A minted session: the access JWT, the rotating refresh token, and profile.

    ``token_type`` is always ``"bearer"`` and ``expires_in`` is the access
    token's remaining lifetime in seconds (``settings.access_token_ttl_seconds``),
    so a client knows when to refresh without decoding the JWT.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """``GET /health`` body."""

    status: str


class FeatureFlags(BaseModel):
    """The per-mode feature switches surfaced to clients (spec §4)."""

    downloads: bool
    auth: bool
    voting: bool
    library: bool


class DownloadDefaults(BaseModel):
    """The server's effective download configuration (``/config`` block).

    CONTRACT — read-only visibility so clients (web/TUI/Plan 8) pre-fill their
    submit forms and codegen against the server's operator defaults. Present only
    when :meth:`Settings.downloads_enabled` (``null`` in HOSTED).
    """

    output_format: str
    bitrate: str
    output_template: str
    concurrency: int
    # engine/session knobs (Plan-8 amendment) — read-only visibility for clients
    restrict: str  # RestrictMode value
    max_filename_length: int | None
    id3_separator: str
    detect_formats: list[str]
    skip_explicit: bool
    respect_skip_file: bool
    create_skip_file: bool
    playlist_numbering: bool
    retain_track_cover: bool
    add_unavailable: bool
    scan_existing: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> DownloadDefaults:
        return cls(
            output_format=settings.default_output_format.value,
            bitrate=settings.default_bitrate,
            output_template=settings.default_output_template,
            concurrency=settings.download_concurrency,
            restrict=settings.download_restrict.value,
            max_filename_length=settings.download_max_filename_length,
            id3_separator=settings.download_id3_separator,
            detect_formats=list(settings.download_detect_formats),
            skip_explicit=settings.download_skip_explicit,
            respect_skip_file=settings.download_respect_skip_file,
            create_skip_file=settings.download_create_skip_file,
            playlist_numbering=settings.download_playlist_numbering,
            retain_track_cover=settings.download_retain_track_cover,
            add_unavailable=settings.download_add_unavailable,
            scan_existing=settings.download_scan_existing,
        )


class ConfigResponse(BaseModel):
    """``GET /config`` body: deployment mode, feature flags, matcher version.

    ``oauth_providers`` lists the OAuth providers a client may offer as sign-in
    buttons (e.g. ``["github", "discord"]``); it is empty when auth is inactive or
    no provider credentials are configured. ``download_defaults`` carries the
    server's effective download configuration (``null`` when downloads are off).
    """

    mode: DeploymentMode
    features: FeatureFlags
    oauth_providers: list[str]
    matcher_version: str
    download_defaults: DownloadDefaults | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> ConfigResponse:
        """Compute the config view from ``settings`` (all values startup-fixed).

        ``downloads`` / ``library`` follow the mode (off only for HOSTED). ``auth``
        derives from :meth:`Settings.auth_active` (off in EMBEDDED / loopback mode by
        default — spec §4). ``voting`` additionally requires the voting switch, since
        voting needs accounts. ``oauth_providers`` reflects the configured provider
        credentials, but only while auth is active. ``matcher_version`` comes from
        the default scoring config.
        """
        downloads = settings.mode is not DeploymentMode.HOSTED
        auth = settings.auth_active()
        oauth_providers = (
            [provider.value for provider in settings.enabled_oauth_providers()] if auth else []
        )
        return cls(
            mode=settings.mode,
            features=FeatureFlags(
                downloads=downloads,
                library=downloads,
                auth=auth,
                voting=settings.voting_enabled and auth,
            ),
            oauth_providers=oauth_providers,
            matcher_version=MATCHER_V5_DEFAULT.matcher_version,
            download_defaults=(
                DownloadDefaults.from_settings(settings) if settings.downloads_enabled() else None
            ),
        )


# --------------------------------------------------------------------------
# Downloads — request/response (CONTRACT 4)
# --------------------------------------------------------------------------


class DownloadSubmitRequest(BaseModel):
    """Body of ``POST /downloads``: what and how to download.

    ``query`` is a URL, ``provider:type:id`` ref, or free text (a single track);
    an album/playlist URL is expanded server-side into N jobs. The ``None``
    engine fields fall back to the server's configured defaults at submit time.
    """

    query: str
    output_format: OutputFormat | None = None  # None -> settings.default_output_format
    bitrate: str | None = None  # None -> settings.default_bitrate
    output_template: str | None = None  # None -> settings.default_output_template
    overwrite: OverwriteMode | None = None  # None -> OverwriteMode.SKIP
    embed_lyrics: bool = True
    generate_lrc: bool = False
    sponsor_block: bool = False
    generate_m3u: bool = False
    m3u_template: str | None = None  # {list}/{list[0]} supported (Plan 4 post)
    generate_save_file: bool = False
    update_archive: bool = False


class DownloadJobOut(BaseModel):
    """One download job (queue row) as returned across the download surface."""

    id: UUID
    batch_id: UUID | None
    status: DownloadStatus
    track_id: UUID | None
    track_name: str | None
    artists: list[str]
    output_format: str | None
    bitrate: str | None
    output_template: str | None
    output_path: str | None
    progress: float  # 0.0-1.0
    skip_reason: str | None
    error_step: str | None
    error_message: str | None
    list_position: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class DownloadBatchOut(BaseModel):
    """A submission (batch) with its per-status tally and job listing."""

    batch_id: UUID
    kind: BatchKind
    name: str | None
    total_jobs: int
    counts: dict[str, int]  # {"queued":n,"running":n,"completed":n,"failed":n,"cancelled":n}
    finalized: bool
    jobs: list[DownloadJobOut]


class DownloadSubmitResponse(BaseModel):
    """``POST /downloads`` (201) body: the created batch + its jobs."""

    batch: DownloadBatchOut


class DownloadListResponse(BaseModel):
    """``GET /downloads`` body: a page of jobs + pagination metadata."""

    jobs: list[DownloadJobOut]
    total: int
    limit: int
    offset: int


# --------------------------------------------------------------------------
# WebSocket progress protocol (CONTRACT 3) — a single fan-out of all job events.
# Messages are Pydantic models serialized with ``model_dump_json()`` and
# discriminated on ``type``; the committed ``ws-protocol.json`` artifact exports
# this union for Plan 8 codegen.
# --------------------------------------------------------------------------

WS_PROTOCOL_VERSION = 1


class WsHello(BaseModel):
    """First frame sent to every client immediately after accept — the protocol
    version envelope. Clients reject a version they don't support."""

    model_config = ConfigDict(frozen=True)

    type: Literal["hello"] = "hello"
    protocol_version: int = WS_PROTOCOL_VERSION


class WsJobQueued(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["job_queued"] = "job_queued"
    job_id: UUID
    batch_id: UUID | None
    track_name: str | None
    list_position: int | None
    list_length: int | None


class WsJobStarted(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["job_started"] = "job_started"
    job_id: UUID
    batch_id: UUID | None


class WsProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["progress"] = "progress"
    job_id: UUID
    batch_id: UUID | None
    phase: str  # ProgressPhase value ("fetch"|"convert"|"embed"|"post"|...)
    percent: int | None  # 0-100 within the phase, when known
    overall: float  # 0.0-1.0 whole-job progress (CONTRACT 5)


class WsJobFinished(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["job_finished"] = "job_finished"
    job_id: UUID
    batch_id: UUID | None
    status: Literal["completed"]
    skipped: bool
    skip_reason: str | None
    output_path: str | None


class WsJobFailed(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["job_failed"] = "job_failed"
    job_id: UUID
    batch_id: UUID | None
    step: str | None
    error: str | None


class WsJobCancelled(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["job_cancelled"] = "job_cancelled"
    job_id: UUID
    batch_id: UUID | None


class WsBatchFinished(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["batch_finished"] = "batch_finished"
    batch_id: UUID
    completed: int
    failed: int
    skipped: int
    cancelled: int
    m3u_paths: list[str]
    save_file_path: str | None


WsMessage = Annotated[
    WsHello
    | WsJobQueued
    | WsJobStarted
    | WsProgress
    | WsJobFinished
    | WsJobFailed
    | WsJobCancelled
    | WsBatchFinished,
    Field(discriminator="type"),
]
