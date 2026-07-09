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
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from spotdl_core.matching import MATCHER_V5_DEFAULT
from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId

from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
    PlaylistView,
    ResolveResult,
    SearchResult,
    TrackView,
)
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
    """``GET /search`` result: a ranked track list + degraded sources."""

    results: list[TrackOut]
    degraded_sources: list[str]

    @classmethod
    def from_result(cls, result: SearchResult) -> SearchResponse:
        return cls(
            results=[TrackOut.from_view(t) for t in result.tracks],
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


class ConfigResponse(BaseModel):
    """``GET /config`` body: deployment mode, feature flags, matcher version."""

    mode: DeploymentMode
    features: FeatureFlags
    matcher_version: str

    @classmethod
    def from_settings(cls, settings: Settings) -> ConfigResponse:
        """Compute the config view from ``settings.mode`` (a startup-fixed value).

        ``downloads`` / ``library`` follow the mode (off only for HOSTED);
        ``auth`` / ``voting`` are hardcoded ``False`` until Plan 6 flips them per
        mode. ``matcher_version`` comes from the default scoring config.
        """
        downloads = settings.mode is not DeploymentMode.HOSTED
        return cls(
            mode=settings.mode,
            features=FeatureFlags(
                downloads=downloads,
                library=downloads,
                auth=False,
                voting=False,
            ),
            matcher_version=MATCHER_V5_DEFAULT.matcher_version,
        )
