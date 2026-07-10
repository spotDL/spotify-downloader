"""Pure ``views.* -> viewmodels.types.*`` mappers + formatting helpers (CONTRACT A).

Shared by the search/track/collection view-models so each stays thin and under its
budget. Everything here is a plain function of ``views.*`` data — no I/O, no client,
directly unit-testable (duration formatting, score scaling, LRC parsing, header
building).
"""

from __future__ import annotations

import re
from uuid import UUID

from spotdl_cli.viewmodels.types import (
    AlbumCard,
    BatchRef,
    EntityHeader,
    EntityRef,
    JobRow,
    LibraryTrack,
    LyricsChoice,
    LyricsLine,
    MatchRow,
    ReportRow,
    SearchHit,
    SourceRow,
    TrackRow,
    UserRow,
)
from spotdl_cli.views import (
    AdminUserView,
    AlbumView,
    ArtistView,
    BatchView,
    EntityView,
    JobView,
    LyricsView,
    MatchView,
    MetadataSourceView,
    PlaylistView,
    ReportView,
    TrackView,
)

# A download job always belongs to a batch; this sentinel stands in only if a WS
# frame or list row omits ``batch_id`` (defensive — should not happen in practice).
_UNBATCHED = UUID(int=0)

# A canonical track carries no single "provider" (provider identity lives on a
# MatchRow); the TrackRow field is kept per CONTRACT A but renders empty.
_NO_PROVIDER = ""

_VERIFIED_STATUS = "community_verified"

# Leading LRC timestamp tag(s), e.g. ``[01:23.45]`` — used to read the time and to
# strip the tag off the displayed line.
_LRC_TAG = re.compile(r"\[(\d+):(\d{2})(?:[.:](\d{1,3}))?\]")
_LEADING_TAGS = re.compile(r"^(?:\[[^\]]*\])+")


def format_duration(duration_ms: int) -> str:
    """Render milliseconds as ``M:SS`` (minutes are not zero-padded)."""
    total_seconds = max(0, duration_ms) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def score_to_percent(score: float) -> int:
    """Scale a 0..1 match score to a clamped 0..100 integer gauge value."""
    return max(0, min(100, round(score * 100)))


def format_count(value: int) -> str:
    """Render a large count compactly (``1500`` → ``1.5K``, ``2_000_000`` → ``2M``)."""
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs(value) >= threshold:
            scaled = f"{value / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{scaled}{suffix}"
    return str(value)


def track_row(track: TrackView) -> TrackRow:
    return TrackRow(
        id=UUID(track.id),
        title=track.name,
        artists=", ".join(track.artists),
        album=track.album.name if track.album is not None else "",
        duration=format_duration(track.duration_ms),
        explicit=bool(track.explicit),
        provider=track.provider or _NO_PROVIDER,
        provider_id=track.provider_id or "",
    )


def match_row(match: MatchView) -> MatchRow:
    return MatchRow(
        id=UUID(match.id),
        provider=match.target_provider,
        url=match.target_url,
        score=score_to_percent(match.score),
        status=match.status,
        verified=match.status == _VERIFIED_STATUS,
        upvotes=match.upvotes,
        downvotes=match.downvotes,
        net_score=match.net_score,
    )


def _lrc_timestamp(match: re.Match[str]) -> int:
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    frac = match.group(3) or "0"
    frac_ms = int(frac.ljust(3, "0")[:3])
    return (minutes * 60 + seconds) * 1000 + frac_ms


def parse_lyrics_lines(text: str, *, synced: bool) -> tuple[LyricsLine, ...]:
    """Parse a lyrics body into lines; for synced lyrics read LRC timestamps."""
    lines: list[LyricsLine] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if synced:
            tag = _LRC_TAG.match(stripped)
            timestamp = _lrc_timestamp(tag) if tag is not None else None
            body = _LEADING_TAGS.sub("", stripped).strip()
            lines.append(LyricsLine(text=body, timestamp_ms=timestamp))
        else:
            lines.append(LyricsLine(text=stripped, timestamp_ms=None))
    return tuple(lines)


