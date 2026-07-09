"""``TrackScreen`` — a track's header, community matches, and lyrics (Task 6).

The parity view for one track. It projects a :class:`TrackDetail` into an
:class:`EntityCard`, a column of :class:`MatchGauge`\\s, and a :class:`LyricsPane`,
then services the widgets' intents through a single :class:`TrackViewModel`:
``u``/``d`` on a focused gauge vote (fresh tallies merged back onto that gauge),
``m`` submits a match URL, and ``e`` enqueues a download. Voting/submit are gated on
``can_vote`` and enqueue on ``can_download`` (CONTRACT F) via ``check_action``; every
remote call runs in a background worker and every failure becomes a toast.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.tui.widgets.lyrics_pane import LyricsPane
from spotdl_cli.tui.widgets.match_gauge import MatchGauge
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.track import TrackViewModel
from spotdl_cli.viewmodels.types import TrackDetail


class TrackScreen(SpotdlScreen):
    BINDINGS = [
        Binding("m", "submit_match", "Add match"),
        Binding("e", "enqueue", "Download"),
    ]

    def __init__(self, track_id: UUID) -> None:
        super().__init__(name=f"track:{track_id}")
        self._track_id = track_id
        self._vm: TrackViewModel | None = None

    def compose_content(self) -> ComposeResult:
        yield Input(placeholder="paste a match URL", id="match-url", classes="hidden")
        with VerticalScroll(id="track-scroll"):
            yield Vertical(id="card-slot")
            yield Vertical(id="matches")
            yield Vertical(id="lyrics-slot")

    def on_mount(self) -> None:
        super().on_mount()
        self._vm = self.vm_factory.track()
        self._load()

    # -- gating ---------------------------------------------------------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        session = self.vm_factory.session
        if action == "submit_match":
            return session.can_vote
        if action == "enqueue":
            return session.can_download
        return True

    # -- load + render --------------------------------------------------------
    @work(group="track-load")
    async def _load(self) -> None:
        assert self._vm is not None
        result = await self._vm.load(self._track_id)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        await self._render_detail(result.data)

    async def _render_detail(self, detail: TrackDetail) -> None:
        can_vote = self.vm_factory.session.can_vote
        await self.query_one("#card-slot", Vertical).mount(EntityCard(detail.header))
        matches = self.query_one("#matches", Vertical)
        for row in detail.matches:
            await matches.mount(MatchGauge(row, can_vote=can_vote))
        await self.query_one("#lyrics-slot", Vertical).mount(LyricsPane(detail.lyrics))
        gauges = self.query(MatchGauge)
        if gauges:
            gauges.first().focus()

    # -- voting ---------------------------------------------------------------
    def on_match_gauge_vote_requested(self, message: MatchGauge.VoteRequested) -> None:
        gauge = self._gauge_for(message.match_id)
        if gauge is not None:
            self._vote(gauge, message.value)

    def _gauge_for(self, match_id: UUID) -> MatchGauge | None:
        for gauge in self.query(MatchGauge):
            if gauge.row.id == match_id:
                return gauge
        return None

    @work(exclusive=True, group="track-vote")
    async def _vote(self, gauge: MatchGauge, value: str) -> None:
        assert self._vm is not None
        result = await self._vm.vote_match(gauge.row.id, value)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        fresh = result.data
        # The vote returns tallies only; keep the gauge's structural fields.
        gauge.update_row(
            replace(
                gauge.row,
                upvotes=fresh.upvotes,
                downvotes=fresh.downvotes,
                net_score=fresh.net_score,
                status=fresh.status,
                verified=fresh.verified,
            )
        )

    # -- submit a match -------------------------------------------------------
    def action_submit_match(self) -> None:
        box = self.query_one("#match-url", Input)
        box.remove_class("hidden")
        box.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "match-url":
            return
        url = event.value.strip()
        event.input.add_class("hidden")
        event.input.value = ""
        if url:
            self._submit_match(url)

    @work(exclusive=True, group="track-submit")
    async def _submit_match(self, url: str) -> None:
        assert self._vm is not None
        result = await self._vm.submit_match(url)
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        await self.query_one("#matches", Vertical).mount(
            MatchGauge(result.data, can_vote=self.vm_factory.session.can_vote)
        )

    # -- enqueue --------------------------------------------------------------
    def action_enqueue(self) -> None:
        self._enqueue()

    @work(exclusive=True, group="track-enqueue")
    async def _enqueue(self) -> None:
        assert self._vm is not None
        result = await self._vm.enqueue()
        if result.state is LoadState.ERROR:
            if result.error is not None:
                self.show_error(result.error)
            return
        assert result.data is not None
        self.notify(f"queued {result.data.job_count} track(s)")
