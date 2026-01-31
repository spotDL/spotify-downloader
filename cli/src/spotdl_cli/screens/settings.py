"""Settings screen for SpotDL CLI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Select,
    Static,
)

from spotdl_cli.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SettingsScreen(Screen[None]):
    """Application settings screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("s", "save", "Save"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="settings-container"):
            # Header
            yield Static("Settings", id="settings-title", classes="title")

            # API Settings
            with Vertical(classes="settings-group"):
                yield Static("API Connection", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Backend URL:")
                    yield Input(
                        value=self._settings.api_url,
                        id="api-url",
                        placeholder="http://localhost:8000",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Offline Mode:")
                    yield Checkbox(
                        "Enable offline mode",
                        value=self._settings.offline_mode,
                        id="offline-mode",
                    )

            # Download Settings
            with Vertical(classes="settings-group"):
                yield Static("Download Settings", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Output Directory:")
                    yield Input(
                        value=str(self._settings.output_dir),
                        id="output-dir",
                        placeholder="~/Music/SpotDL",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Audio Format:")
                    yield Select(
                        [
                            ("MP3", "mp3"),
                            ("M4A", "m4a"),
                            ("FLAC", "flac"),
                            ("Opus", "opus"),
                            ("OGG", "ogg"),
                            ("WAV", "wav"),
                        ],
                        value=self._settings.audio_format,
                        id="audio-format",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Audio Quality:")
                    yield Select(
                        [
                            ("Best", "best"),
                            ("320 kbps", "320k"),
                            ("256 kbps", "256k"),
                            ("192 kbps", "192k"),
                            ("128 kbps", "128k"),
                        ],
                        value=self._settings.audio_quality,
                        id="audio-quality",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Concurrent Downloads:")
                    yield Select(
                        [(str(i), i) for i in range(1, 17)],
                        value=self._settings.threads,
                        id="threads",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Overwrite Files:")
                    yield Checkbox(
                        "Overwrite existing files",
                        value=self._settings.overwrite,
                        id="overwrite",
                    )

            # Output Template
            with Vertical(classes="settings-group"):
                yield Static("Output Template", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Filename Template:")
                    yield Input(
                        value=self._settings.output_template,
                        id="output-template",
                        placeholder="{artist} - {title}",
                    )

                yield Static(
                    "Variables: {artist}, {artists}, {title}, {album}, "
                    "{year}, {track_number}, {disc_number}",
                    classes="help-text",
                )

            # Metadata Settings
            with Vertical(classes="settings-group"):
                yield Static("Metadata Embedding", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Embed metadata",
                        value=self._settings.embed_metadata,
                        id="embed-metadata",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Embed lyrics",
                        value=self._settings.embed_lyrics,
                        id="embed-lyrics",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Embed cover art",
                        value=self._settings.embed_cover,
                        id="embed-cover",
                    )

            # SoundCloud OAuth (CLI-only feature)
            with Vertical(classes="settings-group"):
                yield Static("SoundCloud Authentication", classes="group-title")
                yield Static(
                    "Required for some SoundCloud downloads",
                    classes="help-text",
                )

                with Horizontal(classes="setting-row"):
                    yield Label("Client ID:")
                    yield Input(
                        value=self._settings.soundcloud_client_id or "",
                        id="soundcloud-client-id",
                        placeholder="Optional",
                        password=True,
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Auth Token:")
                    yield Input(
                        value=self._settings.soundcloud_auth_token or "",
                        id="soundcloud-auth-token",
                        placeholder="Optional",
                        password=True,
                    )

            # Actions
            with Horizontal(id="settings-actions"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Reset to Defaults", id="reset-btn", variant="warning")
                yield Button("Cancel", id="cancel-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            await self._save_settings()
        elif event.button.id == "reset-btn":
            self._reset_to_defaults()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    async def _save_settings(self) -> None:
        """Save settings."""
        try:
            # API settings
            api_url = self.query_one("#api-url", Input).value
            offline_mode = self.query_one("#offline-mode", Checkbox).value

            # Download settings
            output_dir = self.query_one("#output-dir", Input).value
            audio_format = self.query_one("#audio-format", Select).value
            audio_quality = self.query_one("#audio-quality", Select).value
            threads = self.query_one("#threads", Select).value
            overwrite = self.query_one("#overwrite", Checkbox).value

            # Output template
            output_template = self.query_one("#output-template", Input).value

            # Metadata settings
            embed_metadata = self.query_one("#embed-metadata", Checkbox).value
            embed_lyrics = self.query_one("#embed-lyrics", Checkbox).value
            embed_cover = self.query_one("#embed-cover", Checkbox).value

            # SoundCloud
            sc_client_id = self.query_one("#soundcloud-client-id", Input).value or None
            sc_auth_token = self.query_one("#soundcloud-auth-token", Input).value or None

            # Update settings
            self._settings.api_url = api_url
            self._settings.offline_mode = offline_mode
            self._settings.output_dir = Path(output_dir)
            self._settings.audio_format = audio_format
            self._settings.audio_quality = audio_quality
            self._settings.threads = threads
            self._settings.overwrite = overwrite
            self._settings.output_template = output_template
            self._settings.embed_metadata = embed_metadata
            self._settings.embed_lyrics = embed_lyrics
            self._settings.embed_cover = embed_cover
            self._settings.soundcloud_client_id = sc_client_id
            self._settings.soundcloud_auth_token = sc_auth_token

            # Ensure directories exist
            self._settings.ensure_directories()

            self.notify("Settings saved")
            self.app.pop_screen()

        except Exception as e:
            logger.exception("Failed to save settings")
            self.notify(f"Error saving settings: {e}", severity="error")

    def _reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        from spotdl_cli.config import Settings

        defaults = Settings()

        # Reset UI values
        self.query_one("#api-url", Input).value = defaults.api_url
        self.query_one("#offline-mode", Checkbox).value = defaults.offline_mode
        self.query_one("#output-dir", Input).value = str(defaults.output_dir)
        self.query_one("#audio-format", Select).value = defaults.audio_format
        self.query_one("#audio-quality", Select).value = defaults.audio_quality
        self.query_one("#threads", Select).value = defaults.threads
        self.query_one("#overwrite", Checkbox).value = defaults.overwrite
        self.query_one("#output-template", Input).value = defaults.output_template
        self.query_one("#embed-metadata", Checkbox).value = defaults.embed_metadata
        self.query_one("#embed-lyrics", Checkbox).value = defaults.embed_lyrics
        self.query_one("#embed-cover", Checkbox).value = defaults.embed_cover
        self.query_one("#soundcloud-client-id", Input).value = ""
        self.query_one("#soundcloud-auth-token", Input).value = ""

        self.notify("Reset to defaults (not saved)")

    def action_save(self) -> None:
        """Save settings action."""
        self.run_worker(self._save_settings())
