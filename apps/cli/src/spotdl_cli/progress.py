"""Download-progress UX: consume the WS ``WsMessage`` stream, render, summarize.

Two pieces the ``download``/``sync`` commands share:

- :func:`consume_progress` — a transport-agnostic async consumer of the
  ``SpotdlClient.progress()`` stream that tallies a batch's outcome and forwards
  each event to an optional renderer. It stops once every target batch has
  emitted ``WsBatchFinished``.
- :class:`RichProgressReporter` — a Rich multi-bar renderer (one bar per active
  job plus an overall bar) driven by those events; and :func:`render_summary` /
  :func:`write_error_report` for the end-of-run failure collection (CONTRACT E:
  a batch never aborts on a per-track failure; failures are collected and listed).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from spotdl_cli._generated.ws_models import (
    WsBatchFinished,
    WsJobCancelled,
    WsJobFailed,
    WsJobFinished,
    WsJobQueued,
    WsJobStarted,
    WsMessage,
    WsProgress,
)


@dataclass(frozen=True)
class FailedJob:
    """One failed job, collected for the end-of-run summary / error report."""

    job_id: str
    track_name: str | None
    step: str | None
    error: str | None


@dataclass
class DownloadOutcome:
    """Aggregate result of consuming a download batch's progress stream."""

    completed: int = 0
    skipped: int = 0
    cancelled: int = 0
    failed_count: int = 0
    failed: list[FailedJob] = field(default_factory=list)
    m3u_paths: list[str] = field(default_factory=list)
    save_file_paths: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return self.failed_count > 0 or bool(self.failed)


async def consume_progress(
    stream: AsyncIterator[WsMessage],
    target_batches: set[str],
    *,
    on_event: Callable[[Any], None] | None = None,
) -> DownloadOutcome:
    """Drive ``stream`` until every batch in ``target_batches`` has finished.

    Returns the aggregated :class:`DownloadOutcome`. Per-batch totals come from
    the authoritative ``WsBatchFinished`` frames; per-track failure detail comes
    from the ``WsJobFailed`` frames. Frames for other batches are ignored (the WS
    fans out *all* jobs). ``on_event`` (a renderer) sees every in-scope frame.
    """
    outcome = DownloadOutcome()
    remaining = set(target_batches)
    names: dict[str, str] = {}
    # No batch ids to wait on (e.g. nothing submitted) → nothing to consume.
    if not remaining:
        return outcome

    async for message in stream:
        event = message.root
        batch_id = str(getattr(event, "batch_id", None) or "")
        if batch_id and batch_id not in target_batches:
            continue

        if on_event is not None:
            on_event(event)

        if isinstance(event, WsJobQueued) and event.track_name:
            names[str(event.job_id)] = event.track_name
        elif isinstance(event, WsJobFailed):
            outcome.failed.append(
                FailedJob(
                    job_id=str(event.job_id),
                    track_name=names.get(str(event.job_id)),
                    step=event.step,
                    error=event.error,
                )
            )
        elif isinstance(event, WsBatchFinished):
            outcome.completed += event.completed
            outcome.skipped += event.skipped
            outcome.cancelled += event.cancelled
            outcome.failed_count += event.failed
            outcome.m3u_paths.extend(event.m3u_paths)
            if event.save_file_path:
                outcome.save_file_paths.append(event.save_file_path)
            remaining.discard(str(event.batch_id))
            if not remaining:
                break

    return outcome


class RichProgressReporter:
    """A Rich multi-bar renderer: one bar per active job plus an overall bar.

    Robust to any event ordering — an event for an unknown job lazily creates its
    bar, and terminal events never raise. Use as a context manager so the live
    display starts/stops cleanly.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        self._jobs: dict[str, TaskID] = {}
        self._names: dict[str, str] = {}
        self._overall: TaskID | None = None
        self._overall_total = 0
        self._overall_done = 0

    def __enter__(self) -> RichProgressReporter:
        self._progress.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._progress.stop()

    @property
    def names(self) -> dict[str, str]:
        """job_id → track name, as learned from queued/started frames."""
        return self._names

    def _ensure_overall(self, total: int | None) -> None:
        if self._overall is None:
            self._overall_total = total or 0
            self._overall = self._progress.add_task(
                "overall", total=float(self._overall_total or 1)
            )
        elif total and total > self._overall_total:
            self._overall_total = total
            self._progress.update(self._overall, total=float(total))

    def _bar(self, job_id: str) -> TaskID:
        task = self._jobs.get(job_id)
        if task is None:
            label = self._names.get(job_id, job_id[:8])
            task = self._progress.add_task(label, total=100.0)
            self._jobs[job_id] = task
        return task

    def _finish_bar(self, job_id: str, marker: str) -> None:
        task = self._bar(job_id)
        label = self._names.get(job_id, job_id[:8])
        self._progress.update(task, completed=100.0, description=f"{marker} {label}")
        if self._overall is not None:
            self._overall_done += 1
            self._progress.update(self._overall, completed=float(self._overall_done))

    def handle(self, event: Any) -> None:
        job_id = str(getattr(event, "job_id", "") or "")
        if isinstance(event, WsJobQueued):
            if event.track_name:
                self._names[job_id] = event.track_name
            self._ensure_overall(event.list_length)
            self._bar(job_id)
        elif isinstance(event, WsJobStarted):
            self._bar(job_id)
        elif isinstance(event, WsProgress):
            task = self._bar(job_id)
            label = self._names.get(job_id, job_id[:8])
            self._progress.update(
                task, completed=event.overall * 100.0, description=f"{event.phase} {label}"
            )
        elif isinstance(event, WsJobFinished):
            self._finish_bar(job_id, "-" if event.skipped else "✓")
        elif isinstance(event, WsJobFailed):
            self._finish_bar(job_id, "✗")
        elif isinstance(event, WsJobCancelled):
            self._finish_bar(job_id, "⊘")


def render_summary(
    console: Console,
    outcome: DownloadOutcome,
    *,
    names: dict[str, str] | None = None,
    print_errors: bool = False,
) -> None:
    """Print the end-of-run summary; always list collected failures (CONTRACT E)."""
    names = names or {}
    parts = [f"[green]{outcome.completed} downloaded[/green]"]
    if outcome.skipped:
        parts.append(f"{outcome.skipped} skipped")
    if outcome.cancelled:
        parts.append(f"{outcome.cancelled} cancelled")
    failure_total = max(outcome.failed_count, len(outcome.failed))
    if failure_total:
        parts.append(f"[red]{failure_total} failed[/red]")
    console.print("Done: " + ", ".join(parts))

    for job in outcome.failed:
        name = job.track_name or names.get(job.job_id) or job.job_id
        step = f" at {job.step}" if job.step else ""
        reason = f": {job.error}" if job.error else ""
        console.print(f"  [red]✗[/red] {name}{step}{reason}", markup=True, highlight=False)

    if print_errors and not outcome.failed and failure_total:
        console.print(f"  [red]{failure_total} job(s) failed[/red] (no per-job detail received)")


def write_error_report(
    path: Path, outcome: DownloadOutcome, names: dict[str, str] | None = None
) -> None:
    """Write collected failure details to ``path`` (``--save-errors``)."""
    names = names or {}
    lines: list[str] = []
    for job in outcome.failed:
        name = job.track_name or names.get(job.job_id) or job.job_id
        step = job.step or "?"
        error = job.error or "unknown error"
        lines.append(f"{name}\tstep={step}\terror={error}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
