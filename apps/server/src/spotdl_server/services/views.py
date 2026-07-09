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
    Track as TrackModel,
)
from spotdl_server.services.dto import (
    AlbumView,
    ArtistView,
    LyricsView,
    MatchView,
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
    # Only touch ``track.album`` when the caller wants it: nested listing tracks
    # (``include_album=False``) are reloaded by the album/artist/playlist repos,
    # which do NOT eager-load ``album``, so reading it here would lazy-load on
    # attribute access outside the await context (MissingGreenlet).
    album = track.album if include_album else None
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
        album=(album_meta(album) if album is not None else None),
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
        tracks=tuple(track_view(t) for t in album.tracks),
    )


def artist_view(artist: ArtistModel) -> ArtistView:
    """A full artist view with its (metadata-only) track listing."""
    return ArtistView(
        id=str(artist.id),
        name=artist.name,
        genres=tuple(artist.genres),
        image_url=artist.image_url,
        tracks=tuple(track_view(t) for t in artist.tracks),
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
