"""Submit match screen for CLI."""

from __future__ import annotations

import logging
from typing import Callable, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from spotdl_cli.core import APIError, MatchEntry, Song, get_api_client

logger = logging.getLogger(__name__)


class SubmitMatchScreen(Screen[None]):
    """Screen to submit a user-discovered match."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(
        self,
        *,
        source_url: str,
        song: Song,
        on_submit: Callable[[MatchEntry], None],
    ) -> None:
        super().__init__()
        self._source_url = source_url
        self._song = song
        self._on_submit = on_submit

    def compose(self) -> ComposeResult:
        """Compose the screen."""
        with Vertical(id="submit-match-container"):
            yield Static("Submit Match", classes="title")
            yield Static(
                "Provide a URL to a downloadable source (YouTube, SoundCloud, etc.)",
                classes="status-muted",
            )
            yield Input(
                placeholder="Target URL",
                id="submit-match-url",
            )
            with Horizontal(id="submit-match-actions"):
                yield Button("Submit", id="submit-match-submit", variant="primary")
                yield Button("Cancel", id="submit-match-cancel", variant="default")

    def action_submit(self) -> None:
        """Submit action."""
        self.run_worker(self._submit())

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-match-submit":
            await self._submit()
        elif event.button.id == "submit-match-cancel":
            self.app.pop_screen()

    async def _submit(self) -> None:
        """Submit the match to the API."""
        target_url = self.query_one("#submit-match-url", Input).value.strip()
        if not target_url:
            self.notify("Enter a target URL", severity="warning")
            return

        try:
            api_client = get_api_client()
            match = await api_client.submit_match(
                source_url=self._source_url,
                target_url=target_url,
                fallback_song=self._song,
            )
            self._on_submit(match)
            self.notify("Match submitted")
            self.app.pop_screen()
        except APIError as e:
            self.notify(f"Submit failed: {e}", severity="error")
