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
                with Horizontal(classes="setting-row"):
                    yield Label("API Timeout (s):")
                    yield Input(
                        value=str(self._settings.api_timeout),
                        id="api-timeout",
                        placeholder="30",
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
                yield Static("Providers", classes="group-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Audio Providers (CSV):")
                    yield Input(
                        value=", ".join(self._settings.audio_providers),
                        id="audio-providers",
                        placeholder="youtube-music, youtube",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Lyrics Providers (CSV):")
                    yield Input(
                        value=", ".join(self._settings.lyrics_providers),
                        id="lyrics-providers",
                        placeholder="genius, musixmatch",
                    )

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
                yield Static("Matching (Offline)", classes="group-title")

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

    def _parse_csv(self, value: str) -> list[str]:
        """Parse comma-separated string into a list."""
        return [item.strip() for item in value.split(",") if item.strip()]

    async def _save_settings(self) -> None:
        """Save settings."""
        try:
            # API settings
            api_url = self.query_one("#api-url", Input).value
            offline_mode = self.query_one("#offline-mode", Checkbox).value
            api_timeout = self.query_one("#api-timeout", Input).value

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
            audio_providers = self.query_one("#audio-providers", Input).value
            lyrics_providers = self.query_one("#lyrics-providers", Input).value
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
            ffmpeg_args = self.query_one("#ffmpeg-args", Input).value
            yt_dlp_args = self.query_one("#yt-dlp-args", Input).value
            proxy = self.query_one("#proxy", Input).value

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
            self._settings.audio_providers = self._parse_csv(audio_providers)
            self._settings.lyrics_providers = self._parse_csv(lyrics_providers)
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
            self._settings.ffmpeg_args = self._parse_optional(ffmpeg_args)
            self._settings.yt_dlp_args = self._parse_optional(yt_dlp_args)
            self._settings.proxy = self._parse_optional(proxy)
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
        self.query_one("#api-timeout", Input).value = str(defaults.api_timeout)
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
        self.query_one("#audio-providers", Input).value = ", ".join(
            defaults.audio_providers
        )
        self.query_one("#lyrics-providers", Input).value = ", ".join(
            defaults.lyrics_providers
        )
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
        self.query_one("#ffmpeg-args", Input).value = defaults.ffmpeg_args or ""
        self.query_one("#yt-dlp-args", Input).value = defaults.yt_dlp_args or ""
        self.query_one("#proxy", Input).value = defaults.proxy or ""
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

        self.notify("Reset to defaults (not saved)")

    def action_save(self) -> None:
        """Save settings action."""
        self.run_worker(self._save_settings())
