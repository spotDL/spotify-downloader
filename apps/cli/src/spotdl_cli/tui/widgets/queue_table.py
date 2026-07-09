"""``QueueTable`` — a DataTable of download jobs, grouped by batch (§4, CONTRACT D).

Renders a :class:`QueueSnapshot`: jobs are grouped by their submission batch, each
group introduced by a subtle header row (``▸ Batch <id> · N tracks``); every job row
carries a status glyph, its title, a progress-bar cell, and a step cell (the current
phase, or the failure/skip reason, or the output path once done). Job rows are keyed
by job id so live WS updates rewrite a row in place; the group structure is rebuilt
only when a new batch/job appears. The widget holds no logic beyond formatting — the
screen owns the snapshot and drives every update.
"""

from __future__ import annotations

from collections.abc import Iterable

from rich.text import Text
from textual.coordinate import Coordinate
from textual.widgets import DataTable

from spotdl_cli.viewmodels.types import JobRow, QueueSnapshot

_BAR_WIDTH = 12
_DONE = frozenset({"completed", "skipped"})
_BAD = frozenset({"failed", "cancelled"})
_GLYPH = {"completed": "✓", "skipped": "»", "failed": "✗", "cancelled": "⊘", "running": "▸"}


class QueueTable(DataTable[Text]):
    """A framework-dumb table bound to the queue snapshot, grouped by batch."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._order: list[str] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("St", "Title", "Progress", "Step")

    def update_snapshot(self, snapshot: QueueSnapshot) -> None:
        """Rebuild on a structural change (new batch/job); else rewrite cells in place."""
        desired = _grouped_keys(snapshot)
        if desired != self._order:
            self._rebuild(snapshot, desired)
        else:
            for job in snapshot.jobs:
                self._update_job(job)

    @property
    def job_row_count(self) -> int:
        """The number of job rows (excludes the batch group-header rows)."""
        return sum(1 for key in self._order if not key.startswith("batch:"))

    def _rebuild(self, snapshot: QueueSnapshot, desired: list[str]) -> None:
        previous = self._current_row_key()
        self.clear()
        for batch_id, group in _groups(snapshot.jobs):
            self.add_row(*_header_cells(batch_id, group), key=f"batch:{batch_id}")
            for job in group:
                self.add_row(*_cells(job), key=str(job.job_id))
        self._order = desired
        self._restore_cursor(previous, desired)

    def _update_job(self, job: JobRow) -> None:
        key = str(job.job_id)
        for column, value in zip(self.columns, _cells(job), strict=True):
            self.update_cell(key, column, value)

    def _current_row_key(self) -> str | None:
        if not self._order or not 0 <= self.cursor_row < self.row_count:
            return None
        return self.coordinate_to_cell_key(Coordinate(self.cursor_row, 0)).row_key.value

    def _restore_cursor(self, previous: str | None, desired: list[str]) -> None:
        """Keep the selection stable across a rebuild; land on a job row, not a header."""
        target = previous if previous in desired else None
        if target is None:
            target = next((key for key in desired if not key.startswith("batch:")), None)
        if target is not None:
            self.move_cursor(row=self.get_row_index(target))


def _groups(jobs: Iterable[JobRow]) -> list[tuple[str, list[JobRow]]]:
    """Bucket jobs by batch id, preserving first-seen order."""
    order: list[str] = []
    buckets: dict[str, list[JobRow]] = {}
    for job in jobs:
        batch = str(job.batch_id)
        if batch not in buckets:
            buckets[batch] = []
            order.append(batch)
        buckets[batch].append(job)
    return [(batch, buckets[batch]) for batch in order]


def _grouped_keys(snapshot: QueueSnapshot) -> list[str]:
    keys: list[str] = []
    for batch_id, group in _groups(snapshot.jobs):
        keys.append(f"batch:{batch_id}")
        keys.extend(str(job.job_id) for job in group)
    return keys


def _header_cells(batch_id: str, group: list[JobRow]) -> tuple[Text, Text, Text, Text]:
    label = Text(f"▸ Batch {batch_id[:8]} · {len(group)} tracks", style="dim bold")
    return (Text("", style="dim"), label, Text(""), Text(""))


def _cells(job: JobRow) -> tuple[Text, Text, Text, Text]:
    return (_status(job), Text(job.title or "—"), _bar(job.percent, job.status), _step(job))


def _bar(percent: int, status: str) -> Text:
    filled = round(percent / 100 * _BAR_WIDTH)
    style = "green" if status in _DONE else "red" if status in _BAD else "cyan"
    text = Text()
    text.append("█" * filled + "░" * (_BAR_WIDTH - filled), style=style)
    text.append(f" {percent:3d}%")
    return text


def _status(job: JobRow) -> Text:
    glyph = _GLYPH.get(job.status, "·")
    style = "green" if job.status in _DONE else "red" if job.status in _BAD else "cyan"
    return Text(f"{glyph} {job.status}", style=style)


def _step(job: JobRow) -> Text:
    """The detail cell: failure/skip reason, the (server) output path, or the phase."""
    if job.status == "failed" and job.error:
        return Text(job.error, style="red")
    if job.status == "skipped" and job.skip_reason:
        return Text(f"skipped: {job.skip_reason}", style="yellow")
    if job.status == "completed" and job.output_path:
        return Text(job.output_path)
    return Text(job.phase)
