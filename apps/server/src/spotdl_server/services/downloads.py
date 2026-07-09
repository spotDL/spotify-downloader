"""``DownloadQueueService`` — submit (resolve + expand), list, get (Plan 7 §6.3).

The orchestration seam behind ``POST/GET /downloads`` and the batch reads. It
turns a submitted query into a **batch of N queued jobs**:

1. **Resolve** the query via :class:`~spotdl_server.services.resolve.ResolveService`
   (Plan 5, cache-first; URL / ``provider:type:id`` / free text). The
   :class:`~spotdl_server.services.dto.ResolveResult` carries the entity kind.
2. **Expand** by kind → an ordered ``(track_id, match_id)`` list + a
   :class:`~spotdl_server.db.enums.BatchKind`:
   * **track** → ``SINGLE`` (one pair; the top ``matches`` row — community-verified
     first, else best score; **no viable match ⇒ ``NoMatchFound``**). ``name=None``.
   * **album** / **playlist** → ``ALBUM`` / ``PLAYLIST``; every listed track in
     order, each carrying its top match. A track with **no** match row is still
     enqueued (``match_id=None``) so it fails visibly at the worker rather than
     being silently dropped (spec §10).
   * **artist** → out of scope ⇒ :class:`UnsupportedBatchEntity` (400).
3. **Create** the batch + N jobs (``list_position`` 1-based, creation order) and
   **commit once**. Returns the batch DTO + the ordered job ids; the router hands
   the ids to ``pool.enqueue`` and broadcasts ``job_queued`` *after* the commit.

Matching is **not** re-kicked here: resolve already persisted per-track matches
(Plan 5 kicks matching for single tracks; for album/playlist tracks this queue
reads whatever match rows exist, and a missing one becomes a fail-fast job).
Bulk pre-matching of album/playlist tracks is a documented follow-up; v1 relies
on resolve + per-job fail-visible.

Collaborators are injected (CONTRACT). No FastAPI/ORM types cross the public
boundary: inputs are the plain :class:`DownloadSubmitRequest` value object,
outputs are the ``DownloadBatchOut`` / ``DownloadJobOut`` / ``DownloadListResponse``
Pydantic DTOs the router returns verbatim (no ORM/HTTP coupling).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from spotdl_core.model import EntityType
from spotdl_core.providers import NoMatchFound

from spotdl_server.api.schemas import (
    DownloadBatchOut,
    DownloadJobOut,
    DownloadListResponse,
    DownloadSubmitRequest,
)
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.downloads.savefile import (
    SaveFileV2,
    TrackProvenance,
    build_save_file,
    pick_track_provenance,
)
from spotdl_server.repositories.merge import SOURCE_PRIORITY
from spotdl_server.repositories.snapshots import SnapshotRepository
from spotdl_server.services.dto import ResolveResult, TrackView
from spotdl_server.services.errors import NotFoundError, UnsupportedBatchEntity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession

    from spotdl_server.auth.clock import Clock
    from spotdl_server.db.models import DownloadJob, Match, Track
    from spotdl_server.repositories.batches import DownloadBatchRepository
    from spotdl_server.repositories.downloads import DownloadJobRepository
    from spotdl_server.repositories.entities import TrackRepository
    from spotdl_server.repositories.matches import MatchRepository
    from spotdl_server.services.entities import EntityService
    from spotdl_server.settings import Settings


class _Resolver(Protocol):
    """The single ``ResolveService`` method this queue depends on."""

    async def resolve(self, query: str) -> ResolveResult: ...


class DownloadQueueService:
    """Resolve + expand a submission into a queued batch; read jobs/batches back."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        resolve_service: _Resolver,
        entity_service: EntityService,
        match_repo: MatchRepository,
        track_repo: TrackRepository,
        job_repo: DownloadJobRepository,
        batch_repo: DownloadBatchRepository,
        settings: Settings,
        requested_by: UUID | None,
        clock: Clock,
    ) -> None:
        self._session = session
        self._resolve = resolve_service
        # Reserved collaborator (uniform router construction / future re-reads);
        # expansion reads the resolve views + match rows directly in v1.
        self._entities = entity_service
        self._matches = match_repo
        self._tracks = track_repo
        self._jobs = job_repo
        self._batches = batch_repo
        self._settings = settings
        self._requested_by = requested_by
        self._clock = clock

    # ------------------------------------------------------------ submit
    async def submit(self, req: DownloadSubmitRequest) -> tuple[DownloadBatchOut, list[UUID]]:
        """Resolve, expand, and enqueue ``req`` as one committed batch of jobs."""
        result = await self._resolve.resolve(req.query)
        kind, name, pairs = await self._expand(result)

        output_format = req.output_format or self._settings.default_output_format
        bitrate = req.bitrate or self._settings.default_bitrate
        output_template = req.output_template or self._settings.default_output_template

        batch = await self._batches.create(
            kind=kind,
            source=req.query,
            name=name,
            output_format=output_format.value,
            bitrate=bitrate,
            output_template=output_template,
            overwrite=req.overwrite.value if req.overwrite is not None else None,
            generate_m3u=req.generate_m3u,
            m3u_template=req.m3u_template,
            generate_save_file=req.generate_save_file,
            save_file_path=None,
            update_archive=req.update_archive,
            embed_lyrics=req.embed_lyrics,
            generate_lrc=req.generate_lrc,
            sponsor_block=req.sponsor_block,
            total_jobs=len(pairs),
            requested_by=self._requested_by,
        )

        job_ids: list[UUID] = []
        for index, (track_id, match_id) in enumerate(pairs):
            job = await self._jobs.create(
                batch_id=batch.id,
                track_id=track_id,
                match_id=match_id,
                output_format=output_format.value,
                bitrate=bitrate,
                output_template=output_template,
                list_position=index + 1,
                requested_by=self._requested_by,
            )
            job_ids.append(job.id)

        await self._session.commit()
        return await self._batch_out(batch.id), job_ids

    async def _expand(
        self, result: ResolveResult
    ) -> tuple[BatchKind, str | None, list[tuple[UUID, UUID | None]]]:
        """Map a resolve result to ``(BatchKind, batch name, (track_id, match_id)[])``."""
        entity_type = result.entity_type
        if entity_type == EntityType.TRACK.value:
            assert result.track is not None
            track_id = UUID(result.track.id)
            match = await self._top_match(track_id)
            if match is None:
                raise NoMatchFound(f"no viable audio match for track {track_id}")
            return BatchKind.SINGLE, None, [(track_id, match.id)]

        if entity_type == EntityType.ALBUM.value:
            assert result.album is not None
            return BatchKind.ALBUM, result.album.name, await self._pairs(result.album.tracks)

        if entity_type == EntityType.PLAYLIST.value:
            assert result.playlist is not None
            return (
                BatchKind.PLAYLIST,
                result.playlist.name,
                await self._pairs(result.playlist.tracks),
            )

        # artist (or any other resolvable-but-not-batchable kind)
        raise UnsupportedBatchEntity(entity_type)

    async def _pairs(self, tracks: tuple[TrackView, ...]) -> list[tuple[UUID, UUID | None]]:
        """One ``(track_id, top match id or None)`` per listed track, in order."""
        pairs: list[tuple[UUID, UUID | None]] = []
        for view in tracks:
            track_id = UUID(view.id)
            match = await self._top_match(track_id)
            pairs.append((track_id, match.id if match is not None else None))
        return pairs

    async def _top_match(self, track_id: UUID) -> Match | None:
        """The chosen audio target: community-verified first, else best score."""
        rows = await self._matches.list_for_track(track_id)
        return rows[0] if rows else None

    # ------------------------------------------------------------ reads
    async def list_jobs(
        self,
        *,
        status: DownloadStatus | None = None,
        batch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DownloadListResponse:
        jobs, total = await self._jobs.list(
            status=status, batch_id=batch_id, limit=limit, offset=offset
        )
        return DownloadListResponse(
            jobs=[await self._job_out(job) for job in jobs],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_job(self, job_id: UUID) -> DownloadJobOut:
        job = await self._jobs.get(job_id)
        if job is None:
            raise NotFoundError(entity_type="download_job", entity_id=job_id)
        return await self._job_out(job)

    async def get_batch(self, batch_id: UUID) -> DownloadBatchOut:
        batch = await self._batches.get(batch_id)
        if batch is None:
            raise NotFoundError(entity_type="download_batch", entity_id=batch_id)
        return await self._batch_out(batch_id)

    async def build_batch_save_file(self, batch_id: UUID) -> SaveFileV2:
        """Build the ``.spotdl`` v2 model for a batch (the ``save-file`` GET body).

        Read-only: loads the batch, its jobs, and the tracks/matches they
        reference, then delegates to the pure :func:`build_save_file` mapper — the
        same model the finalizer writes to disk, served on demand for
        ``spotdl save``/``sync`` (CONTRACT 7). ``NotFoundError`` if the batch is
        unknown.
        """
        batch = await self._batches.get(batch_id)
        if batch is None:
            raise NotFoundError(entity_type="download_batch", entity_id=batch_id)
        jobs = await self._batches.jobs(batch_id)
        tracks_by_id: dict[UUID, Track] = {}
        matches_by_id: dict[UUID, Match] = {}
        for job in jobs:
            if job.track_id is not None and job.track_id not in tracks_by_id:
                track = await self._tracks.get(job.track_id)
                if track is not None:
                    tracks_by_id[job.track_id] = track
            if job.match_id is not None and job.match_id not in matches_by_id:
                match = await self._matches.get(job.match_id)
                if match is not None:
                    matches_by_id[job.match_id] = match
        provenance_by_id = await _track_provenance_map(self._session, tracks_by_id)
        return build_save_file(batch, jobs, tracks_by_id, matches_by_id, provenance_by_id)

    # ------------------------------------------------------------ mapping
    async def _batch_out(self, batch_id: UUID) -> DownloadBatchOut:
        batch = await self._batches.get(batch_id)
        assert batch is not None  # only ever called with a just-created / known id
        jobs = await self._batches.jobs(batch_id)
        counts = await self._batches.counts(batch_id)
        return DownloadBatchOut(
            batch_id=batch.id,
            kind=batch.kind,
            name=batch.name,
            total_jobs=batch.total_jobs,
            counts=counts,
            finalized=batch.finalized_at is not None,
            jobs=[await self._job_out(job) for job in jobs],
        )

    async def _job_out(self, job: DownloadJob) -> DownloadJobOut:
        track_name: str | None = None
        artists: list[str] = []
        if job.track_id is not None:
            track = await self._tracks.get(job.track_id)
            if track is not None:
                track_name = track.name
                artists = [artist.name for artist in track.artists]
        return DownloadJobOut(
            id=job.id,
            batch_id=job.batch_id,
            status=job.status,
            track_id=job.track_id,
            track_name=track_name,
            artists=artists,
            output_format=job.output_format,
            bitrate=job.bitrate,
            output_template=job.output_template,
            output_path=job.output_path,
            progress=job.progress,
            skip_reason=job.skip_reason,
            error_step=job.error_step,
            error_message=job.error_message,
            list_position=job.list_position,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


async def _track_provenance_map(
    session: AsyncSession, tracks_by_id: Mapping[UUID, Any]
) -> dict[UUID, TrackProvenance]:
    """Load each track's linked snapshots and pick its save-file provenance.

    Shared by the on-demand save-file endpoint and the batch finalizer so both
    emit identical ``provider``/``provider_id``/``track_url`` fields. One
    ``list_for_entity`` query per distinct track — save files are small enough
    that this beats a bespoke join.
    """
    snapshots = SnapshotRepository(session)
    provenance: dict[UUID, TrackProvenance] = {}
    for track_id in tracks_by_id:
        linked = await snapshots.list_for_entity(EntityType.TRACK, track_id)
        picked = pick_track_provenance(linked, SOURCE_PRIORITY)
        if picked is not None:
            provenance[track_id] = picked
    return provenance
