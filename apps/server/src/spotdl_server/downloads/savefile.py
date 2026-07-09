"""``.spotdl`` v2 save-file model + (de)serialization (CONTRACT 7).

v4's ``.spotdl`` was a bare array of ``Song.asdict``; v5 wraps it in a versioned,
self-describing JSON object so Plan 8's ``spotdl sync`` can auto-migrate v4 files
and re-resolve/re-download from a stable schema. One entry per job in the batch
(including failed jobs — mirrors v4, which serialized every result).

This module owns the model + the pure mapper signature; the full
``build_save_file`` field-by-field mapping is exercised by the ``BatchFinalizer``
in Task 7. It imports only value types (Pydantic + the ``DownloadStatus``/
``BatchKind`` enums via plain strings) — no FastAPI, no ORM in its public surface.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel

SAVE_FILE_VERSION = 2


class SaveFileMatch(BaseModel):
    """The chosen audio target (from the ``matches`` row / ``DownloadRequest.candidate``)."""

    provider: str  # ProviderId value
    provider_id: str
    url: str  # playable target url (candidate.url / matches.target_url)
    name: str | None = None
    artists: list[str] = []
    duration_ms: int | None = None
    isrc: str | None = None
    verified: bool = False
    score: float | None = None
    matcher_version: str | None = None


class SaveFileDownload(BaseModel):
    """What the queue decided/produced for one job."""

    output_format: str
    bitrate: str
    output_template: str
    output_path: str | None = None
    status: str  # DownloadStatus value: completed|failed|cancelled|queued|running
    skip_reason: str | None = None
    error_step: str | None = None


class SaveFileSong(BaseModel):
    """Full track metadata (v5 ``Track`` + list context) + its match + download."""

    name: str
    artists: list[str]
    artist: str | None = None  # main artist
    album_name: str | None = None
    album_artist: str | None = None
    duration_ms: int
    isrc: str | None = None
    explicit: bool | None = None
    track_number: int | None = None
    disc_number: int | None = None
    disc_count: int | None = None
    track_count: int | None = None
    year: int | None = None
    date: str | None = None
    genres: list[str] = []
    publisher: str | None = None
    copyright_text: str | None = None
    popularity: int | None = None
    cover_url: str | None = None
    track_url: str | None = None  # canonical entity url (WOAS)
    provider: str | None = None  # source metadata provider
    provider_id: str | None = None
    list_name: str | None = None
    list_position: int | None = None
    list_length: int | None = None
    match: SaveFileMatch | None = None
    download: SaveFileDownload


class SaveFileV2(BaseModel):
    """The versioned save-file envelope written / served as ``.spotdl`` v2."""

    version: int = SAVE_FILE_VERSION  # == 2
    kind: str  # BatchKind value
    name: str | None = None  # playlist/album name
    source: str | None = None  # submitted url/query
    created_at: str  # ISO 8601 (batch.created_at)
    matcher_version: str | None = None
    songs: list[SaveFileSong]


def _iso(value: Any) -> str:
    """Render a datetime (or already-string) as an ISO-8601 string."""
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _provider_value(value: Any) -> str | None:
    """Render a ``ProviderId`` (or plain string) as its string value, or ``None``."""
    if value is None:
        return None
    return getattr(value, "value", None) or str(value)


def _status_value(value: Any) -> str:
    """Render a ``DownloadStatus`` / ``BatchKind`` (StrEnum) as its plain value."""
    if value is None:
        return ""
    return getattr(value, "value", None) or str(value)


def _save_match(match: Any) -> SaveFileMatch | None:
    """Map a ``matches`` row onto the save-file's chosen audio target."""
    if match is None:
        return None
    verified = _status_value(getattr(match, "status", None)) == "community_verified"
    return SaveFileMatch(
        provider=_provider_value(getattr(match, "target_provider", None)) or "",
        provider_id=str(getattr(match, "target_id", "") or ""),
        url=str(getattr(match, "target_url", "") or ""),
        name=getattr(match, "candidate_name", None),
        artists=list(getattr(match, "candidate_artists", None) or []),
        duration_ms=getattr(match, "candidate_duration_ms", None),
        verified=verified,
        score=getattr(match, "score", None),
        matcher_version=getattr(match, "matcher_version", None),
    )


