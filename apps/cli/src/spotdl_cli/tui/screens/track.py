"""``TrackScreen`` — a track's header card, community matches, and lyrics (§4).

The parity view for one track. A full-width header card (title + artists + muted
metadata line, accent left border) pins an actions row ([d Download] [m Submit match]
[o Open source]); below it two columns fill — a ``Matches`` panel of
:class:`MatchGauge`\\s (score bar, verified marker, vote arrows; the selected row
reveals its URL) and a ``Lyrics`` pane (synced highlight, source/vote in its border
subtitle). Under 110 cols the two columns stack. Voting/submit are gated on
``can_vote`` and enqueue on ``can_download`` (CONTRACT F); when voting is unavailable
the header shows a "sign in to vote" CTA, and a community sign-in mid-session
re-enables the gauges on resume. Every remote call runs in a worker; failures toast.
"""

from __future__ import annotations

import webbrowser
from dataclasses import replace
from uuid import UUID

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input

from spotdl_cli.tui.screens.base import SpotdlScreen
from spotdl_cli.tui.widgets.entity_card import EntityCard
from spotdl_cli.tui.widgets.lyrics_pane import LyricsPane
from spotdl_cli.tui.widgets.match_gauge import MatchGauge
from spotdl_cli.tui.widgets.patterns import LoadingPane
from spotdl_cli.tui.widgets.sources_panel import SourcesPanel
from spotdl_cli.viewmodels.app_state import SessionSnapshot
from spotdl_cli.viewmodels.base import LoadState
from spotdl_cli.viewmodels.track import TrackViewModel
from spotdl_cli.viewmodels.types import TrackDetail

# Below this width the header stays full-width but the matches/lyrics columns stack.
_STACK_WIDTH = 110
_VOTE_CTA = "🔒  sign in to vote — press 5 for Account"


class TrackScreen(SpotdlScreen):
    BINDINGS = [
        Binding("d", "enqueue", "Download"),
        Binding("m", "submit_match", "Add match"),
        Binding("o", "open_source", "Open source"),
    ]

    def __init__(self, track_id: UUID) -> None:
        super().__init__(name=f"track:{track_id}")
        self._track_id = track_id
        self._vm: TrackViewModel | None = None

    def compose_content(self) -> ComposeResult:
        yield Input(placeholder="paste a match URL", id="match-url", classes="hidden")
        with Vertical(id="track-header", classes="panel"):
            yield Vertical(id="card-slot")
            yield Button(_VOTE_CTA, id="vote-cta", classes="vote-cta hidden")
            with Horizontal(id="track-actions"):
                yield Button("Download", id="act-download", variant="primary")
                yield Button("Submit match", id="act-match")
                yield Button("Open source", id="act-open")
        with Horizontal(id="track-body"):
            with VerticalScroll(id="matches", classes="panel counted"):
                yield LoadingPane("Loading matches…")
            with Vertical(id="lyrics-slot"):
                yield Vertical(LoadingPane("Loading lyrics…"), id="lyrics-inner")
                yield VerticalScroll(
                    LoadingPane("Loading sources…"), id="track-sources", classes="panel counted"
                )

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#track-header", Vertical).border_title = "Track"
        self.query_one("#matches", VerticalScroll).border_title = "Matches"
        self.query_one("#track-sources", VerticalScroll).border_title = "Sources"
        self._apply_width(self.size.width)
        self._vm = self.vm_factory.track()
        self._load()

    def on_resize(self) -> None:
        self._apply_width(self.size.width)

    def on_screen_resume(self) -> None:
        """A community sign-in on the Account screen re-enables voting here (§5 flow 2)."""
        session = self.vm_factory.session
        if self._vm is not None:
            self._vm.update_session(session)
        self._sync_voting(session)

    def _apply_width(self, width: int) -> None:
        self.query_one("#track-body", Horizontal).set_class(width < _STACK_WIDTH, "stacked")

    # -- gating ---------------------------------------------------------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        session = self.spotdl_app.session
        if session is None:
            return True
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
        session = self.vm_factory.session
        can_vote = session.can_vote
        await self.query_one("#card-slot", Vertical).mount(EntityCard(detail.header))
        matches = self.query_one("#matches", VerticalScroll)
        await matches.remove_children()
        matches.border_subtitle = str(len(detail.matches))
        inner = self.query_one("#lyrics-inner", Vertical)
        await inner.remove_children()
        for row in detail.matches:
            await matches.mount(MatchGauge(row, can_vote=can_vote))
        await inner.mount(LyricsPane(detail.lyrics))
        self._sync_voting(session)
        self._load_sources()
        gauges = self.query(MatchGauge)
        if gauges:
            gauges.first().focus()

    @work(group="track-sources")
    async def _load_sources(self) -> None:
        assert self._vm is not None
        result = await self._vm.load_sources()
        panel = self.query_one("#track-sources", VerticalScroll)
        await panel.remove_children()
        rows = result.data if result.state is LoadState.READY and result.data is not None else ()
        panel.border_subtitle = str(len(rows))
        await panel.mount(SourcesPanel(rows))

    def _sync_voting(self, session: SessionSnapshot) -> None:
        """Push the current ``can_vote`` onto the gauges + the header CTA."""
        for gauge in self.query(MatchGauge):
            gauge.set_can_vote(session.can_vote)
        show_cta = not session.can_vote and session.can_auth
        self.query_one("#vote-cta", Button).set_class(not show_cta, "hidden")

    # -- actions row ----------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "act-download":
            self.action_enqueue()
        elif event.button.id in ("act-match", "vote-cta"):
            if event.button.id == "vote-cta":
                self.spotdl_app.call_later(self.spotdl_app.action_switch_section, "auth")
            else:
                self.action_submit_match()
        elif event.button.id == "act-open":
            self.action_open_source()

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
        await self.query_one("#matches", VerticalScroll).mount(
            MatchGauge(result.data, can_vote=self.vm_factory.session.can_vote)
        )

    # -- open source ----------------------------------------------------------
    def action_open_source(self) -> None:
        gauge = self._focused_gauge()
        if gauge is None or not gauge.row.url:
            self.notify("no source URL to open", severity="warning")
            return
        webbrowser.open(gauge.row.url)
        self.notify(f"opened {gauge.row.url}")

    def _focused_gauge(self) -> MatchGauge | None:
        if isinstance(self.focused, MatchGauge):
            return self.focused
        gauges = self.query(MatchGauge)
        return gauges.first() if gauges else None

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
