"""Metadata report screen for CLI."""

from __future__ import annotations

import logging
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static

from spotdl_cli.core import APIError, get_api_client

logger = logging.getLogger(__name__)


class ReportScreen(Screen[None]):
    """Report incorrect metadata."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(
        self,
        *,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        fields: list[dict[str, str]],
    ) -> None:
        super().__init__()
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._entity_name = entity_name
        self._fields = fields

    def compose(self) -> ComposeResult:
        """Compose the report screen."""
        with Vertical(id="report-container"):
            yield Static("Report Incorrect Data", classes="title")
            yield Static(
                f'Report an issue with "{self._entity_name}"',
                classes="status-muted",
            )

            yield Select(
                [(f["label"], f["name"]) for f in self._fields],
                id="report-field",
                prompt="Select a field",
            )

            yield Static("", id="report-current-value", classes="status-muted")

            yield Input(
                placeholder="Correct value",
                id="report-suggested-value",
            )
            yield Input(
                placeholder="Additional details (optional)",
                id="report-description",
            )

            with Horizontal(id="report-actions"):
                yield Button("Submit Report", id="report-submit", variant="primary")
                yield Button("Cancel", id="report-cancel", variant="default")

    def action_submit(self) -> None:
        """Submit report action."""
        self.run_worker(self._submit_report())

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Update current value display when field changes."""
        if event.select.id != "report-field":
            return
        current_value = ""
        for field in self._fields:
            if field["name"] == event.value:
                current_value = field.get("current_value", "")
                break
        self.query_one("#report-current-value", Static).update(
            f"[dim]Current value:[/] {current_value or 'Empty'}"
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "report-submit":
            await self._submit_report()
        elif event.button.id == "report-cancel":
            self.app.pop_screen()

    async def _submit_report(self) -> None:
        """Submit report to API."""
        field = self.query_one("#report-field", Select).value
        suggested = self.query_one("#report-suggested-value", Input).value.strip()
        description = self.query_one("#report-description", Input).value.strip()

        if not field or not suggested:
            self.notify("Select a field and provide a value", severity="warning")
            return

        current_value = ""
        for f in self._fields:
            if f["name"] == field:
                current_value = f.get("current_value", "")
                break

        try:
            api_client = get_api_client()
            await api_client.create_report(
                entity_type=self._entity_type,
                entity_id=self._entity_id,
                field_name=field,
                current_value=current_value,
                suggested_value=suggested,
                description=description or None,
            )
            self.notify("Report submitted")
            self.app.pop_screen()
        except APIError as e:
            self.notify(f"Report failed: {e}", severity="error")