def lyrics_choice(lyrics: LyricsView) -> LyricsChoice:
    synced = lyrics.kind == "synced"
    return LyricsChoice(
        id=UUID(lyrics.id),
        source=lyrics.source,
        kind=lyrics.kind,
        synced=synced,
        net_score=lyrics.net_score,
        lines=parse_lyrics_lines(lyrics.text, synced=synced),
    )


def lyrics_choices(lyrics: list[LyricsView]) -> tuple[LyricsChoice, ...]:
    """Map + order lyrics synced-first, then by descending net score (stable)."""
    choices = [lyrics_choice(item) for item in lyrics]
    choices.sort(key=lambda choice: (0 if choice.synced else 1, -choice.net_score))
    return tuple(choices)


def track_header(track: TrackView) -> EntityHeader:
    stats: list[tuple[str, str]] = [("duration", format_duration(track.duration_ms))]
    if track.album is not None:
        stats.append(("album", track.album.name))
    if track.year is not None:
        stats.append(("year", str(track.year)))
    if track.explicit:
        stats.append(("explicit", "yes"))
    return EntityHeader(
        title=track.name,
        subtitle=", ".join(track.artists),
        kind="track",
        stats=tuple(stats),
        cover_url=track.album.cover_url if track.album is not None else None,
    )


def album_header(album: AlbumView) -> EntityHeader:
    stats: list[tuple[str, str]] = []
    if album.album_type:
        stats.append(("type", album.album_type))
    if album.track_count is not None:
        stats.append(("tracks", str(album.track_count)))
    if album.year is not None:
        stats.append(("year", str(album.year)))
    if album.label:
        stats.append(("label", album.label))
    if album.popularity is not None:
        stats.append(("popularity", str(album.popularity)))
    if album.genres:
        stats.append(("genres", ", ".join(album.genres)))
    return EntityHeader(
        title=album.name,
        subtitle=album.album_artist or "",
        kind="album",
        stats=tuple(stats),
        cover_url=album.cover_url,
    )


def artist_header(artist: ArtistView) -> EntityHeader:
    stats: list[tuple[str, str]] = []
    if artist.followers is not None:
        stats.append(("followers", format_count(artist.followers)))
    if artist.popularity is not None:
        stats.append(("popularity", str(artist.popularity)))
    stats.append(("tracks", str(len(artist.tracks))))
    return EntityHeader(
        title=artist.name,
        subtitle=", ".join(artist.genres),
        kind="artist",
        stats=tuple(stats),
        cover_url=artist.image_url,
    )


def playlist_header(playlist: PlaylistView) -> EntityHeader:
    stats: list[tuple[str, str]] = [("tracks", str(len(playlist.tracks)))]
    return EntityHeader(
        title=playlist.name,
        subtitle=playlist.owner or "",
        kind="playlist",
        stats=tuple(stats),
        cover_url=playlist.cover_url,
    )


def album_card(album: AlbumView) -> AlbumCard:
    """One discography album (an artist's ``AlbumView``) → a rendered card row."""
    return AlbumCard(
        id=str(album.id),
        title=album.name,
        album_type=album.album_type or "",
        year=_year(album.year),
        provider=album.provider or "",
        provider_id=album.provider_id or "",
    )


def _hit(
    kind: str, view: AlbumView | ArtistView | PlaylistView, subtitle: str, detail: str
) -> SearchHit:
    """Section hit: ``id`` is the row key, ``provider``/``provider_id`` resolve-on-open."""
    return SearchHit(
        kind,
        str(view.id),
        view.name,
        subtitle,
        detail,
        provider=view.provider or "",
        provider_id=view.provider_id or "",
    )


def album_hit(album: AlbumView) -> SearchHit:
    """An album preview row for the universal-search "Albums" section."""
    detail = " · ".join(p for p in (album.album_type, _year(album.year)) if p)
    return _hit("album", album, album.album_artist or "", detail)


