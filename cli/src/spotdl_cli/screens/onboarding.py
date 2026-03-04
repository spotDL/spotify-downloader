"""Onboarding screen for first-time users."""

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
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class OnboardingScreen(Screen[bool]):
    """First-time user onboarding wizard."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "skip", "Skip"),
        Binding("enter", "next", "Next", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._step = 0
        self._total_steps = 4  # Welcome, Output, Spotify, Complete
        self._show_secret = False

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with Vertical(id="onboarding-container"):
            # Progress header
            with Vertical(id="onboarding-header"):
                with Horizontal(id="progress-steps"):
                    # Step indicators: Unicode filled/ring/empty circles
                    yield Static("", id="step-1", classes="step-item")
                    yield Static("─────", classes="step-connector")
                    yield Static("", id="step-2", classes="step-item")
                    yield Static("─────", classes="step-connector")
                    yield Static("", id="step-3", classes="step-item")
                    yield Static("─────", classes="step-connector")
                    yield Static("", id="step-4", classes="step-item")

                yield Static("", id="step-title")

            # Content area
            with VerticalScroll(id="onboarding-content"):
                # Step 1: Welcome
                with Vertical(id="step-welcome", classes="onboarding-step"):
                    with Vertical(id="welcome-content"):
                        yield Static("spotdl", id="welcome-logo")
                        yield Static("Welcome to SpotDL", id="welcome-title", classes="title-xl")
                        yield Static(
                            "Download music from Spotify, YouTube, and more",
                            id="welcome-subtitle",
                            classes="subtitle",
                        )

                        with Vertical(classes="feature-grid"):
                            with Horizontal(classes="feature-item"):
                                yield Static("\u25ce", classes="feature-icon")
                                with Vertical(classes="feature-text"):
                                    yield Static("Multi-Platform", classes="feature-title")
                                    yield Static(
                                        "Spotify, Deezer, Apple Music, YouTube",
                                        classes="feature-desc",
                                    )

                            with Horizontal(classes="feature-item"):
                                yield Static("\u2192", classes="feature-icon")
                                with Vertical(classes="feature-text"):
                                    yield Static("Smart Matching", classes="feature-title")
                                    yield Static(
                                        "Finds the best audio quality match",
                                        classes="feature-desc",
                                    )

                            with Horizontal(classes="feature-item"):
                                yield Static("\u266a", classes="feature-icon")
                                with Vertical(classes="feature-text"):
                                    yield Static("Metadata", classes="feature-title")
                                    yield Static(
                                        "Cover art, lyrics, and tags",
                                        classes="feature-desc",
                                    )

                            with Horizontal(classes="feature-item"):
                                yield Static("\u2193", classes="feature-icon")
                                with Vertical(classes="feature-text"):
                                    yield Static("Offline Mode", classes="feature-title")
                                    yield Static(
                                        "Works without a backend server",
                                        classes="feature-desc",
                                    )

                # Step 2: Output settings
                with Vertical(id="step-output", classes="onboarding-step hidden"):
                    yield Static("Output Settings", classes="title-lg")
                    yield Static(
                        "Choose where to save your music",
                        classes="subtitle",
                    )

                    # Output directory
                    with Vertical(classes="config-card"):
                        with Horizontal(classes="config-card-header"):
                            yield Static("\u2699", classes="config-card-icon")
                            yield Static("Output Directory", classes="config-card-title")
                        yield Static(
                            "Where your downloaded music will be saved",
                            classes="config-card-desc",
                        )
                        yield Input(
                            value=str(self._settings.output_dir),
                            id="output-dir",
                            placeholder="~/Music/SpotDL",
                            classes="config-input",
                        )

                    # Audio format
                    with Vertical(classes="config-card"):
                        with Horizontal(classes="config-card-header"):
                            yield Static("\u266a", classes="config-card-icon")
                            yield Static("Audio Format", classes="config-card-title")
                        yield Static(
                            "Choose the format for your files",
                            classes="config-card-desc",
                        )
                        yield Select(
                            [
                                ("MP3 \u2014 Universal compatibility", "mp3"),
                                ("M4A \u2014 Better quality/size", "m4a"),
                                ("FLAC \u2014 Lossless quality", "flac"),
                                ("Opus \u2014 Modern & efficient", "opus"),
                                ("OGG \u2014 Open format", "ogg"),
                                ("WAV \u2014 Uncompressed", "wav"),
                            ],
                            value=self._settings.audio_format,
                            id="audio-format",
                            classes="config-select",
                        )

                    # Audio quality
                    with Vertical(classes="config-card"):
                        with Horizontal(classes="config-card-header"):
                            yield Static("\u2261", classes="config-card-icon")
                            yield Static("Audio Quality", classes="config-card-title")
                        yield Static(
                            "Higher quality = larger files",
                            classes="config-card-desc",
                        )
                        yield Select(
                            [
                                ("Best available", "best"),
                                ("320 kbps \u2014 High", "320k"),
                                ("256 kbps \u2014 Good", "256k"),
                                ("192 kbps \u2014 Standard", "192k"),
                                ("128 kbps \u2014 Compact", "128k"),
                            ],
                            value=self._settings.audio_quality,
                            id="audio-quality",
                            classes="config-select",
                        )

                # Step 3: Spotify
                with Vertical(id="step-spotify", classes="onboarding-step hidden"):
                    yield Static("Spotify Integration", classes="title-lg")
                    yield Static(
                        "Optional: Connect Spotify for direct URL support",
                        classes="subtitle",
                    )

                    # Status bar
                    yield Static("", id="spotify-status", classes="cred-status-bar")

                    # Credentials card
                    with Vertical(classes="credentials-card"):
                        with Horizontal(classes="credentials-header"):
                            yield Static("API Credentials", classes="credentials-title")
                            yield Static("OPTIONAL", classes="credentials-badge")

                        yield Rule()

                        # Client ID
                        with Vertical(classes="cred-field"):
                            with Horizontal(classes="cred-field-header"):
                                yield Label("Client ID", classes="cred-field-label")
                            yield Input(
                                value=self._settings.spotify_client_id or "",
                                id="spotify-client-id",
                                placeholder="e.g., 1a2b3c4d5e6f7g8h9i0j",
                                classes="cred-input",
                            )

                        # Client Secret
                        with Vertical(classes="cred-field"):
                            with Horizontal(classes="cred-field-header"):
                                yield Label("Client Secret", classes="cred-field-label")
                                yield Button(
                                    "Show",
                                    id="toggle-secret-btn",
                                    variant="default",
                                    classes="toggle-btn",
                                )
                            yield Input(
                                value=self._settings.spotify_client_secret or "",
                                id="spotify-client-secret",
                                placeholder="e.g., a1b2c3d4e5f6g7h8i9j0",
                                password=True,
                                classes="cred-input",
                            )

                        yield Rule()

                        # User auth
                        with Vertical(classes="auth-section"):
                            yield Checkbox(
                                "Enable user authentication",
                                value=self._settings.spotify_user_auth,
                                id="spotify-user-auth",
                            )
                            yield Static(
                                "Required for private playlists",
                                classes="auth-hint",
                            )

                    # Instructions
                    with Vertical(classes="instructions-card"):
                        yield Button(
                            "How to get credentials",
                            id="show-instructions-btn",
                            variant="default",
                            classes="instructions-btn",
                        )
                        with Vertical(id="instructions-content", classes="hidden"):
                            yield Static(
                                "1. Go to [link]developer.spotify.com/dashboard[/link]\n"
                                "2. Log in and click [bold]Create App[/bold]\n"
                                "3. Fill in any name and description\n"
                                "4. Set Redirect URI to: http://localhost:8888/callback\n"
                                "5. Copy your Client ID and Client Secret",
                                classes="hint",
                            )

                    yield Static(
                        "You can skip this and configure later in Settings",
                        classes="skip-note",
                    )

                # Step 4: Complete
                with Vertical(id="step-complete", classes="onboarding-step hidden"):
                    with Vertical(id="complete-content"):
                        yield Static("\u2713", id="complete-icon")
                        yield Static("You're All Set", id="complete-title", classes="title-xl")
                        yield Static(
                            "Start downloading your favorite music",
                            classes="subtitle",
                        )

                        with Vertical(classes="tips-grid"):
                            yield Static("Quick Tips", classes="title-md")

                            with Horizontal(classes="tip-item"):
                                yield Static("[bold cyan]S[/]", classes="tip-key")
                                yield Static("Search for music", classes="tip-desc")

                            with Horizontal(classes="tip-item"):
                                yield Static("[bold cyan]D[/]", classes="tip-key")
                                yield Static("View download queue", classes="tip-desc")

                            with Horizontal(classes="tip-item"):
                                yield Static("[bold cyan],[/]", classes="tip-key")
                                yield Static("Open settings", classes="tip-desc")

                            with Horizontal(classes="tip-item"):
                                yield Static("[bold cyan]?[/]", classes="tip-key")
                                yield Static("Get help", classes="tip-desc")

            # Navigation
            with Horizontal(id="onboarding-nav"):
                yield Button("Skip", id="skip-btn", variant="default")
                yield Button("\u2190 Back", id="back-btn", variant="default", disabled=True)
                yield Button("Next \u2192", id="next-btn", variant="primary")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        self._show_step(0)
        self._update_spotify_status()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id in ("spotify-client-id", "spotify-client-secret"):
            self._update_spotify_status()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "skip-btn":
            await self._complete(skipped=True)
        elif event.button.id == "back-btn":
            self._go_back()
        elif event.button.id == "next-btn":
            await self._go_next()
        elif event.button.id == "toggle-secret-btn":
            self._toggle_secret_visibility()
        elif event.button.id == "show-instructions-btn":
            self._toggle_instructions()

    def _toggle_secret_visibility(self) -> None:
        """Toggle password visibility."""
        self._show_secret = not self._show_secret
        secret_input = self.query_one("#spotify-client-secret", Input)
        toggle_btn = self.query_one("#toggle-secret-btn", Button)

        secret_input.password = not self._show_secret
        toggle_btn.label = "Hide" if self._show_secret else "Show"

    def _toggle_instructions(self) -> None:
        """Toggle instructions visibility."""
        content = self.query_one("#instructions-content", Vertical)
        btn = self.query_one("#show-instructions-btn", Button)

        if content.has_class("hidden"):
            content.remove_class("hidden")
            btn.label = "Hide instructions"
        else:
            content.add_class("hidden")
            btn.label = "How to get credentials"

    def _update_spotify_status(self) -> None:
        """Update the Spotify credentials status indicator."""
        try:
            client_id = self.query_one("#spotify-client-id", Input).value.strip()
            client_secret = self.query_one("#spotify-client-secret", Input).value.strip()
            status = self.query_one("#spotify-status", Static)

            if client_id and client_secret:
                status.update("[green]✓ Credentials configured[/green]")
                status.remove_class("partial")
                status.add_class("configured")
            elif client_id or client_secret:
                status.update("[yellow]\u25ce Both fields required[/yellow]")
                status.remove_class("configured")
                status.add_class("partial")
            else:
                status.update("[dim]○ Not configured — using other providers[/dim]")
                status.remove_class("configured")
                status.remove_class("partial")
        except Exception:
            pass  # Screen not fully mounted yet

    def _update_step_indicators(self) -> None:
        """Update the step progress indicators."""
        for i in range(4):
            step = self.query_one(f"#step-{i + 1}", Static)
            if i < self._step:
                # Completed
                step.update("[green]\u25cf[/]")
                step.add_class("step-number-complete")
                step.remove_class("step-number-active")
                step.remove_class("step-number-pending")
            elif i == self._step:
                # Current
                step.update("[bold cyan]\u25ce[/]")
                step.add_class("step-number-active")
                step.remove_class("step-number-complete")
                step.remove_class("step-number-pending")
            else:
                # Pending
                step.update("[dim]\u25cb[/]")
                step.add_class("step-number-pending")
                step.remove_class("step-number-active")
                step.remove_class("step-number-complete")

        # Update connectors
        connectors = self.query(".step-connector")
        for i, conn in enumerate(connectors):
            if i < self._step:
                conn.update("[green]─────[/green]")
                conn.add_class("step-connector-complete")
            else:
                conn.update("[dim]─────[/dim]")
                conn.remove_class("step-connector-complete")

        # Update title
        step_names = ["Welcome", "Output Settings", "Spotify Integration", "Complete"]
        title = self.query_one("#step-title", Static)
        title.update(f"Step {self._step + 1} of {self._total_steps} — {step_names[self._step]}")

    def _show_step(self, step: int) -> None:
        """Show a specific step."""
        self._step = step

        # Update step indicators
        self._update_step_indicators()

        # Hide all steps
        step_ids = ["step-welcome", "step-output", "step-spotify", "step-complete"]
        for sid in step_ids:
            container = self.query_one(f"#{sid}", Vertical)
            container.add_class("hidden")

        # Show current step
        current = self.query_one(f"#{step_ids[step]}", Vertical)
        current.remove_class("hidden")

        # Update button states
        back_btn = self.query_one("#back-btn", Button)
        next_btn = self.query_one("#next-btn", Button)
        skip_btn = self.query_one("#skip-btn", Button)

        back_btn.disabled = step == 0

        if step == self._total_steps - 1:
            next_btn.label = "\u2192 Get Started"
            skip_btn.add_class("hidden")
        else:
            next_btn.label = "Next \u2192"
            skip_btn.remove_class("hidden")

    def _go_back(self) -> None:
        """Go to previous step."""
        if self._step > 0:
            self._show_step(self._step - 1)

    async def _go_next(self) -> None:
        """Go to next step or complete."""
        # Save settings from current step
        await self._save_current_step()

        if self._step < self._total_steps - 1:
            self._show_step(self._step + 1)
        else:
            await self._complete(skipped=False)

    async def _save_current_step(self) -> None:
        """Save settings from the current step."""
        if self._step == 1:
            # Output settings
            output_dir = self.query_one("#output-dir", Input).value
            audio_format = self.query_one("#audio-format", Select).value
            audio_quality = self.query_one("#audio-quality", Select).value

            self._settings.output_dir = Path(output_dir).expanduser()
            self._settings.audio_format = audio_format
            self._settings.audio_quality = audio_quality

        elif self._step == 2:
            # Spotify settings
            client_id = self.query_one("#spotify-client-id", Input).value.strip()
            client_secret = self.query_one("#spotify-client-secret", Input).value.strip()
            user_auth = self.query_one("#spotify-user-auth", Checkbox).value

            self._settings.spotify_client_id = client_id if client_id else None
            self._settings.spotify_client_secret = client_secret if client_secret else None
            self._settings.spotify_user_auth = user_auth

    async def _complete(self, skipped: bool = False) -> None:
        """Complete onboarding."""
        if not skipped:
            # Ensure directories exist
            self._settings.ensure_directories()

            # Mark onboarding as complete
            self._mark_onboarding_complete()

        self.dismiss(not skipped)

    def _mark_onboarding_complete(self) -> None:
        """Mark onboarding as complete by creating a marker file."""
        marker_file = self._settings.config_dir / ".onboarding_complete"
        marker_file.touch()

    def action_skip(self) -> None:
        """Skip onboarding action."""
        self.run_worker(self._complete(skipped=True))

    def action_next(self) -> None:
        """Next step action."""
        self.run_worker(self._go_next())


def should_show_onboarding() -> bool:
    """Check if onboarding should be shown."""
    settings = get_settings()
    marker_file = settings.config_dir / ".onboarding_complete"
    return not marker_file.exists()
