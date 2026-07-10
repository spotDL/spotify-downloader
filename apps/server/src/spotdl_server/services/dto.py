"""Service-layer DTOs — the boundary shape between services and the API layer.

These carry only primitives and nested DTOs: **no** FastAPI types and **no** ORM
rows. The service builds them from canonical ORM entities so routers never touch
a live SQLAlchemy object (the API schema layer in Task 10 maps DTO → response
model). Every DTO is a frozen dataclass — hashable, immutable, trivially
serialisable.

``degraded_sources`` (on the two top-level result DTOs, :class:`ResolveResult`
and :class:`SearchResult`) is the sorted, de-duplicated tuple of provider-id
*values* that failed during the operation — provider construction failures,
resolve failures, or audio-candidate failures. An empty tuple means everything
succeeded (spec §10 "no silent fallbacks": the client can always see what broke).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MatchView:
    """One ranked audio target for a track (the ``matches`` list element)."""

    id: str
    target_provider: str
    target_id: str
    target_url: str
    score: float
    matcher_version: str
    status: str
    upvotes: int
    downvotes: int
    net_score: int
    candidate_name: str | None = None
    candidate_artists: tuple[str, ...] = ()
    candidate_duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class LyricsView:
    """One lyrics variant for a track (per source, per kind)."""

    id: str
    source: str
    kind: str
    text: str
    upvotes: int
    downvotes: int
    net_score: int


@dataclass(frozen=True, slots=True)
class AlbumView:
    """A canonical album. ``tracks`` is populated only for a top-level album
    result; when nested inside a :class:`TrackView` it is empty (metadata only)
    to keep the graph bounded."""

    id: str
    name: str
    album_artist: str | None = None
    year: int | None = None
    track_count: int | None = None
    cover_url: str | None = None
    label: str | None = None
    copyright_text: str | None = None
    popularity: int | None = None
    genres: tuple[str, ...] = ()
    # Display label only (album/single/ep/compilation) — NOT an entity type.
    album_type: str | None = None
    tracks: tuple[TrackView, ...] = ()


@dataclass(frozen=True, slots=True)
class TrackView:
    """A canonical track with its ranked matches and lyrics.

    ``album`` is metadata-only (its own ``tracks`` empty). When a ``TrackView``
    is itself nested inside an :class:`AlbumView`/:class:`PlaylistView` listing,
    ``album`` is ``None`` to avoid a redundant parent-in-child cycle.
    """

    id: str
    name: str
    artists: tuple[str, ...]
    duration_ms: int
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    year: int | None = None
    genres: tuple[str, ...] = ()
    popularity: int | None = None
    date: str | None = None
    publisher: str | None = None
    copyright_text: str | None = None
    # Album cover thumbnail, carried even on nested listing rows (where ``album`` is
    # dropped) so a list can render the artwork without the full album sub-object.
    cover_url: str | None = None
    # Source-provider ref (search previews only): lets clients resolve a hit
    # into a canonical entity ("{provider}:track:{provider_id}").
    provider: str | None = None
    provider_id: str | None = None
    album: AlbumView | None = None
    matches: tuple[MatchView, ...] = ()
    lyrics: tuple[LyricsView, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtistView:
    """A canonical artist with (optionally) its top tracks."""

    id: str
    name: str
    genres: tuple[str, ...] = ()
    image_url: str | None = None
    popularity: int | None = None
    followers: int | None = None
    bio: str | None = None
    country: str | None = None
    # Hero-backdrop art, distinct from the ``image_url`` avatar.
    header_url: str | None = None
    tracks: tuple[TrackView, ...] = ()


@dataclass(frozen=True, slots=True)
class PlaylistView:
    """A canonical playlist with its ordered track listing."""

    id: str
    name: str
    description: str | None = None
    owner: str | None = None
    cover_url: str | None = None
    tracks: tuple[TrackView, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolveResult:
    """The output of ``ResolveService.resolve`` — exactly one entity view set,
    keyed by ``entity_type`` (an :class:`~spotdl_core.model.EntityType` value)."""

    entity_type: str
    track: TrackView | None = None
    album: AlbumView | None = None
    artist: ArtistView | None = None
    playlist: PlaylistView | None = None
    degraded_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResult:
    """The output of ``SearchService.search`` — sectioned universal search results.

    Each group is a ranked tuple of preview views (Phase 2 §universal search):
    ``tracks`` are the rich track previews (with album cover); ``albums`` /
    ``artists`` / ``playlists`` are lightweight previews built from provider search
    hits. Any group may be empty. ``degraded_sources`` is the sorted provider-id
    values that failed during the fan-out.
    """

    tracks: tuple[TrackView, ...] = field(default_factory=tuple)
    albums: tuple[AlbumView, ...] = field(default_factory=tuple)
    artists: tuple[ArtistView, ...] = field(default_factory=tuple)
    playlists: tuple[PlaylistView, ...] = field(default_factory=tuple)
    degraded_sources: tuple[str, ...] = ()
