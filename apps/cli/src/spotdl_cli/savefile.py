"""``.spotdl`` loading + v4→v2 auto-migration (Plan 8 CONTRACT G).

The typed save-file models (``SaveFileV2`` and its parts) are the server's Plan 7
models, reused here (``cli → server`` is an allowed layer) so the CLI's on-disk
``.spotdl`` shape can never drift from the server's. This module adds the
CLI-only pieces: detecting a v4 file (a bare JSON array of ``Song.asdict``) and
migrating it in memory to a ``SaveFileV2``, and a small host→provider map so the
required ``SaveFileMatch.provider`` is always populated.

Migration is in-memory only; a command that writes the result back out emits v2.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError
from spotdl_server.downloads.savefile import (
    SaveFileDownload,
    SaveFileMatch,
    SaveFileSong,
    SaveFileV2,
    dump_save_file,
)

from spotdl_cli._generated.api.models.error_code import ErrorCode
from spotdl_cli.errors import ApiError

__all__ = [
    "DEFAULT_OUTPUT_TEMPLATE",
    "dump_save_file",
    "infer_audio_provider",
    "load_save_file",
    "migrate_v4",
]

DEFAULT_OUTPUT_TEMPLATE = "{artists} - {title}.{output-ext}"
"""The config default template (CONTRACT D) synthesized for migrated v4 songs."""

_FALLBACK_PROVIDER = "youtube"
"""v4 ``download_url``s came from its audio providers (YouTube-family by default),
so any unmapped host is overwhelmingly YouTube — the pinned fallback (CONTRACT G)."""


def infer_audio_provider(url: str) -> str:
    """Map an audio-target URL's host to a v5 provider id (CONTRACT G).

    A small pure host→provider table (the CLI cannot import ``spotdl_core`` URL
    parsing, and this is display/provenance metadata only — ``sync`` re-resolves
    through the server). Unrecognized hosts fall back to ``"youtube"``.
    """
    host = (urlparse(url).hostname or "").lower()
    if host == "music.youtube.com":
        return "youtube-music"
    if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
        return "youtube"
    if host == "soundcloud.com" or host.endswith(".soundcloud.com"):
        return "soundcloud"
    if host == "bandcamp.com" or host.endswith(".bandcamp.com"):
        return "bandcamp"
    return _FALLBACK_PROVIDER


def _migrate_song(raw: dict[str, Any]) -> SaveFileSong:
    """Map one v4 ``Song.asdict`` entry to a :class:`SaveFileSong` (CONTRACT G)."""
    artists = [str(a) for a in (raw.get("artists") or [])]
    main_artist = raw.get("artist") or (artists[0] if artists else None)

    duration = raw.get("duration")
    duration_ms = round(float(duration) * 1000) if duration is not None else 0

    download_url = raw.get("download_url")
    match: SaveFileMatch | None = None
    if download_url:
        match = SaveFileMatch(
            provider=infer_audio_provider(str(download_url)),
            provider_id=str(raw.get("song_id") or ""),
            url=str(download_url),
            verified=False,
        )

    download = SaveFileDownload(
        output_format=str(raw.get("output_format") or "mp3"),
        bitrate="auto",
        output_template=DEFAULT_OUTPUT_TEMPLATE,
        status="queued",
    )

    return SaveFileSong(
        name=str(raw.get("name") or ""),
        artists=artists,
        artist=main_artist,
        album_name=raw.get("album_name"),
        album_artist=raw.get("album_artist"),
        duration_ms=duration_ms,
        isrc=raw.get("isrc"),
        explicit=raw.get("explicit"),
        track_number=raw.get("track_number"),
        disc_number=raw.get("disc_number"),
        disc_count=raw.get("disc_count"),
        track_count=raw.get("track_count"),
        year=raw.get("year"),
        date=raw.get("date"),
        genres=[str(g) for g in (raw.get("genres") or [])],
        publisher=raw.get("publisher"),
        copyright_text=raw.get("copyright"),
        popularity=raw.get("popularity"),
        cover_url=raw.get("cover_url"),
        track_url=raw.get("url"),
        provider=None,
        provider_id=None,
        list_name=raw.get("list_name"),
        list_position=raw.get("list_position"),
        list_length=raw.get("list_length"),
        match=match,
        download=download,
    )


def _infer_kind(songs: list[SaveFileSong]) -> str:
    """Infer the batch ``kind`` from the migrated songs (CONTRACT G)."""
    if any(s.list_name for s in songs):
        return "playlist"
    albums = {s.album_name for s in songs if s.album_name}
    if albums and len(albums) == 1 and all(s.album_name for s in songs):
        return "album"
    return "single"


def _inferred_name(songs: list[SaveFileSong]) -> str | None:
    for song in songs:
        if song.list_name:
            return song.list_name
    for song in songs:
        if song.album_name:
            return song.album_name
    return None


def migrate_v4(raw_songs: list[Any], *, created_at: str) -> SaveFileV2:
    """Build a :class:`SaveFileV2` from a v4 bare array of song dicts (CONTRACT G)."""
    songs = [_migrate_song(dict(entry)) for entry in raw_songs]
    return SaveFileV2(
        version=2,
        kind=_infer_kind(songs),
        name=_inferred_name(songs),
        source=None,
        created_at=created_at,
        matcher_version=None,
        songs=songs,
    )


def load_save_file(path: Path | str) -> SaveFileV2:
    """Load a ``.spotdl`` file, migrating a v4 array to :class:`SaveFileV2` in memory.

    Detection is by top-level JSON type: a **list** is v4 (a bare array of
    ``Song.asdict``); an **object with ``version == 2``** is v5 and parses
    directly; anything else raises ``ApiError(validation_error)``.
    """
    file_path = Path(path)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ApiError(ErrorCode.VALIDATION_ERROR, f"unrecognized .spotdl file: {exc}") from exc

    if isinstance(data, list):
        mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime, tz=datetime.UTC)
        return migrate_v4(data, created_at=mtime.isoformat())

    if isinstance(data, dict) and data.get("version") == 2:
        try:
            return SaveFileV2.model_validate(data)
        except ValidationError as exc:
            raise ApiError(ErrorCode.VALIDATION_ERROR, f"unrecognized .spotdl file: {exc}") from exc

    raise ApiError(ErrorCode.VALIDATION_ERROR, "unrecognized .spotdl file")