def build_save_file(
    batch: Any,
    jobs: Sequence[Any],
    tracks_by_id: Mapping[UUID, Any],
    matches_by_id: Mapping[UUID, Any],
) -> SaveFileV2:
    """Map a batch + its jobs (with resolved tracks/matches) to a :class:`SaveFileV2`.

    Pure mapper — no I/O. One :class:`SaveFileSong` per job, in the jobs' given
    order, so a failed job still appears (v4 parity). Populates the full track
    metadata available on the canonical rows, the chosen ``match`` provenance, and
    the ``download`` settings/result. DB-unbacked optional tags (``date`` /
    ``publisher`` / ``copyright_text`` / ``cover_url``) serialize as ``null`` — an
    additive-safe, documented limitation of the v5 canonical ``tracks`` table.
    """
    songs: list[SaveFileSong] = []
    matcher_version: str | None = None
    for job in jobs:
        track_id: Any = getattr(job, "track_id", None)
        match_id: Any = getattr(job, "match_id", None)
        track = tracks_by_id.get(track_id) if track_id is not None else None
        match = matches_by_id.get(match_id) if match_id is not None else None

        download = SaveFileDownload(
            output_format=getattr(job, "output_format", None) or "",
            bitrate=getattr(job, "bitrate", None) or "",
            output_template=getattr(job, "output_template", None) or "",
            output_path=getattr(job, "output_path", None),
            status=_status_value(getattr(job, "status", None)),
            skip_reason=getattr(job, "skip_reason", None),
            error_step=getattr(job, "error_step", None),
        )

        artists: list[str] = []
        name = ""
        duration_ms = 0
        album = None
        if track is not None:
            artists = [str(a.name) for a in getattr(track, "artists", [])]
            name = str(getattr(track, "name", "") or "")
            duration_ms = int(getattr(track, "duration_ms", 0) or 0)
            album = getattr(track, "album", None)

        save_match = _save_match(match)
        if matcher_version is None and save_match is not None:
            matcher_version = save_match.matcher_version

        songs.append(
            SaveFileSong(
                name=name,
                artists=artists,
                artist=artists[0] if artists else None,
                album_name=getattr(album, "name", None) if album is not None else None,
                album_artist=getattr(album, "album_artist", None) if album is not None else None,
                duration_ms=duration_ms,
                isrc=getattr(track, "isrc", None) if track is not None else None,
                explicit=getattr(track, "explicit", None) if track is not None else None,
                track_number=getattr(track, "track_number", None) if track is not None else None,
                disc_number=getattr(track, "disc_number", None) if track is not None else None,
                track_count=getattr(album, "track_count", None) if album is not None else None,
                year=getattr(track, "year", None) if track is not None else None,
                genres=list(getattr(track, "genres", []) or []) if track is not None else [],
                popularity=getattr(track, "popularity", None) if track is not None else None,
                provider=(
                    _provider_value(getattr(track, "provider", None)) if track is not None else None
                ),
                list_name=getattr(batch, "name", None),
                list_position=getattr(job, "list_position", None),
                list_length=getattr(batch, "total_jobs", None),
                match=save_match,
                download=download,
            )
        )

    return SaveFileV2(
        kind=_status_value(getattr(batch, "kind", None)),
        name=getattr(batch, "name", None),
        source=getattr(batch, "source", None),
        created_at=_iso(getattr(batch, "created_at", None)),
        matcher_version=matcher_version,
        songs=songs,
    )


def dump_save_file(model: SaveFileV2) -> str:
    """Serialize to deterministic ``.spotdl`` v2 JSON text (stable indent + newline)."""
    return json.dumps(model.model_dump(), indent=2, ensure_ascii=False) + "\n"
