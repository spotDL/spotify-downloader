"""Canonical ORM row → service DTO mapping (the single mapping seam).

Pure, synchronous functions that translate a persisted SQLAlchemy row into the
frozen service DTOs in :mod:`spotdl_server.services.dto`. They are shared by
:class:`~spotdl_server.services.resolve.ResolveService` (write-then-read) and
:class:`~spotdl_server.services.entities.EntityService` (read-only) so the two
never drift on the ORM → DTO shape.

**No I/O.** Every relation these functions read (``track.artists``, ``track.album``,
``album.tracks`` …) is eager-loaded (``lazy="selectin"`` on the models), so no
lazy load fires from inside a function here — callers pass ``matches`` / ``lyrics``
in explicitly (fetched via their repositories in the async context) rather than
off the ORM relationship, keeping the async boundary at the service layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from spotdl_server.db.models import (
    Album as AlbumModel,
)
from spotdl_server.db.models import (
    Artist as ArtistModel,
)
from spotdl_server.db.models import (
    Lyrics as LyricsModel,
)
from spotdl_server.db.models import (
    Match as MatchModel,
)
from spotdl_server.db.models import (
    Playlist as PlaylistModel,
)
from spotdl_server.db.models import (
    ProviderSnapshot,
)
from spotdl_server.db.models import (
    Track as TrackModel,
)
from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
    MetadataSourceView,
    PlaylistView,
    TrackView,
)


def match_view(row: MatchModel) -> MatchView:
    return MatchView(
        id=str(row.id),
        target_provider=row.target_provider.value,
        target_id=row.target_id,
        target_url=row.target_url,
        score=row.score,
        matcher_version=row.matcher_version,
        status=row.status.value,
        upvotes=row.upvotes,
        downvotes=row.downvotes,
        net_score=row.net_score,
        candidate_name=row.candidate_name,
        candidate_artists=tuple(row.candidate_artists or ()),
        candidate_duration_ms=row.candidate_duration_ms,
    )


def lyrics_view(row: LyricsModel) -> LyricsView:
    return LyricsView(
        id=str(row.id),
        source=row.source.value,
        kind=row.kind.value,
        text=row.text,
        upvotes=row.upvotes,
        downvotes=row.downvotes,
        net_score=row.net_score,
    )


def album_meta(album: AlbumModel) -> AlbumView:
    """An album's metadata only — its ``tracks`` deliberately left empty.

    Used when an album appears nested inside a :class:`TrackView` (avoids pulling
    the whole album track listing into every track view).
    """
    return AlbumView(
        id=str(album.id),
        name=album.name,
        album_artist=album.album_artist,
        year=album.year,
        track_count=album.track_count,
        cover_url=album.cover_url,
        label=album.label,
        copyright_text=album.copyright_text,
        popularity=album.popularity,
        genres=tuple(album.genres),
        album_type=album.album_type,
        provider=album.provider.value if album.provider is not None else None,
        provider_id=album.provider_id,
    )


def track_view(
    track: TrackModel,
    *,
    matches: Sequence[MatchModel] = (),
    lyrics: Sequence[LyricsModel] = (),
    include_album: bool = False,
) -> TrackView:
    """Map a canonical track row to a :class:`TrackView`.

    ``matches`` / ``lyrics`` are supplied by the caller (fetched via their
    repositories) rather than read off the ORM relationship, so no lazy load
    fires here. Nested listing tracks omit both and the album to keep the graph
    bounded (``include_album=False``).
    """
    # ``track.album`` is eager-loaded on every path that builds a ``TrackView``
    # (model-level selectin for a direct track get; the explicit track→album chain
    # in the album/artist/playlist repos), so reading it here never lazy-loads. The
    # full album sub-object is attached only when the caller asks (``include_album``);
    # the cover thumbnail is always carried so nested listing rows can render artwork.
    album = track.album
    cover_url = album.cover_url if album is not None else None
    return TrackView(
        id=str(track.id),
        name=track.name,
        artists=tuple(a.name for a in track.artists),
        duration_ms=track.duration_ms,
        isrc=track.isrc,
        explicit=track.explicit,
        track_number=track.track_number,
        disc_number=track.disc_number,
        year=track.year,
        genres=tuple(track.genres),
        popularity=track.popularity,
        date=track.date,
        publisher=track.publisher,
        copyright_text=track.copyright_text,
        cover_url=cover_url,
        album=(album_meta(album) if include_album and album is not None else None),
        matches=tuple(match_view(m) for m in matches),
        lyrics=tuple(lyrics_view(row) for row in lyrics),
    )


def album_view(album: AlbumModel) -> AlbumView:
    """A full album view with its (metadata-only) track listing."""
    return AlbumView(
        id=str(album.id),
        name=album.name,
        album_artist=album.album_artist,
        year=album.year,
        track_count=album.track_count,
        cover_url=album.cover_url,
        label=album.label,
        copyright_text=album.copyright_text,
        popularity=album.popularity,
        genres=tuple(album.genres),
        album_type=album.album_type,
        provider=album.provider.value if album.provider is not None else None,
        provider_id=album.provider_id,
        tracks=tuple(track_view(t) for t in album.tracks),
    )


def artist_view(artist: ArtistModel) -> ArtistView:
    """A full artist view with its (metadata-only) track listing + discography."""
    return ArtistView(
        id=str(artist.id),
        name=artist.name,
        genres=tuple(artist.genres),
        image_url=artist.image_url,
        popularity=artist.popularity,
        followers=artist.followers,
        bio=artist.bio,
        country=artist.country,
        header_url=artist.header_url,
        tracks=tuple(track_view(t) for t in artist.tracks),
        # ``album_meta`` (no nested track listing) — the discography grid needs only
        # cover/name/year/album_type + the source ref for resolve-on-open.
        albums=tuple(album_meta(a) for a in artist.albums),
    )


def _payload_of(snapshot: ProviderSnapshot) -> dict[str, Any]:
    payload = snapshot.raw_payload
    return payload if isinstance(payload, dict) else {}


def _int_field(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _str_field(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def metadata_source_view(snapshot: ProviderSnapshot) -> MetadataSourceView:
    """Map one entity-linked provider snapshot to a per-source provenance view.

    Reads the fast-query normalized columns first, then the ``raw_payload`` for the
    notable metadata a source contributed (mirrors the accessor convention the
    :class:`~spotdl_server.repositories.merge.CanonicalMerger` uses, but only for
    display — this never influences the merge). Fields irrelevant to the snapshot's
    entity type simply stay ``None`` / empty.
    """
    payload = _payload_of(snapshot)
    genres = payload.get("genres")
    return MetadataSourceView(
        provider=snapshot.provider.value,
        provider_entity_id=snapshot.provider_entity_id,
        entity_type=snapshot.entity_type.value,
        fetched_at=snapshot.fetched_at,
        name=snapshot.name or _str_field(payload, "name"),
        cover_url=snapshot.art_url
        or _str_field(payload, "cover_url")
        or _str_field(payload, "image_url"),
        isrc=snapshot.isrc or _str_field(payload, "isrc"),
        popularity=_int_field(payload, "popularity"),
        followers=_int_field(payload, "followers"),
        listeners=_int_field(payload, "listeners"),
        playcount=_int_field(payload, "playcount"),
        genres=tuple(genres) if isinstance(genres, list) else (),
        label=_str_field(payload, "label"),
        year=_int_field(payload, "year"),
        album_name=snapshot.album_name,
        artist_names=tuple(snapshot.artist_names or ()),
    )


def playlist_view(playlist: PlaylistModel) -> PlaylistView:
    """A full playlist view with its ordered (metadata-only) track listing."""
    return PlaylistView(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        owner=playlist.owner,
        cover_url=playlist.cover_url,
        tracks=tuple(track_view(t) for t in playlist.tracks),
    )
