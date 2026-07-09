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
    BatchRef,
    EntityHeader,
    EntityRef,
    JobRow,
    LibraryTrack,
    LyricsChoice,
    LyricsLine,
    MatchRow,
    ReportRow,
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
    PlaylistView,
    ReportView,
    TrackView,
)

# A download job always belongs to a batch; this sentinel stands in only if a WS
# frame or list row omits ``batch_id`` (defensive — should not happen in practice).
_UNBATCHED = UUID(int=0)

# A canonical track carries no single "provider" (it is provider-agnostic
# metadata; provider identity lives on a MatchRow). The field is kept on TrackRow
# per CONTRACT A but has no TrackView source, so it renders empty.
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


def track_row(track: TrackView) -> TrackRow:
    return TrackRow(
        id=UUID(track.id),
        title=track.name,
        artists=", ".join(track.artists),
        album=track.album.name if track.album is not None else "",
        duration=format_duration(track.duration_ms),
        explicit=bool(track.explicit),
        provider=_NO_PROVIDER,
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
    if album.track_count is not None:
        stats.append(("tracks", str(album.track_count)))
    if album.year is not None:
        stats.append(("year", str(album.year)))
    return EntityHeader(
        title=album.name,
        subtitle=album.album_artist or "",
        kind="album",
        stats=tuple(stats),
        cover_url=album.cover_url,
    )


def artist_header(artist: ArtistView) -> EntityHeader:
    return EntityHeader(
        title=artist.name,
        subtitle=", ".join(artist.genres),
        kind="artist",
        stats=(("tracks", str(len(artist.tracks))),),
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
    )


def library_track(job: JobView) -> LibraryTrack:
    return LibraryTrack(
        job_id=UUID(job.id),
        title=job.track_name or "",
        artists=", ".join(job.artists),
        output_path=job.output_path,
        skip_reason=job.skip_reason,
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
