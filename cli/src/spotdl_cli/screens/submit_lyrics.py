"""Submit lyrics screen for CLI."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Static, TextArea

from spotdl_cli.core import APIError, get_api_client

logger = logging.getLogger(__name__)


class SubmitLyricsScreen(ModalScreen[None]):
    """Modal screen to submit user-contributed lyrics."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(
        self,
        *,
        entity_id: str,
        song_name: str,
        on_submit: Callable[[], None],
    ) -> None:
        super().__init__()
        self._entity_id = entity_id
        self._song_name = song_name
        self._on_submit = on_submit

    def compose(self) -> ComposeResult:
        """Compose the screen."""
        with Center(id="submit-lyrics-overlay"):
            with Vertical(id="submit-lyrics-container", classes="card"):
                yield Static("Submit Lyrics", classes="title")
                yield Static(
                    f"Submit lyrics for: {self._song_name}",
                    classes="status-muted",
                )
                yield Input(
                    placeholder="Source name (e.g. genius, custom)",
                    id="submit-lyrics-source",
                )
                yield TextArea(
                    id="submit-lyrics-text",
                )
                with Horizontal(id="submit-lyrics-options"):
                    yield Checkbox(
                        "Synced (LRC format)",
                        value=False,
                        id="submit-lyrics-synced",
                    )
                with Horizontal(id="submit-lyrics-actions"):
                    yield Button("Submit", id="submit-lyrics-submit", variant="primary")
                    yield Button("Cancel", id="submit-lyrics-cancel", variant="default")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-lyrics-submit":
            await self._submit()
        elif event.button.id == "submit-lyrics-cancel":
            self.app.pop_screen()

    async def _submit(self) -> None:
        """Submit the lyrics to the API."""
        source = self.query_one("#submit-lyrics-source", Input).value.strip()
        if not source:
            self.notify("Enter a source name", severity="warning")
            return

        lyrics_text = self.query_one("#submit-lyrics-text", TextArea).text.strip()
        if not lyrics_text:
            self.notify("Enter lyrics text", severity="warning")
            return

        synced = self.query_one("#submit-lyrics-synced", Checkbox).value

        try:
            api_client = get_api_client()
            await api_client.submit_lyrics(
                entity_id=self._entity_id,
                lyrics=lyrics_text,
                source=source,
                synced=synced,
            )
            self._on_submit()
            self.notify("Lyrics submitted")
            self.app.pop_screen()
        except APIError as e:
            self.notify(f"Submit failed: {e}", severity="error")
