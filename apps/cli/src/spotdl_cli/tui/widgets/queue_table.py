"""``QueueTable`` — a dumb DataTable of download jobs with a progress cell (CONTRACT D).

Renders a :class:`QueueSnapshot`: one row per :class:`JobRow`, keyed by job id so
live WS updates rewrite a row in place (phase/percent/status) instead of churning
the table. A failed row surfaces its error in the status cell. The widget holds no
logic beyond formatting — the screen owns the snapshot and drives every update.
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from spotdl_cli.viewmodels.types import JobRow, QueueSnapshot

_BAR_WIDTH = 12
_DONE = frozenset({"completed", "skipped"})
_BAD = frozenset({"failed", "cancelled"})


class QueueTable(DataTable[Text]):
    """A framework-dumb table bound to the queue snapshot."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._seen: set[str] = set()

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Track", "Phase", "Progress", "Status")

    def update_snapshot(self, snapshot: QueueSnapshot) -> None:
        """Add new job rows and rewrite existing ones in place (stable order)."""
        for job in snapshot.jobs:
            key = str(job.job_id)
            cells = _cells(job)
            if key in self._seen:
                for column, value in zip(self.columns, cells, strict=True):
                    self.update_cell(key, column, value)
            else:
                self.add_row(*cells, key=key)
                self._seen.add(key)


def _cells(job: JobRow) -> tuple[Text, Text, Text, Text]:
    return (
        Text(job.title or "—"),
        Text(job.phase),
        _bar(job.percent, job.status),
        _status(job),
    )


def _bar(percent: int, status: str) -> Text:
    filled = round(percent / 100 * _BAR_WIDTH)
    style = "green" if status in _DONE else "red" if status in _BAD else "cyan"
    text = Text()
    text.append("█" * filled + "░" * (_BAR_WIDTH - filled), style=style)
    text.append(f" {percent:3d}%")
    return text


def _status(job: JobRow) -> Text:
    if job.status == "failed" and job.error:
        return Text(f"failed: {job.error}", style="red")
    if job.status == "skipped" and job.skip_reason:
        return Text(f"skipped: {job.skip_reason}", style="yellow")
    style = "green" if job.status in _DONE else "red" if job.status in _BAD else ""
    return Text(job.status, style=style)
