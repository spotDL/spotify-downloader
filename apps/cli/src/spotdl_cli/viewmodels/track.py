"""``TrackViewModel`` — track detail, match voting/submit, lyrics, enqueue, report.

The parity core (CONTRACT A): fetches track + matches + lyrics concurrently, gates
voting/submit/report on ``session.can_vote`` and enqueue on ``session.can_download``
(CONTRACT F), and owns the pure ``active_synced_line`` used by the lyrics widget.
"""

from __future__ import annotations

import asyncio
from typing import cast
from uuid import UUID

from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.mappers import (
    batch_ref,
    lyrics_choice,
    lyrics_choices,
    match_row,
    report_row,
    track_header,
)
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol, VoteValue
from spotdl_cli.viewmodels.types import (
    BatchRef,
    LyricsChoice,
    MatchRow,
    ReportRow,
    TrackDetail,
)
from spotdl_cli.views import DownloadSubmit

_VOTE_BLOCKED = ErrorDisplay("voting isn't available on this server", code=None, severity="error")
_DOWNLOAD_BLOCKED = ErrorDisplay(
    "downloads aren't available on this server", code=None, severity="error"
)
_NOT_LOADED = ErrorDisplay("no track loaded yet", code=None, severity="error")


class TrackViewModel:
    def __init__(self, client: SpotdlClientProtocol, session: SessionSnapshot) -> None:
        self._client = client
        self._session = session
        self._track_id: UUID | None = None

    async def load(self, track_id: UUID) -> Loadable[TrackDetail]:
        self._track_id = track_id

        async def _run() -> TrackDetail:
            track, matches, lyrics = await asyncio.gather(
                self._client.track(track_id),
                self._client.matches(track_id),
                self._client.lyrics(track_id),
            )
            return TrackDetail(
                header=track_header(track),
                matches=tuple(match_row(match) for match in matches),
                lyrics=lyrics_choices(lyrics),
            )

        return await guard(_run())

    async def vote_match(self, match_id: UUID, value: str) -> Loadable[MatchRow]:
        if not self._session.can_vote:
            return Loadable.failed(_VOTE_BLOCKED)

        async def _run() -> MatchRow:
            return match_row(await self._client.vote_match(match_id, cast(VoteValue, value)))

        return await guard(_run())

    async def submit_match(self, url: str) -> Loadable[MatchRow]:
        if not self._session.can_vote:
            return Loadable.failed(_VOTE_BLOCKED)
        if self._track_id is None:
            return Loadable.failed(_NOT_LOADED)
        track_id = self._track_id

        async def _run() -> MatchRow:
            return match_row(await self._client.submit_match(track_id, url))

        return await guard(_run())

    async def vote_lyrics(self, lyrics_id: UUID, value: str) -> Loadable[LyricsChoice]:
        if not self._session.can_vote:
            return Loadable.failed(_VOTE_BLOCKED)

        async def _run() -> LyricsChoice:
            return lyrics_choice(await self._client.vote_lyrics(lyrics_id, cast(VoteValue, value)))

        return await guard(_run())

    async def enqueue(self) -> Loadable[BatchRef]:
        if not self._session.can_download:
            return Loadable.failed(_DOWNLOAD_BLOCKED)
        if self._track_id is None:
            return Loadable.failed(_NOT_LOADED)
        track_id = self._track_id

        async def _run() -> BatchRef:
            batch = await self._client.submit_download(DownloadSubmit(query=str(track_id)))
            return batch_ref(batch)

        return await guard(_run())

    async def report(
        self, *, field: str | None, proposed_value: str | None, reason: str | None
    ) -> Loadable[ReportRow]:
        if not self._session.can_vote:
            return Loadable.failed(_VOTE_BLOCKED)
        if self._track_id is None:
            return Loadable.failed(_NOT_LOADED)
        track_id = self._track_id

        async def _run() -> ReportRow:
            report = await self._client.submit_report(
                "track", track_id, field=field, proposed_value=proposed_value, reason=reason
            )
            return report_row(report)

        return await guard(_run())

    @staticmethod
    def active_synced_line(choice: LyricsChoice, position_ms: int) -> int | None:
        """Index of the synced line active at ``position_ms`` (pure; CONTRACT A).

        The last line whose timestamp is ``<= position_ms``; ``None`` before the
        first timestamp or when the choice carries no timestamps.
        """
        active: int | None = None
        for index, line in enumerate(choice.lines):
            if line.timestamp_ms is None:
                continue
            if line.timestamp_ms <= position_ms:
                active = index
            else:
                break
        return active
