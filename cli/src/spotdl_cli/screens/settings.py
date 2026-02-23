"""Settings screen for SpotDL CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Input,
    Label,
    Rule,
    Select,
    Static,
)

from spotdl_cli.config import get_settings
from spotdl_cli.core import APIError, get_api_client

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_PREFERENCES = [
    {"id": "youtube_music", "enabled": True},
    {"id": "youtube", "enabled": True},
    {"id": "soundcloud", "enabled": False},
    {"id": "bandcamp", "enabled": False},
    {"id": "piped", "enabled": False},
]

DEFAULT_METADATA_PREFERENCES = [
    {"id": "spotify", "enabled": True},
    {"id": "musicbrainz", "enabled": True},
    {"id": "discogs", "enabled": True},
]

DEFAULT_LYRICS_PREFERENCES = [
    {"id": "synced", "enabled": True},
    {"id": "genius", "enabled": True},
    {"id": "musixmatch", "enabled": True},
    {"id": "azlyrics", "enabled": False},
]

AUDIO_PROVIDER_LABELS = {
    "youtube_music": "YouTube Music",
    "youtube": "YouTube",
    "soundcloud": "SoundCloud",
    "bandcamp": "Bandcamp",
    "piped": "Piped",
}

METADATA_PROVIDER_LABELS = {
    "spotify": "Spotify",
    "musicbrainz": "MusicBrainz",
    "discogs": "Discogs",
}

LYRICS_PROVIDER_LABELS = {
    "synced": "Synced",
    "genius": "Genius",
    "musixmatch": "Musixmatch",
    "azlyrics": "AZLyrics",
}


class SettingsScreen(Screen[None]):
    """Application settings screen."""

    TITLE = "Settings"

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
        self._show_api_token = False
        self._audio_prefs = self._normalize_preferences(
            getattr(self._settings, "audio_source_preferences", None),
            DEFAULT_AUDIO_PREFERENCES,
            legacy_ids=self._settings.audio_providers,
        )
        self._metadata_prefs = self._normalize_preferences(
            getattr(self._settings, "metadata_source_preferences", None),
            DEFAULT_METADATA_PREFERENCES,
        )
        self._lyrics_prefs = self._normalize_preferences(
            getattr(self._settings, "lyrics_source_preferences", None),
            DEFAULT_LYRICS_PREFERENCES,
            legacy_ids=self._settings.lyrics_providers,
        )
        self._service_status: dict[str, Any] | None = None

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

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
                with Horizontal(classes="setting-row"):
                    yield Label("API Timeout (s):")
                    yield Input(
                        value=str(self._settings.api_timeout),
                        id="api-timeout",
                        placeholder="30",
                    )
                with Horizontal(classes="setting-row"):
                    yield Label("Auth Token:")
                    yield Input(
                        value=self._settings.auth_token or "",
                        id="api-auth-token",
                        placeholder="Bearer token",
                        password=True,
                    )
                    yield Button(
                        "Show",
                        id="toggle-api-auth-token",
                        variant="default",
                        classes="toggle-visibility-btn",
                    )

            # Connection Status
            with Vertical(classes="settings-group"):
                yield Static("Connection Status", classes="group-title")
                yield Button(
                    "Refresh Status",
                    id="refresh-service-status",
                    variant="default",
                )
                yield DataTable(id="service-status-table")
                yield Static("", id="service-status-overall", classes="status-muted")

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
                    yield Label("Bitrate:")
                    yield Select(
                        [
                            ("Auto", "auto"),
                            ("Disable", "disable"),
                            ("320k", "320k"),
                            ("128k", "128k"),
                            ("VBR 0", "0"),
                            ("VBR 1", "1"),
                            ("VBR 2", "2"),
                            ("VBR 3", "3"),
                            ("VBR 4", "4"),
                            ("VBR 5", "5"),
                            ("VBR 6", "6"),
                            ("VBR 7", "7"),
                            ("VBR 8", "8"),
                            ("VBR 9", "9"),
                        ],
                        value=self._settings.bitrate or "auto",
                        id="bitrate",
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
                    yield Select(
                        [
                            ("Skip", "skip"),
                            ("Force", "force"),
                            ("Metadata", "metadata"),
                        ],
                        value=self._settings.overwrite,
                        id="overwrite",
                    )
                with Horizontal(classes="setting-row"):
                    yield Label("Max Filename Length:")
                    yield Input(
                        value=str(self._settings.max_filename_length),
                        id="max-filename-length",
                        placeholder="255",
                    )
                with Horizontal(classes="setting-row"):
                    yield Label("Filename Restrict:")
                    yield Select(
                        [
                            ("Off", ""),
                            ("Strict", "strict"),
                            ("Loose", "loose"),
                        ],
                        value=self._settings.restrict or "",
                        id="restrict",
                    )
                with Horizontal(classes="setting-row"):
                    yield Label("ID3 Separator:")
                    yield Input(
                        value=self._settings.id3_separator,
                        id="id3-separator",
                        placeholder="/",
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

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Generate LRC files",
                        value=self._settings.generate_lrc,
                        id="generate-lrc",
                    )

            # Provider Settings
            with Vertical(classes="settings-group"):
                yield Static("Provider Preferences", classes="group-title")

                yield Static("Audio Sources", classes="subgroup-title")
                yield DataTable(id="audio-source-table")
                with Horizontal(classes="setting-row"):
                    yield Button("Up", id="audio-source-up", variant="default")
                    yield Button("Down", id="audio-source-down", variant="default")
                    yield Button("Toggle", id="audio-source-toggle", variant="default")

                yield Rule()

                yield Static("Metadata Sources", classes="subgroup-title")
                yield DataTable(id="metadata-source-table")
                with Horizontal(classes="setting-row"):
                    yield Button("Up", id="metadata-source-up", variant="default")
                    yield Button("Down", id="metadata-source-down", variant="default")
                    yield Button("Toggle", id="metadata-source-toggle", variant="default")

                yield Rule()

                yield Static("Lyrics Sources", classes="subgroup-title")
                yield DataTable(id="lyrics-source-table")
                with Horizontal(classes="setting-row"):
                    yield Button("Up", id="lyrics-source-up", variant="default")
                    yield Button("Down", id="lyrics-source-down", variant="default")
                    yield Button("Toggle", id="lyrics-source-toggle", variant="default")

                with Horizontal(classes="setting-row"):
                    yield Label("Search Query Template:")
                    yield Input(
                        value=self._settings.search_query or "",
                        id="search-query",
                        placeholder="{artist} - {title}",
                    )

            # Playlist Settings
            with Vertical(classes="settings-group"):
                yield Static("Playlists", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Playlist numbering",
                        value=self._settings.playlist_numbering,
                        id="playlist-numbering",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Fetch albums for artists",
                        value=self._settings.fetch_albums,
                        id="fetch-albums",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("M3U Template:")
                    yield Input(
                        value=self._settings.m3u or "",
                        id="m3u",
                        placeholder="{list}.m3u",
                    )

            # Archive & Sync
            with Vertical(classes="settings-group"):
                yield Static("Archive & Sync", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Archive File:")
                    yield Input(
                        value=self._settings.archive or "",
                        id="archive",
                        placeholder="~/.spotdl-archive.txt",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Archive unavailable tracks",
                        value=self._settings.add_unavailable,
                        id="add-unavailable",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Save File Path:")
                    yield Input(
                        value=self._settings.save_file or "",
                        id="save-file",
                        placeholder="~/spotdl-save.txt",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Sync without deleting",
                        value=self._settings.sync_without_deleting,
                        id="sync-without-deleting",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Remove LRC on sync",
                        value=self._settings.sync_remove_lrc,
                        id="sync-remove-lrc",
                    )

            # Library Scan
            with Vertical(classes="settings-group"):
                yield Static("Library Scan", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Create skip file",
                        value=self._settings.create_skip_file,
                        id="create-skip-file",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Respect skip file",
                        value=self._settings.respect_skip_file,
                        id="respect-skip-file",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Scan for existing songs",
                        value=self._settings.scan_for_songs,
                        id="scan-for-songs",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Skip explicit tracks",
                        value=self._settings.skip_explicit,
                        id="skip-explicit",
                    )

            # SponsorBlock
            with Vertical(classes="settings-group"):
                yield Static("SponsorBlock", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Enable SponsorBlock",
                        value=self._settings.sponsor_block,
                        id="sponsor-block",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Categories (CSV):")
                    yield Input(
                        value=", ".join(self._settings.sponsor_block_categories),
                        id="sponsor-block-categories",
                        placeholder="sponsor, intro, outro",
                    )

            # Advanced
            with Vertical(classes="settings-group"):
                yield Static("Advanced", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Log Level:")
                    yield Select(
                        [
                            ("Debug", "DEBUG"),
                            ("Info", "INFO"),
                            ("Warning", "WARNING"),
                            ("Error", "ERROR"),
                            ("Critical", "CRITICAL"),
                        ],
                        value=self._settings.log_level,
                        id="log-level",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Cookie File Path:")
                    yield Input(
                        value=self._settings.cookie_file or "",
                        id="cookie-file",
                        placeholder="path/to/cookies.txt",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("FFmpeg Args:")
                    yield Input(
                        value=self._settings.ffmpeg_args or "",
                        id="ffmpeg-args",
                        placeholder="-af loudnorm",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("yt-dlp Args:")
                    yield Input(
                        value=self._settings.yt_dlp_args or "",
                        id="yt-dlp-args",
                        placeholder="--cookies cookies.txt",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Proxy:")
                    yield Input(
                        value=self._settings.proxy or "",
                        id="proxy",
                        placeholder="http://127.0.0.1:8080",
                    )

            # Errors
            with Vertical(classes="settings-group"):
                yield Static("Error Handling", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Save Errors Path:")
                    yield Input(
                        value=self._settings.save_errors or "",
                        id="save-errors",
                        placeholder="~/spotdl-errors.log",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Print errors to console",
                        value=self._settings.print_errors,
                        id="print-errors",
                    )

            # Matching (Offline)
            with Vertical(classes="settings-group"):
                yield Static("Matching", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Auto-select best match",
                        value=not self._settings.offline_mode,
                        id="auto-select-match",
                    )

                with Vertical(
                    id="matching-thresholds",
                    classes="" if self._settings.offline_mode else "hidden",
                ):
                    with Horizontal(classes="setting-row"):
                        yield Label("Name Match Threshold:")
                        yield Input(
                            value=str(self._settings.name_match_threshold),
                            id="name-match-threshold",
                            placeholder="60",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Artist Match Threshold:")
                        yield Input(
                            value=str(self._settings.artist_match_threshold),
                            id="artist-match-threshold",
                            placeholder="70",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Time Match Threshold:")
                        yield Input(
                            value=str(self._settings.time_match_threshold),
                            id="time-match-threshold",
                            placeholder="25",
                        )

            # Appearance
            with Vertical(classes="settings-group"):
                yield Static("Appearance", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Compact mode",
                        value=self._settings.compact_mode,
                        id="compact-mode",
                    )

                with Horizontal(classes="setting-row"):
                    yield Checkbox(
                        "Enable animations",
                        value=self._settings.enable_animations,
                        id="enable-animations",
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
                yield Button("Sync with Server", id="sync-btn", variant="default")
                yield Button("Load from Server", id="load-server-btn", variant="default")
                yield Button("Export to File", id="export-btn", variant="default")
                yield Button("Import from File", id="import-btn", variant="default")
                yield Button("Reset to Defaults", id="reset-btn", variant="warning")
                yield Button("Cancel", id="cancel-btn")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        self._update_status_badges()
        self._init_provider_tables()
        self.run_worker(self._load_service_status())

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes for conditional visibility."""
        if event.checkbox.id == "offline-mode":
            thresholds = self.query_one("#matching-thresholds")
            if event.value:
                thresholds.remove_class("hidden")
            else:
                thresholds.add_class("hidden")

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
        elif event.button.id == "sync-btn":
            await self._sync_settings()
        elif event.button.id == "reset-btn":
            self._reset_to_defaults()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "toggle-api-auth-token":
            self._toggle_visibility("api-auth-token", "toggle-api-auth-token")
        elif event.button.id == "toggle-spotify-secret":
            self._toggle_visibility("spotify-client-secret", "toggle-spotify-secret")
        elif event.button.id == "toggle-sc-client-id":
            self._toggle_visibility("soundcloud-client-id", "toggle-sc-client-id")
        elif event.button.id == "toggle-sc-auth-token":
            self._toggle_visibility("soundcloud-auth-token", "toggle-sc-auth-token")
        elif event.button.id == "audio-source-up":
            self._move_provider(
                "#audio-source-table",
                self._audio_prefs,
                AUDIO_PROVIDER_LABELS,
                -1,
            )
        elif event.button.id == "audio-source-down":
            self._move_provider(
                "#audio-source-table",
                self._audio_prefs,
                AUDIO_PROVIDER_LABELS,
                1,
            )
        elif event.button.id == "audio-source-toggle":
            self._toggle_provider(
                "#audio-source-table",
                self._audio_prefs,
                AUDIO_PROVIDER_LABELS,
            )
        elif event.button.id == "metadata-source-up":
            self._move_provider(
                "#metadata-source-table",
                self._metadata_prefs,
                METADATA_PROVIDER_LABELS,
                -1,
            )
        elif event.button.id == "metadata-source-down":
            self._move_provider(
                "#metadata-source-table",
                self._metadata_prefs,
                METADATA_PROVIDER_LABELS,
                1,
            )
        elif event.button.id == "metadata-source-toggle":
            self._toggle_provider(
                "#metadata-source-table",
                self._metadata_prefs,
                METADATA_PROVIDER_LABELS,
            )
        elif event.button.id == "lyrics-source-up":
            self._move_provider(
                "#lyrics-source-table",
                self._lyrics_prefs,
                LYRICS_PROVIDER_LABELS,
                -1,
            )
        elif event.button.id == "lyrics-source-down":
            self._move_provider(
                "#lyrics-source-table",
                self._lyrics_prefs,
                LYRICS_PROVIDER_LABELS,
                1,
            )
        elif event.button.id == "lyrics-source-toggle":
            self._toggle_provider(
                "#lyrics-source-table",
                self._lyrics_prefs,
                LYRICS_PROVIDER_LABELS,
            )
        elif event.button.id == "refresh-service-status":
            self.run_worker(self._load_service_status())
        elif event.button.id == "export-btn":
            self.run_worker(self._export_settings())
        elif event.button.id == "import-btn":
            self.run_worker(self._import_settings())
        elif event.button.id == "load-server-btn":
            self.run_worker(self._load_from_server())

    async def _sync_settings(self) -> None:
        """Sync settings with server."""
        if not self.spotdl_app.is_online:
            self.notify("Cannot sync in offline mode", severity="warning")
            return

        try:
            api_client = get_api_client()
            
            # First save local changes
            await self._save_settings(close_screen=False)
            
            # Then push to server
            # Convert settings to dict matching backend model
            settings_dict = self._settings.model_dump()
            
            # Filter out fields that are not in UserSettingsUpdate
            # This is a simplification; ideally we'd map fields precisely
            # For now, we'll rely on the backend ignoring extra fields or handle specific mapping if needed
            
            await api_client.update_user_settings(settings_dict)
            self.notify("Settings synced with server")
            
        except APIError as e:
            self.notify(f"Sync failed: {e}", severity="error")
        except Exception as e:
            logger.exception("Sync failed")
            self.notify(f"Sync failed: {e}", severity="error")

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

    def _parse_int(self, value: str, default: int) -> int:
        """Parse an int with fallback."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _parse_float(self, value: str, default: float) -> float:
        """Parse a float with fallback."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _parse_optional(self, value: str) -> str | None:
        """Normalize optional input value."""
        value = value.strip()
        return value or None

    def _normalize_preferences(
        self,
        prefs: list[dict[str, Any]] | None,
        defaults: list[dict[str, Any]],
        *,
        legacy_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Normalize provider preferences with defaults."""
        if prefs:
            normalized = []
            for pref in prefs:
                provider_id = pref.get("id") if isinstance(pref, dict) else None
                if not provider_id:
                    continue
                normalized.append(
                    {"id": provider_id, "enabled": bool(pref.get("enabled", True))}
                )
            if normalized:
                return normalized
        if legacy_ids:
            seen = set()
            normalized: list[dict[str, Any]] = []
            for provider_id in legacy_ids:
                if provider_id:
                    normalized.append({"id": provider_id, "enabled": True})
                    seen.add(provider_id)
            for item in defaults:
                provider_id = item.get("id")
                if provider_id and provider_id not in seen:
                    normalized.append(
                        {"id": provider_id, "enabled": bool(item.get("enabled", False))}
                    )
            return normalized
        return [dict(item) for item in defaults]

    def _parse_csv(self, value: str) -> list[str]:
        """Parse comma-separated string into a list."""
        return [item.strip() for item in value.split(",") if item.strip()]

    def _init_provider_tables(self) -> None:
        """Initialize provider preference tables."""
        self._render_provider_table(
            "#audio-source-table", self._audio_prefs, AUDIO_PROVIDER_LABELS
        )
        self._render_provider_table(
            "#metadata-source-table", self._metadata_prefs, METADATA_PROVIDER_LABELS
        )
        self._render_provider_table(
            "#lyrics-source-table", self._lyrics_prefs, LYRICS_PROVIDER_LABELS
        )

    def _render_provider_table(
        self,
        table_id: str,
        prefs: list[dict[str, Any]],
        labels: dict[str, str],
    ) -> None:
        """Render provider preferences into a DataTable."""
        table = self.query_one(table_id, DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        if len(table.columns) == 0:
            table.add_columns("#", "Provider", "Enabled")
        table.clear()
        for idx, pref in enumerate(prefs, 1):
            provider_id = pref.get("id", "")
            label = labels.get(provider_id, provider_id)
            enabled = "Yes" if pref.get("enabled", True) else "No"
            table.add_row(str(idx), label, enabled, key=provider_id)

    def _selected_provider_index(self, table_id: str, prefs: list[dict[str, Any]]) -> int | None:
        """Get selected provider index for a table."""
        table = self.query_one(table_id, DataTable)
        if table.cursor_row is None:
            return None
        if table.cursor_row >= len(prefs):
            return None
        return table.cursor_row

    def _move_provider(
        self,
        table_id: str,
        prefs: list[dict[str, Any]],
        labels: dict[str, str],
        direction: int,
    ) -> None:
        """Move a provider up or down in the list."""
        index = self._selected_provider_index(table_id, prefs)
        if index is None:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(prefs):
            return
        prefs[index], prefs[new_index] = prefs[new_index], prefs[index]
        self._render_provider_table(table_id, prefs, labels)
        table = self.query_one(table_id, DataTable)
        table.move_cursor(row=new_index)

    def _toggle_provider(
        self,
        table_id: str,
        prefs: list[dict[str, Any]],
        labels: dict[str, str],
    ) -> None:
        """Toggle provider enabled state."""
        index = self._selected_provider_index(table_id, prefs)
        if index is None:
            return
        prefs[index]["enabled"] = not prefs[index].get("enabled", True)
        self._render_provider_table(table_id, prefs, labels)
        table = self.query_one(table_id, DataTable)
        table.move_cursor(row=index)

    async def _load_service_status(self) -> None:
        """Load backend service status."""
        overall = self.query_one("#service-status-overall", Static)
        try:
            is_online = self.spotdl_app.is_online
        except (AssertionError, AttributeError):
            is_online = True
        if not is_online:
            overall.update("[dim]Offline mode — status unavailable[/]")
            return
        try:
            api_client = get_api_client()
            self._service_status = await api_client.get_service_status()
            self.call_later(self._update_service_status_table)
        except APIError as e:
            overall.update(f"[red]Status error: {e}[/red]")

    def _update_service_status_table(self) -> None:
        """Update connection status table."""
        if not self._service_status:
            return
        table = self.query_one("#service-status-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        if len(table.columns) == 0:
            table.add_columns("Type", "Service", "State", "Latency")
        table.clear()
        overall = self.query_one("#service-status-overall", Static)
        overall_state = self._service_status.get("overall_state", "unknown")
        overall.update(f"[dim]Overall:[/] {overall_state}")

        def add_rows(group: str, items: list[dict[str, Any]]) -> None:
            for item in items:
                state = item.get("state", "unknown")
                latency = item.get("latency")
                latency_text = f"{latency}ms" if latency is not None else "-"
                table.add_row(
                    group.title(),
                    item.get("display_name", item.get("name", "")),
                    state,
                    latency_text,
                )

        add_rows("sources", self._service_status.get("sources", []))
        add_rows("targets", self._service_status.get("targets", []))
        add_rows("metadata", self._service_status.get("metadata", []))

    async def _save_settings(self, close_screen: bool = True) -> None:
        """Save settings."""
        try:
            # API settings
            api_url = self.query_one("#api-url", Input).value
            offline_mode = self.query_one("#offline-mode", Checkbox).value
            api_timeout = self.query_one("#api-timeout", Input).value
            auth_token = self.query_one("#api-auth-token", Input).value.strip()

            # Download settings
            output_dir = self.query_one("#output-dir", Input).value
            audio_format = self.query_one("#audio-format", Select).value
            audio_quality = self.query_one("#audio-quality", Select).value
            bitrate = self.query_one("#bitrate", Select).value
            threads = self.query_one("#threads", Select).value
            overwrite = self.query_one("#overwrite", Select).value
            max_filename_length = self.query_one("#max-filename-length", Input).value
            restrict = self.query_one("#restrict", Select).value
            id3_separator = self.query_one("#id3-separator", Input).value

            # Output template
            output_template = self.query_one("#output-template", Input).value

            # Metadata settings
            embed_metadata = self.query_one("#embed-metadata", Checkbox).value
            embed_lyrics = self.query_one("#embed-lyrics", Checkbox).value
            embed_cover = self.query_one("#embed-cover", Checkbox).value
            generate_lrc = self.query_one("#generate-lrc", Checkbox).value

            # Providers
            search_query = self.query_one("#search-query", Input).value

            # Playlists
            playlist_numbering = self.query_one("#playlist-numbering", Checkbox).value
            fetch_albums = self.query_one("#fetch-albums", Checkbox).value
            m3u = self.query_one("#m3u", Input).value

            # Archive & Sync
            archive = self.query_one("#archive", Input).value
            add_unavailable = self.query_one("#add-unavailable", Checkbox).value
            save_file = self.query_one("#save-file", Input).value
            sync_without_deleting = self.query_one(
                "#sync-without-deleting", Checkbox
            ).value
            sync_remove_lrc = self.query_one("#sync-remove-lrc", Checkbox).value

            # Library scan
            create_skip_file = self.query_one("#create-skip-file", Checkbox).value
            respect_skip_file = self.query_one("#respect-skip-file", Checkbox).value
            scan_for_songs = self.query_one("#scan-for-songs", Checkbox).value
            skip_explicit = self.query_one("#skip-explicit", Checkbox).value

            # SponsorBlock
            sponsor_block = self.query_one("#sponsor-block", Checkbox).value
            sponsor_block_categories = self.query_one(
                "#sponsor-block-categories", Input
            ).value

            # Advanced
            log_level = self.query_one("#log-level", Select).value
            cookie_file = self.query_one("#cookie-file", Input).value
            ffmpeg_args = self.query_one("#ffmpeg-args", Input).value
            yt_dlp_args = self.query_one("#yt-dlp-args", Input).value
            proxy = self.query_one("#proxy", Input).value

            # Appearance
            compact_mode = self.query_one("#compact-mode", Checkbox).value
            enable_animations = self.query_one("#enable-animations", Checkbox).value

            # Errors
            save_errors = self.query_one("#save-errors", Input).value
            print_errors = self.query_one("#print-errors", Checkbox).value

            # Matching thresholds
            name_match_threshold = self.query_one("#name-match-threshold", Input).value
            artist_match_threshold = self.query_one("#artist-match-threshold", Input).value
            time_match_threshold = self.query_one("#time-match-threshold", Input).value

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
            self._settings.api_timeout = self._parse_float(
                api_timeout, self._settings.api_timeout
            )
            self._settings.auth_token = auth_token or None
            self._settings.output_dir = Path(output_dir)
            self._settings.audio_format = audio_format
            self._settings.audio_quality = audio_quality
            self._settings.bitrate = None if bitrate in ("", "auto") else bitrate
            self._settings.threads = threads
            self._settings.overwrite = overwrite
            self._settings.max_filename_length = self._parse_int(
                max_filename_length, self._settings.max_filename_length
            )
            self._settings.restrict = None if restrict in ("", "none") else restrict
            self._settings.id3_separator = id3_separator.strip() or self._settings.id3_separator
            self._settings.output_template = output_template
            self._settings.embed_metadata = embed_metadata
            self._settings.embed_lyrics = embed_lyrics
            self._settings.embed_cover = embed_cover
            self._settings.generate_lrc = generate_lrc
            self._settings.audio_source_preferences = list(self._audio_prefs)
            self._settings.metadata_source_preferences = list(self._metadata_prefs)
            self._settings.lyrics_source_preferences = list(self._lyrics_prefs)
            self._settings.audio_providers = [
                p.get("id", "")
                for p in self._audio_prefs
                if p.get("enabled", True)
            ]
            self._settings.lyrics_providers = [
                p.get("id", "")
                for p in self._lyrics_prefs
                if p.get("enabled", True)
            ]
            self._settings.search_query = self._parse_optional(search_query)
            self._settings.playlist_numbering = playlist_numbering
            self._settings.fetch_albums = fetch_albums
            self._settings.m3u = self._parse_optional(m3u)
            self._settings.archive = self._parse_optional(archive)
            self._settings.add_unavailable = add_unavailable
            self._settings.save_file = self._parse_optional(save_file)
            self._settings.sync_without_deleting = sync_without_deleting
            self._settings.sync_remove_lrc = sync_remove_lrc
            self._settings.create_skip_file = create_skip_file
            self._settings.respect_skip_file = respect_skip_file
            self._settings.scan_for_songs = scan_for_songs
            self._settings.skip_explicit = skip_explicit
            self._settings.sponsor_block = sponsor_block
            self._settings.sponsor_block_categories = self._parse_csv(
                sponsor_block_categories
            )
            self._settings.log_level = log_level
            self._settings.cookie_file = self._parse_optional(cookie_file)
            self._settings.ffmpeg_args = self._parse_optional(ffmpeg_args)
            self._settings.yt_dlp_args = self._parse_optional(yt_dlp_args)
            self._settings.proxy = self._parse_optional(proxy)
            self._settings.compact_mode = compact_mode
            self._settings.enable_animations = enable_animations
            self._settings.save_errors = self._parse_optional(save_errors)
            self._settings.print_errors = print_errors
            self._settings.name_match_threshold = self._parse_float(
                name_match_threshold, self._settings.name_match_threshold
            )
            self._settings.artist_match_threshold = self._parse_float(
                artist_match_threshold, self._settings.artist_match_threshold
            )
            self._settings.time_match_threshold = self._parse_float(
                time_match_threshold, self._settings.time_match_threshold
            )
            self._settings.spotify_client_id = spotify_client_id
            self._settings.spotify_client_secret = spotify_client_secret
            self._settings.spotify_user_auth = spotify_user_auth
            self._settings.soundcloud_client_id = sc_client_id
            self._settings.soundcloud_auth_token = sc_auth_token

            # Ensure directories exist
            self._settings.ensure_directories()

            # Persist settings to disk
            self._settings.save()

            # Reset API client so auth/header changes apply immediately
            from spotdl_cli.core import get_api_client
            await get_api_client().close()

            if close_screen:
                self.notify("Settings saved")
                self.app.pop_screen()

        except Exception as e:
            logger.exception("Failed to save settings")
            self.notify(f"Error saving settings: {e}", severity="error")

    def _reset_to_defaults(self) -> None:
        """Reset settings to defaults."""
        from spotdl_cli.config import reset_settings

        defaults = reset_settings()
        self._settings = defaults

        # Reset UI values
        self.query_one("#api-url", Input).value = defaults.api_url
        self.query_one("#offline-mode", Checkbox).value = defaults.offline_mode
        self.query_one("#api-timeout", Input).value = str(defaults.api_timeout)
        self.query_one("#api-auth-token", Input).value = defaults.auth_token or ""
        self.query_one("#output-dir", Input).value = str(defaults.output_dir)
        self.query_one("#audio-format", Select).value = defaults.audio_format
        self.query_one("#audio-quality", Select).value = defaults.audio_quality
        self.query_one("#bitrate", Select).value = defaults.bitrate or "auto"
        self.query_one("#threads", Select).value = defaults.threads
        self.query_one("#overwrite", Select).value = defaults.overwrite
        self.query_one("#max-filename-length", Input).value = str(
            defaults.max_filename_length
        )
        self.query_one("#restrict", Select).value = defaults.restrict or ""
        self.query_one("#id3-separator", Input).value = defaults.id3_separator
        self.query_one("#output-template", Input).value = defaults.output_template
        self.query_one("#embed-metadata", Checkbox).value = defaults.embed_metadata
        self.query_one("#embed-lyrics", Checkbox).value = defaults.embed_lyrics
        self.query_one("#embed-cover", Checkbox).value = defaults.embed_cover
        self.query_one("#generate-lrc", Checkbox).value = defaults.generate_lrc
        self._audio_prefs = self._normalize_preferences(
            defaults.audio_source_preferences,
            DEFAULT_AUDIO_PREFERENCES,
        )
        self._metadata_prefs = self._normalize_preferences(
            defaults.metadata_source_preferences,
            DEFAULT_METADATA_PREFERENCES,
        )
        self._lyrics_prefs = self._normalize_preferences(
            defaults.lyrics_source_preferences,
            DEFAULT_LYRICS_PREFERENCES,
        )
        self._init_provider_tables()
        self.query_one("#search-query", Input).value = defaults.search_query or ""
        self.query_one("#playlist-numbering", Checkbox).value = defaults.playlist_numbering
        self.query_one("#fetch-albums", Checkbox).value = defaults.fetch_albums
        self.query_one("#m3u", Input).value = defaults.m3u or ""
        self.query_one("#archive", Input).value = defaults.archive or ""
        self.query_one("#add-unavailable", Checkbox).value = defaults.add_unavailable
        self.query_one("#save-file", Input).value = defaults.save_file or ""
        self.query_one("#sync-without-deleting", Checkbox).value = (
            defaults.sync_without_deleting
        )
        self.query_one("#sync-remove-lrc", Checkbox).value = defaults.sync_remove_lrc
        self.query_one("#create-skip-file", Checkbox).value = defaults.create_skip_file
        self.query_one("#respect-skip-file", Checkbox).value = defaults.respect_skip_file
        self.query_one("#scan-for-songs", Checkbox).value = defaults.scan_for_songs
        self.query_one("#skip-explicit", Checkbox).value = defaults.skip_explicit
        self.query_one("#sponsor-block", Checkbox).value = defaults.sponsor_block
        self.query_one("#sponsor-block-categories", Input).value = ", ".join(
            defaults.sponsor_block_categories
        )
        self.query_one("#log-level", Select).value = defaults.log_level
        self.query_one("#cookie-file", Input).value = defaults.cookie_file or ""
        self.query_one("#ffmpeg-args", Input).value = defaults.ffmpeg_args or ""
        self.query_one("#yt-dlp-args", Input).value = defaults.yt_dlp_args or ""
        self.query_one("#proxy", Input).value = defaults.proxy or ""
        self.query_one("#compact-mode", Checkbox).value = defaults.compact_mode
        self.query_one("#enable-animations", Checkbox).value = defaults.enable_animations
        self.query_one("#save-errors", Input).value = defaults.save_errors or ""
        self.query_one("#print-errors", Checkbox).value = defaults.print_errors
        self.query_one("#name-match-threshold", Input).value = str(
            defaults.name_match_threshold
        )
        self.query_one("#artist-match-threshold", Input).value = str(
            defaults.artist_match_threshold
        )
        self.query_one("#time-match-threshold", Input).value = str(
            defaults.time_match_threshold
        )
        self.query_one("#spotify-client-id", Input).value = ""
        self.query_one("#spotify-client-secret", Input).value = ""
        self.query_one("#spotify-user-auth", Checkbox).value = False
        self.query_one("#soundcloud-client-id", Input).value = ""
        self.query_one("#soundcloud-auth-token", Input).value = ""

        # Update status badges
        self._update_status_badges()

        self.notify("Settings reset to defaults")

    async def _export_settings(self) -> None:
        """Export settings to a JSON file."""
        try:
            export_path = self._settings.config_dir / "settings-export.json"
            config_data = self._settings.model_dump()
            # Convert Path objects to strings
            for key, value in config_data.items():
                if isinstance(value, Path):
                    config_data[key] = str(value)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
            self.notify(f"Settings exported to {export_path}")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    async def _import_settings(self) -> None:
        """Import settings from a JSON file."""
        try:
            import_path = self._settings.config_dir / "settings-export.json"
            if not import_path.exists():
                self.notify(
                    f"No export file found at {import_path}",
                    severity="warning",
                )
                return

            with open(import_path, encoding="utf-8") as f:
                data = json.load(f)

            # Apply imported settings
            for key, value in data.items():
                if hasattr(self._settings, key):
                    try:
                        setattr(self._settings, key, value)
                    except Exception:
                        pass

            self._settings.save()
            self.notify("Settings imported. Reloading screen...")
            # Pop and re-push to refresh all widgets
            self.app.pop_screen()
            await self.app.push_screen("settings")
        except Exception as e:
            self.notify(f"Import failed: {e}", severity="error")

    async def _load_from_server(self) -> None:
        """Load settings from server."""
        if not self.spotdl_app.is_online:
            self.notify("Cannot load in offline mode", severity="warning")
            return

        try:
            api_client = get_api_client()
            server_settings = await api_client.get_user_settings()

            for key, value in server_settings.items():
                if hasattr(self._settings, key):
                    try:
                        setattr(self._settings, key, value)
                    except Exception:
                        pass

            self._settings.save()
            self.notify("Settings loaded from server. Reloading screen...")
            self.app.pop_screen()
            await self.app.push_screen("settings")
        except APIError as e:
            self.notify(f"Load failed: {e}", severity="error")

    def action_save(self) -> None:
        """Save settings action."""
        self.run_worker(self._save_settings())
