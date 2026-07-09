"""Display dataclasses the view-models emit (CONTRACT A).

These are the *only* types that cross from a view-model to a screen — frozen,
slotted, and built from stdlib types alone. None leak a generated/server model, so
a client regeneration re-runs the ``views.py`` mappers without rippling into the
TUI. Distinct from the ``views.*`` façade types (``*Row``/``*Detail``/``*Choice``/
``*Snapshot``) so the presentation contract stays decoupled from the wire contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

FieldKind = Literal["str", "int", "bool", "choice", "path"]


@dataclass(frozen=True, slots=True)
class EntityRef:
    """A router dispatch target (from ``resolve``)."""

    entity_type: str
    id: UUID
    title: str


@dataclass(frozen=True, slots=True)
class TrackRow:
    id: UUID
    title: str
    artists: str
    album: str
    duration: str
    explicit: bool
    provider: str


@dataclass(frozen=True, slots=True)
class EntityHeader:
    title: str
    subtitle: str
    kind: str
    stats: tuple[tuple[str, str], ...]
    cover_url: str | None


@dataclass(frozen=True, slots=True)
class MatchRow:
    id: UUID
    provider: str
    url: str
    score: int
    status: str
    verified: bool
    upvotes: int
    downvotes: int
    net_score: int


@dataclass(frozen=True, slots=True)
class LyricsLine:
    text: str
    timestamp_ms: int | None


@dataclass(frozen=True, slots=True)
class LyricsChoice:
    id: UUID
    source: str
    kind: str
    synced: bool
    net_score: int
    lines: tuple[LyricsLine, ...]


@dataclass(frozen=True, slots=True)
class TrackDetail:
    header: EntityHeader
    matches: tuple[MatchRow, ...]
    lyrics: tuple[LyricsChoice, ...]


@dataclass(frozen=True, slots=True)
class CollectionDetail:
    header: EntityHeader
    kind: str
    tracks: tuple[TrackRow, ...]


@dataclass(frozen=True, slots=True)
class JobRow:
    job_id: UUID
    batch_id: UUID
    title: str
    phase: str
    percent: int
    status: str
    error: str | None
    output_path: str | None
    skip_reason: str | None


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    jobs: tuple[JobRow, ...]
    overall_percent: int
    active: int
    completed: int
    failed: int
    skipped: int
    cancelled: int


@dataclass(frozen=True, slots=True)
class BatchRef:
    batch_id: UUID
    job_count: int


@dataclass(frozen=True, slots=True)
class SettingField:
    key: str
    label: str
    kind: FieldKind
    value: str
    choices: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class AuthSnapshot:
    logged_in: bool
    email: str | None
    server_origin: str


@dataclass(frozen=True, slots=True)
class ReportRow:
    id: UUID
    subject_type: str
    subject_id: UUID
    field: str | None
    proposed_value: str | None
    reason: str | None
    status: str
    reporter: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class StatsRow:
    users: int
    tracks: int
    matches: int
    pending_reports: int
    matcher_version: str
