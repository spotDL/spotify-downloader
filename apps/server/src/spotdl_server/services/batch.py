"""``BatchFinalizer`` — post-download batch orchestration (CONTRACT 7 + v4 order).

Runs once per batch, after its last job reaches a terminal state (the pool's
``mark_finalized`` gate guarantees exactly-once, so this class is not itself
responsible for the race). It performs the three post-processing steps **in v4
order** (``downloader.py`` 319-354):

1. **archive** — when ``update_archive``: load the library-root ``.spotdl-archive``,
   fold in each job's ``(track_url, succeeded)`` result via Plan 4
   :func:`~spotdl_core.download.post.archive_update`, and rewrite it. Rewrite (not
   append) is what makes a repeat call idempotent.
2. **m3u** — when ``generate_m3u``: one :class:`~spotdl_core.download.post.M3uEntry`
   per *completed* job, handed to Plan 4 :func:`~spotdl_core.download.post.gen_m3u_files`.
3. **save-file** — when ``generate_save_file``: :func:`build_save_file` over **all**
   jobs (failed included), dumped to the batch's ``.spotdl`` v2 target.

It **reuses** the Plan 4 batch utilities — it never re-implements m3u/archive
logic. It opens its own session (a leaf collaborator built in the app lifespan),
holds no FastAPI types, and returns a plain :class:`BatchFinalizeResult` value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from spotdl_core.download import OutputFormat
from spotdl_core.download.paths import load_archive, sanitize_string, save_archive
from spotdl_core.download.post import M3uEntry, archive_update, gen_m3u_files
from spotdl_core.model import AlbumRef, Track

from spotdl_server.db.enums import DownloadStatus
from spotdl_server.downloads.savefile import build_save_file, dump_save_file
from spotdl_server.repositories.batches import DownloadBatchRepository
from spotdl_server.repositories.entities import TrackRepository
from spotdl_server.repositories.matches import MatchRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from spotdl_server.db.models import DownloadBatch, DownloadJob
    from spotdl_server.db.models import Match as MatchModel
    from spotdl_server.db.models import Track as TrackModel
    from spotdl_server.settings import Settings

_ARCHIVE_FILENAME = ".spotdl-archive.txt"
_DEFAULT_M3U_TEMPLATE = "{list[0]}.m3u8"


@dataclass(frozen=True)
class BatchFinalizeResult:
    """What the finalizer produced — surfaced by the pool in ``batch_finished``."""

    m3u_paths: list[Path] = field(default_factory=list)
    save_file_path: Path | None = None
    counts: dict[str, int] = field(default_factory=dict)


class BatchFinalizer:
    """Archive + m3u + ``.spotdl`` v2 emission for a completed download batch."""

    def __init__(
        self, *, sessionmaker: async_sessionmaker[AsyncSession], settings: Settings
    ) -> None:
        self._sessionmaker = sessionmaker
        self._settings = settings

    async def finalize(self, batch_id: UUID) -> BatchFinalizeResult:
        """Run the batch's post-processing (idempotent; empty result if unknown)."""
        async with self._sessionmaker() as session:
            batch = await DownloadBatchRepository(session).get(batch_id)
            if batch is None:
                return BatchFinalizeResult()
            jobs = await DownloadBatchRepository(session).jobs(batch_id)
            tracks_by_id, matches_by_id = await self._load_related(session, jobs)

        library = self._settings.effective_library_path()
        output_format = OutputFormat(
            batch.output_format or self._settings.default_output_format.value
        )

        # 1) archive
        if batch.update_archive:
            self._update_archive(batch, jobs, matches_by_id, library)

        # 2) m3u
        m3u_paths: list[Path] = []
        if batch.generate_m3u:
            m3u_paths = self._write_m3u(batch, jobs, tracks_by_id, library, output_format)

        # 3) save-file
        save_file_path: Path | None = None
        if batch.generate_save_file:
            save_file_path = await self._write_save_file(
                batch_id, batch, jobs, tracks_by_id, matches_by_id, library
            )

        return BatchFinalizeResult(
            m3u_paths=m3u_paths,
            save_file_path=save_file_path,
            counts=self._counts(jobs),
        )

    # ------------------------------------------------------------ archive
    def _update_archive(
        self,
        batch: DownloadBatch,
        jobs: list[DownloadJob],
        matches_by_id: dict[UUID, MatchModel],
        library: Path,
    ) -> None:
        archive_path = library / _ARCHIVE_FILENAME
        current = load_archive(archive_path)
        results: list[tuple[str, bool]] = []
        for job in jobs:
            match = matches_by_id.get(job.match_id) if job.match_id is not None else None
            if match is None:
                continue
            succeeded = job.status is DownloadStatus.COMPLETED
            results.append((match.target_url, succeeded))
        updated = archive_update(
            current, results, add_unavailable=self._settings.download_add_unavailable
        )
        library.mkdir(parents=True, exist_ok=True)
        save_archive(archive_path, updated)

    # ------------------------------------------------------------ m3u
    def _write_m3u(
        self,
        batch: DownloadBatch,
        jobs: list[DownloadJob],
        tracks_by_id: dict[UUID, TrackModel],
        library: Path,
        output_format: OutputFormat,
    ) -> list[Path]:
        entries: list[M3uEntry] = []
        for job in jobs:
            if job.status is not DownloadStatus.COMPLETED or not job.output_path:
                continue
            track = tracks_by_id.get(job.track_id) if job.track_id is not None else None
            if track is None:
                continue
            entries.append(
                M3uEntry(
                    track=self._core_track(track),
                    path=Path(job.output_path),
                    list_name=batch.name,
                )
            )
        if not entries:
            return []

        file_name = batch.m3u_template or _DEFAULT_M3U_TEMPLATE
        template = batch.output_template or self._settings.default_output_template
        library.mkdir(parents=True, exist_ok=True)
        # Plan 4's gen_m3u_files resolves the file name relative to the CWD (and
        # its ``sanitize_string`` would strip a leading "/" from an absolute path),
        # so run it with the CWD pinned to the library root. The chdir window is
        # purely synchronous (no await), so no other coroutine interleaves.
        previous = os.getcwd()
        os.chdir(library)
        try:
            return gen_m3u_files(
                entries,
                file_name,
                template,
                output_format,
                restrict=self._settings.download_restrict,
            )
        finally:
            os.chdir(previous)

    # ------------------------------------------------------------ save-file
    async def _write_save_file(
        self,
        batch_id: UUID,
        batch: DownloadBatch,
        jobs: list[DownloadJob],
        tracks_by_id: dict[UUID, TrackModel],
        matches_by_id: dict[UUID, MatchModel],
        library: Path,
    ) -> Path:
        model = build_save_file(batch, jobs, tracks_by_id, matches_by_id)
        save_file_path = self._resolve_save_path(batch, library)
        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        save_file_path.write_text(dump_save_file(model), encoding="utf-8")
        # Persist an auto-derived path so the save-file GET endpoint (Task 9) can
        # locate it; a batch-pinned path is left as configured.
        if not batch.save_file_path:
            async with self._sessionmaker() as session:
                stored = await DownloadBatchRepository(session).get(batch_id)
                if stored is not None:
                    stored.save_file_path = str(save_file_path)
                    await session.commit()
        return save_file_path

    def _resolve_save_path(self, batch: DownloadBatch, library: Path) -> Path:
        if batch.save_file_path:
            pinned = Path(batch.save_file_path)
            return pinned if pinned.is_absolute() else library / pinned
        name = sanitize_string(batch.name) if batch.name else ""
        return library / f"{name or 'download'}.spotdl"

    # ------------------------------------------------------------ helpers
    async def _load_related(
        self, session: AsyncSession, jobs: list[DownloadJob]
    ) -> tuple[dict[UUID, TrackModel], dict[UUID, MatchModel]]:
        tracks: dict[UUID, TrackModel] = {}
        matches: dict[UUID, MatchModel] = {}
        track_repo = TrackRepository(session)
        match_repo = MatchRepository(session)
        for job in jobs:
            if job.track_id is not None and job.track_id not in tracks:
                track = await track_repo.get(job.track_id)
                if track is not None:
                    tracks[job.track_id] = track
            if job.match_id is not None and job.match_id not in matches:
                match = await match_repo.get(job.match_id)
                if match is not None:
                    matches[job.match_id] = match
        return tracks, matches

    @staticmethod
    def _core_track(track: TrackModel) -> Track:
        album = track.album
        album_ref = (
            AlbumRef(
                name=album.name,
                album_artist=album.album_artist,
                year=album.year,
                track_count=album.track_count,
                cover_url=album.cover_url,
            )
            if album is not None
            else None
        )
        artists = tuple(artist.name for artist in track.artists) or (track.name,)
        return Track(
            name=track.name,
            artists=artists,
            duration_ms=track.duration_ms,
            album=album_ref,
            isrc=track.isrc,
            explicit=track.explicit,
            track_number=track.track_number,
            disc_number=track.disc_number,
            genres=tuple(track.genres),
            year=track.year,
            popularity=track.popularity,
        )

    @staticmethod
    def _counts(jobs: list[DownloadJob]) -> dict[str, int]:
        counts = {"completed": 0, "skipped": 0, "failed": 0, "cancelled": 0}
        for job in jobs:
            if job.status is DownloadStatus.COMPLETED:
                counts["skipped" if job.skip_reason else "completed"] += 1
            elif job.status is DownloadStatus.FAILED:
                counts["failed"] += 1
            elif job.status is DownloadStatus.CANCELLED:
                counts["cancelled"] += 1
        return counts
