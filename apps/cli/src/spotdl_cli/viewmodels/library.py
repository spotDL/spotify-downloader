"""``LibraryViewModel`` — completed downloads, grouped by batch (CONTRACT A).

The library is the *completed*-jobs view: it lists ``list_downloads(status="completed")``
and groups the rows by submission batch (web parity: ``apps/web/src/routes/library.tsx``).
Each group exposes its tracks' local output paths and the batch's ``.spotdl`` save-file
URL, built from the server origin exactly like the web client's ``batchSaveFileUrl``.
The screen renders the grouping and never fetches or computes anything itself.
"""

from __future__ import annotations

from uuid import UUID

from spotdl_cli.viewmodels.base import Loadable, guard
from spotdl_cli.viewmodels.mappers import library_track, save_file_url
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol
from spotdl_cli.viewmodels.types import LibraryBatch
from spotdl_cli.views import JobView

# The page size mirrors the web library view (``useDownloads({ limit: 100 })``).
_PAGE_LIMIT = 100


class LibraryViewModel:
    def __init__(self, client: SpotdlClientProtocol, *, server_origin: str) -> None:
        self._client = client
        self._server_origin = server_origin

    async def load(self) -> Loadable[tuple[LibraryBatch, ...]]:
        """Load completed downloads and group them into per-batch sections."""

        async def _run() -> tuple[LibraryBatch, ...]:
            page = await self._client.list_downloads(status="completed", limit=_PAGE_LIMIT)
            return self._group(page.jobs)

        return await guard(_run())

    def _group(self, jobs: list[JobView]) -> tuple[LibraryBatch, ...]:
        """Group jobs by batch id, preserving first-seen order (like the web view)."""
        order: list[str | None] = []
        grouped: dict[str | None, list[JobView]] = {}
        for job in jobs:
            key = job.batch_id
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(job)
        return tuple(self._batch(key, grouped[key]) for key in order)

    def _batch(self, batch_id: str | None, jobs: list[JobView]) -> LibraryBatch:
        parsed = UUID(batch_id) if batch_id is not None else None
        url = save_file_url(self._server_origin, parsed) if parsed is not None else None
        # The batch name/kind are denormalized onto every job; take the first
        # non-empty so a batch the server left unnamed still falls back cleanly.
        name = next((job.batch_name for job in jobs if job.batch_name), None)
        kind = next((job.batch_kind for job in jobs if job.batch_kind), None)
        tracks = tuple(library_track(job) for job in jobs)
        return LibraryBatch(batch_id=parsed, save_file_url=url, tracks=tracks, name=name, kind=kind)