def artist_hit(artist: ArtistView) -> SearchHit:
    """An artist preview row for the "Artists" section (followers as the detail)."""
    detail = f"{format_count(artist.followers)} followers" if artist.followers is not None else ""
    return _hit("artist", artist, ", ".join(artist.genres), detail)


def playlist_hit(playlist: PlaylistView) -> SearchHit:
    """A playlist preview row for the "Playlists" section."""
    detail = f"{len(playlist.tracks)} tracks" if playlist.tracks else ""
    return _hit("playlist", playlist, playlist.owner or "", detail)


def _year(year: int | None) -> str:
    return str(year) if year is not None else ""


def source_row(source: MetadataSourceView) -> SourceRow:
    """One provider's per-entity metadata provenance → a "Sources" panel row.

    Only the metrics relevant to the entity kind are populated on the source, so the
    chip list stays naturally sparse (followers for artists, label/year for albums, …).
    """
    metrics: list[tuple[str, str]] = []
    if source.followers is not None:
        metrics.append(("followers", format_count(source.followers)))
    if source.popularity is not None:
        metrics.append(("popularity", str(source.popularity)))
    if source.label:
        metrics.append(("label", source.label))
    if source.year is not None:
        metrics.append(("year", str(source.year)))
    if source.isrc:
        metrics.append(("isrc", source.isrc))
    if source.genres:
        metrics.append(("genres", ", ".join(source.genres)))
    name = source.name or source.album_name or ""
    return SourceRow(provider=source.provider, name=name, metrics=tuple(metrics))


def batch_ref(batch: BatchView) -> BatchRef:
    return BatchRef(batch_id=UUID(batch.batch_id), job_count=batch.total_jobs)


def job_row(job: JobView) -> JobRow:
    return JobRow(
        job_id=UUID(job.id),
        batch_id=UUID(job.batch_id) if job.batch_id else _UNBATCHED,
        title=job.track_name or "",
        phase=job.status,
        percent=max(0, min(100, round(job.progress * 100))),
        status=job.status,
        error=job.error_message,
        output_path=job.output_path,
        skip_reason=job.skip_reason,
        cover_url=job.cover_url,
        batch_name=job.batch_name,
        batch_kind=job.batch_kind,
    )


def library_track(job: JobView) -> LibraryTrack:
    return LibraryTrack(
        job_id=UUID(job.id),
        title=job.track_name or "",
        artists=", ".join(job.artists),
        output_path=job.output_path,
        skip_reason=job.skip_reason,
        cover_url=job.cover_url,
    )


def save_file_url(server_origin: str, batch_id: UUID) -> str:
    """The server URL that serves a batch's ``.spotdl`` save file (web parity)."""
    return f"{server_origin.rstrip('/')}/api/v1/downloads/batches/{batch_id}/save-file"


def report_row(report: ReportView) -> ReportRow:
    return ReportRow(
        id=UUID(report.id),
        subject_type=report.subject_type,
        subject_id=UUID(report.subject_id),
        field=report.field,
        proposed_value=report.proposed_value,
        reason=report.reason,
        status=report.status,
        reporter=report.reporter,
        created_at=report.created_at.isoformat(),
    )


def user_row(user: AdminUserView) -> UserRow:
    return UserRow(
        id=UUID(user.id),
        name=user.display_name or "—",
        email=user.email,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )


def entity_ref(entity: EntityView) -> EntityRef | None:
    """Build a router ``EntityRef`` from a resolved entity (``None`` if unpopulated)."""
    if entity.track is not None:
        return EntityRef("track", UUID(entity.track.id), entity.track.name)
    if entity.album is not None:
        return EntityRef("album", UUID(entity.album.id), entity.album.name)
    if entity.artist is not None:
        return EntityRef("artist", UUID(entity.artist.id), entity.artist.name)
    if entity.playlist is not None:
        return EntityRef("playlist", UUID(entity.playlist.id), entity.playlist.name)
    return None
