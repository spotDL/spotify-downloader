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
    Rule,
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
        self._show_spotify_secret = False
        self._show_sc_client_id = False
        self._show_sc_auth_token = False

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

            # Spotify Integration - improved UI
            with Vertical(classes="settings-group credentials-section"):
                with Horizontal(classes="group-header"):
                    yield Static("Spotify Integration", classes="group-title")
                    yield Static("", id="spotify-status-badge", classes="status-badge")

                yield Static(
                    "Enable Spotify URL support and enhanced metadata",
                    classes="help-text section-desc",
                )

                yield Rule()

                # Client ID field
                with Vertical(classes="cred-field-group"):
                    with Horizontal(classes="cred-label-row"):
                        yield Label("Client ID:", classes="cred-label")
                    yield Input(
                        value=self._settings.spotify_client_id or "",
                        id="spotify-client-id",
                        placeholder="Your Spotify Client ID",
                        classes="cred-input",
                    )

                # Client Secret field with show/hide
                with Vertical(classes="cred-field-group"):
                    with Horizontal(classes="cred-label-row"):
                        yield Label("Client Secret:", classes="cred-label")
                        yield Button(
                            "Show",
                            id="toggle-spotify-secret",
                            variant="default",
                            classes="toggle-visibility-btn",
                        )
                    yield Input(
                        value=self._settings.spotify_client_secret or "",
                        id="spotify-client-secret",
                        placeholder="Your Spotify Client Secret",
                        password=True,
                        classes="cred-input",
                    )

                # User auth checkbox
                with Vertical(classes="cred-option-group"):
                    yield Checkbox(
                        "Enable user authentication",
                        value=self._settings.spotify_user_auth,
                        id="spotify-user-auth",
                    )
                    yield Static(
                        "Required for private playlists and liked songs",
                        classes="option-hint",
                    )

                yield Rule()

                # Help link
                yield Static(
                    "Get credentials at: developer.spotify.com/dashboard",
                    classes="cred-help-link",
                )

            # SoundCloud OAuth - improved UI
            with Vertical(classes="settings-group credentials-section"):
                with Horizontal(classes="group-header"):
                    yield Static("SoundCloud Authentication", classes="group-title")
                    yield Static("", id="soundcloud-status-badge", classes="status-badge")

                yield Static(
                    "Required for some SoundCloud downloads",
                    classes="help-text section-desc",
                )

                yield Rule()

                # Client ID field with show/hide
                with Vertical(classes="cred-field-group"):
                    with Horizontal(classes="cred-label-row"):
                        yield Label("Client ID:", classes="cred-label")
                        yield Button(
                            "Show",
                            id="toggle-sc-client-id",
                            variant="default",
                            classes="toggle-visibility-btn",
                        )
                    yield Input(
                        value=self._settings.soundcloud_client_id or "",
                        id="soundcloud-client-id",
                        placeholder="Optional - SoundCloud Client ID",
                        password=True,
                        classes="cred-input",
                    )

                # Auth Token field with show/hide
                with Vertical(classes="cred-field-group"):
                    with Horizontal(classes="cred-label-row"):
                        yield Label("Auth Token:", classes="cred-label")
                        yield Button(
                            "Show",
                            id="toggle-sc-auth-token",
                            variant="default",
                            classes="toggle-visibility-btn",
                        )
                    yield Input(
                        value=self._settings.soundcloud_auth_token or "",
                        id="soundcloud-auth-token",
                        placeholder="Optional - SoundCloud Auth Token",
                        password=True,
                        classes="cred-input",
                    )

            # Actions
            with Horizontal(id="settings-actions"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Reset to Defaults", id="reset-btn", variant="warning")
                yield Button("Cancel", id="cancel-btn")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        self._update_status_badges()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to update status badges."""
        if event.input.id in (
            "spotify-client-id",
            "spotify-client-secret",
            "soundcloud-client-id",
            "soundcloud-auth-token",
        ):
            self._update_status_badges()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            await self._save_settings()
        elif event.button.id == "reset-btn":
            self._reset_to_defaults()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "toggle-spotify-secret":
            self._toggle_visibility("spotify-client-secret", "toggle-spotify-secret")
        elif event.button.id == "toggle-sc-client-id":
            self._toggle_visibility("soundcloud-client-id", "toggle-sc-client-id")
        elif event.button.id == "toggle-sc-auth-token":
            self._toggle_visibility("soundcloud-auth-token", "toggle-sc-auth-token")

    def _toggle_visibility(self, input_id: str, button_id: str) -> None:
        """Toggle password visibility for a field."""
        input_field = self.query_one(f"#{input_id}", Input)
        button = self.query_one(f"#{button_id}", Button)

        input_field.password = not input_field.password
        button.label = "Hide" if not input_field.password else "Show"

    def _update_status_badges(self) -> None:
        """Update the status badges for credential sections."""
        try:
            # Spotify status
            spotify_id = self.query_one("#spotify-client-id", Input).value.strip()
            spotify_secret = self.query_one("#spotify-client-secret", Input).value.strip()
            spotify_badge = self.query_one("#spotify-status-badge", Static)

            if spotify_id and spotify_secret:
                spotify_badge.update("[green]Configured[/green]")
            elif spotify_id or spotify_secret:
                spotify_badge.update("[yellow]Incomplete[/yellow]")
            else:
                spotify_badge.update("[dim]Not configured[/dim]")

            # SoundCloud status
            sc_id = self.query_one("#soundcloud-client-id", Input).value.strip()
            sc_token = self.query_one("#soundcloud-auth-token", Input).value.strip()
            sc_badge = self.query_one("#soundcloud-status-badge", Static)

            if sc_id or sc_token:
                sc_badge.update("[green]Configured[/green]")
            else:
                sc_badge.update("[dim]Not configured[/dim]")

        except Exception:
            pass  # Screen not fully mounted

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

            # Spotify
            spotify_client_id = (
                self.query_one("#spotify-client-id", Input).value.strip() or None
            )
            spotify_client_secret = (
                self.query_one("#spotify-client-secret", Input).value.strip() or None
            )
            spotify_user_auth = self.query_one("#spotify-user-auth", Checkbox).value

            # SoundCloud
            sc_client_id = (
                self.query_one("#soundcloud-client-id", Input).value or None
            )
            sc_auth_token = (
                self.query_one("#soundcloud-auth-token", Input).value or None
            )

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
            self._settings.spotify_client_id = spotify_client_id
            self._settings.spotify_client_secret = spotify_client_secret
            self._settings.spotify_user_auth = spotify_user_auth
            self._settings.soundcloud_client_id = sc_client_id
            self._settings.soundcloud_auth_token = sc_auth_token

            # Ensure directories exist
            self._settings.ensure_directories()

            # Persist settings to disk
            self._settings.save()

            self.notify("Settings saved")
            self.app.pop_screen()

        except Exception as e:
            logger.exception("Failed to save settings")
            self.notify(f"Error saving settings: {e}", severity="error")

    def _reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        from spotdl_cli.config import Settings, reset_settings

        defaults = Settings()
        # Note: This only resets the UI. The actual settings are not persisted
        # until user clicks Save. To fully reset, call reset_settings().

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
        self.query_one("#spotify-client-id", Input).value = ""
        self.query_one("#spotify-client-secret", Input).value = ""
        self.query_one("#spotify-user-auth", Checkbox).value = False
        self.query_one("#soundcloud-client-id", Input).value = ""
        self.query_one("#soundcloud-auth-token", Input).value = ""

        # Update status badges
        self._update_status_badges()

        self.notify("Reset to defaults (not saved)")

    def action_save(self) -> None:
        """Save settings action."""
        self.run_worker(self._save_settings())
