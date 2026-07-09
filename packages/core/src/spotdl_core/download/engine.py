"""The single-track download engine: compose plan/fetch/convert/embed/post into
``DownloadEngine.download(request, on_progress)``.

This is the v5 replacement for v4's ~860-line ``Downloader.search_and_download``
god-method (``spotdl/download/downloader.py`` ~425-863), decomposed into the
small typed steps built in Tasks 4-8 and threaded through a frozen
:class:`DownloadContext`. The engine owns only the *composition* — output-path
planning, the skip/overwrite/archive decision branches, and per-track failure
isolation. It performs **no** queueing, batching, or concurrency: that is the
server's job (Plan 7), which calls exactly this coroutine per track.

``DownloadEngine.download(request, on_progress=None) -> DownloadOutcome`` is a
CONTRACT (spec §5.4): it never raises for a per-track failure — every
:class:`DownloadFailed` subclass is caught and returned as a ``FAILED`` outcome
tagged with its ``.step``, and any other unexpected error is reported with step
``"unknown"``. Each blocking step already offloads to ``asyncio.to_thread`` (via
the fetch/convert/embed steps), so ``download`` is safe to run under the server's
worker pool.

All external effects (yt-dlp, ffmpeg, cover HTTP, synced-lyrics, SponsorBlock)
are injected collaborators — the same seam the offline test suite fills with
fakes. Archive load/save and m3u generation are batch concerns handled by the
orchestrator around many ``download()`` calls; the engine only reads
``request.archive`` for membership and reports outcomes, never mutating the
archive file.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path

from spotdl_core.download.context import (
    DownloadConfig,
    DownloadContext,
    DownloadOutcome,
    DownloadRequest,
    OverwriteMode,
    ProgressCallback,
    ProgressEvent,
    ProgressPhase,
    SkipReason,
)
from spotdl_core.download.convert import ConvertStep
from spotdl_core.download.fetch import Fetcher, FetchStep
from spotdl_core.download.paths import build_output_path, find_duplicates, plan_skip
from spotdl_core.download.post import (
    SponsorBlock,
    SponsorBlockStep,
    SyncedLyricsSearch,
    generate_lrc,
)
from spotdl_core.download.tags import CoverDownloader, EmbedStep
from spotdl_core.providers.errors import DownloadFailed, PostProcessingFailed

__all__ = ["DownloadEngine"]

logger = logging.getLogger(__name__)


# --- null collaborators ---------------------------------------------------


class _NullCoverDownloader:
    """Cover seam used when no downloader is injected: never fetches art (all
    other tags are still embedded)."""

    def fetch(self, url: str) -> bytes | None:  # noqa: ARG002 - protocol shape
        return None


class _NullSyncedLyricsSearch:
    """Synced-lyrics seam used when none is injected: never returns lyrics. A
    request that already carries synced lyrics still gets an ``.lrc`` because
    :func:`generate_lrc` reads those directly without touching the search."""

    def search(self, query: str) -> str | None:  # noqa: ARG002 - protocol shape
        return None


# --- engine ---------------------------------------------------------------


class DownloadEngine:
    """Compose the download pipeline for a single track.

    Collaborators are injected once (construction is contract-ish so Plan 7 can
    build the engine): ``fetcher`` is required; ``cover`` / ``lyrics_search`` /
    ``sponsor_block`` are optional and default to inert null seams (or, for
    SponsorBlock, simply skip the step).
    """

    def __init__(
        self,
        config: DownloadConfig,
        *,
        fetcher: Fetcher,
        cover: CoverDownloader | None = None,
        lyrics_search: SyncedLyricsSearch | None = None,
        sponsor_block: SponsorBlock | None = None,
    ) -> None:
        self._config = config
        self._fetcher = fetcher
        self._cover: CoverDownloader = cover if cover is not None else _NullCoverDownloader()
        self._lyrics_search: SyncedLyricsSearch = (
            lyrics_search if lyrics_search is not None else _NullSyncedLyricsSearch()
        )
        self._sponsor_block = sponsor_block

    async def download(
        self,
        request: DownloadRequest,
        on_progress: ProgressCallback | None = None,
    ) -> DownloadOutcome:
        """Download exactly one track through the pipeline (CONTRACT).

        Never raises for per-track failures: a :class:`DownloadFailed` subclass is
        returned as a ``FAILED`` outcome tagged with its ``.step``; any other
        unexpected error is reported with step ``"unknown"``. A partial output
        produced by *this* run is cleaned up best-effort.
        """
        ctx = DownloadContext(request=request)
        output_path: Path | None = None
        output_existed = False

        try:
            # 1. plan -------------------------------------------------------
            output_path = self._plan_output_path(request)
            duplicates = find_duplicates(output_path, request.known_paths, request.detect_formats)
            skip_reason = plan_skip(request, output_path, duplicates)
            self._emit(on_progress, ProgressPhase.PLAN)

            if skip_reason is not None and not (
                skip_reason is SkipReason.ALREADY_EXISTS
                and request.overwrite in (OverwriteMode.FORCE, OverwriteMode.METADATA)
            ):
                self._emit(on_progress, ProgressPhase.SKIPPED)
                return DownloadOutcome.skipped(
                    request.track,
                    skip_reason,
                    path=output_path if output_path.exists() else None,
                )

            file_exists = output_path.exists() or bool(duplicates)
            output_existed = output_path.exists()

            # 2. metadata-only branch --------------------------------------
            if file_exists and request.overwrite is OverwriteMode.METADATA:
                return await self._metadata_only(request, output_path, duplicates, on_progress)

            # 3. force branch: drop duplicates before re-downloading -------
            if file_exists and request.overwrite is OverwriteMode.FORCE:
                for duplicate in duplicates:
                    with contextlib.suppress(OSError):
                        duplicate.unlink()

            # 4. ensure the destination directory exists -------------------
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 5. fetch -> convert -> (sponsorblock) -> embed -> (lrc) -------
            ctx = ctx.updated(output_path=output_path)
            ctx = await FetchStep(self._fetcher, on_progress, temp_dir=self._config.temp_dir)(ctx)
            ctx = await ConvertStep(self._config, on_progress)(ctx)

            if request.sponsor_block and self._sponsor_block is not None:
                ctx = await SponsorBlockStep(self._sponsor_block, on_progress)(ctx)

            ctx = await EmbedStep(self._cover, on_progress)(ctx)

            if request.generate_lrc:
                await self._generate_lrc(request, ctx.final_path or output_path, on_progress)

            # 6. success ---------------------------------------------------
            if request.create_skip_file:
                self._write_skip_file(output_path)

            final_path = ctx.final_path or output_path
            self._emit(on_progress, ProgressPhase.DONE, percent=100)
            return DownloadOutcome.downloaded(request.track, final_path)

        # 7. per-track failure isolation -----------------------------------
        except DownloadFailed as exc:
            self._cleanup_partial(output_path, ctx, output_existed)
            self._emit(on_progress, ProgressPhase.ERROR, message=str(exc))
            return DownloadOutcome.failed(request.track, step=exc.step, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - catch-all keeps download() total
            self._cleanup_partial(output_path, ctx, output_existed)
            self._emit(on_progress, ProgressPhase.ERROR, message=str(exc))
            return DownloadOutcome.failed(request.track, step="unknown", error=str(exc))

    # --- internals --------------------------------------------------------

    def _plan_output_path(self, request: DownloadRequest) -> Path:
        """Resolve the templated output path, tagging any failure as step ``plan``."""
        try:
            return build_output_path(request, self._config)
        except DownloadFailed:
            raise
        except Exception as exc:
            raise DownloadFailed(str(exc), step="plan") from exc

    async def _metadata_only(
        self,
        request: DownloadRequest,
        output_path: Path,
        duplicates: list[Path],
        on_progress: ProgressCallback | None,
    ) -> DownloadOutcome:
        """Re-embed metadata into the existing file without fetching/converting
        (port of v4's ``overwrite == "metadata"`` branch, simplified).

        When the planned output is absent but a same-extension duplicate exists,
        the most recent such duplicate is consolidated into ``output_path`` first.
        """
        target = output_path
        if not output_path.exists() and duplicates:
            most_recent = max(duplicates, key=lambda path: path.stat().st_mtime)
            if most_recent.suffix == output_path.suffix:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                most_recent.replace(output_path)
                target = output_path
            else:
                # Different container: embed the duplicate in place (v4 could not
                # move across extensions either).
                target = most_recent

        ctx = DownloadContext(request=request, output_path=target, final_path=target)
        ctx = await EmbedStep(self._cover, on_progress)(ctx)
        self._emit(on_progress, ProgressPhase.DONE, percent=100)
        return DownloadOutcome.downloaded(request.track, target)

    async def _generate_lrc(
        self,
        request: DownloadRequest,
        output_file: Path,
        on_progress: ProgressCallback | None,
    ) -> None:
        """Write the ``.lrc`` sidecar off-thread, tagging failures as step ``post``."""
        import asyncio

        self._emit(on_progress, ProgressPhase.POST)
        try:
            await asyncio.to_thread(generate_lrc, request, output_file, self._lyrics_search)
        except Exception as exc:  # noqa: BLE001 - normalise to the post step
            raise PostProcessingFailed(f"lrc generation failed: {exc}") from exc

    @staticmethod
    def _skip_sidecar(output_path: Path) -> Path:
        """The ``.skip`` sidecar path for ``output_path`` (matches ``plan_skip``)."""
        return Path(str(output_path.absolute()) + ".skip")

    def _write_skip_file(self, output_path: Path) -> None:
        with contextlib.suppress(OSError):
            self._skip_sidecar(output_path).write_text("", encoding="utf-8")

    @staticmethod
    def _cleanup_partial(
        output_path: Path | None, ctx: DownloadContext, output_existed: bool
    ) -> None:
        """Best-effort removal of a partial output produced by *this* run.

        A file that already existed before the run (e.g. a FORCE-overwrite target
        that failed before being replaced) is never deleted, and a file for which
        conversion already completed (``ctx.final_path`` set) is left intact — the
        audio is valid; only a later post/embed step failed.
        """
        if output_path is None or output_existed or ctx.final_path is not None:
            return
        if output_path.exists():
            with contextlib.suppress(OSError):
                output_path.unlink()

    @staticmethod
    def _emit(
        on_progress: ProgressCallback | None,
        phase: ProgressPhase,
        *,
        percent: int | None = None,
        message: str | None = None,
    ) -> None:
        """Emit a pipeline-level progress event. Best-effort: a raising callback
        must never abort a download."""
        if on_progress is None:
            return
        with contextlib.suppress(Exception):
            on_progress(ProgressEvent(phase=phase, percent=percent, message=message))
