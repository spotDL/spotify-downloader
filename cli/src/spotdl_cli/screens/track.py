"""Track detail screen for SpotDL CLI.

Displays detailed track information including:
- Track metadata (title, artist, album, duration)
- Cross-platform matches with scores
- Lyrics (if available)
- Audio features (BPM, energy, etc.)
- Technical info (ISRC, platform IDs)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Label,
    ProgressBar,
    Rule,
    Static,
)

from spotdl_cli.widgets import CoverArt

from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIError,
    DownloadResult,
    Song,
    get_api_client,
    get_offline_matcher,
)

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class TrackScreen(Screen[None]):
    """Track detail screen matching frontend layout."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("d", "download", "Download"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        song: Song,
        track_id: str | None = None,
        platform: str = "spotify",
    ) -> None:
        """
        Initialize track screen.

        Args:
            song: Song object with basic info
            track_id: Platform-specific track ID (for API calls)
            platform: Platform name
        """
        super().__init__()
        self._song = song
        self._track_id = track_id or song.platform_id
        self._platform = platform
        self._settings = get_settings()
        self._matches: list[DownloadResult] = []
        self._lyrics: str | None = None
        self._audio_features: dict[str, Any] = {}
        self._track_details: dict[str, Any] = {}

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="track-container"):
            # Hero section
            with Vertical(id="track-hero", classes="hero-section"):
                with Horizontal(id="track-hero-content"):
                    # Left: Cover art placeholder
                    yield CoverArt(id="track-cover", classes="cover-placeholder")

                    # Right: Track info
                    with Vertical(id="track-info"):
                        # Badges row
                        with Horizontal(id="track-badges"):
                            yield Static("TRACK", classes="badge badge-info")
                            yield Static(
                                "", id="explicit-badge", classes="badge badge-warning hidden"
                            )
                            yield Static("", id="track-number-badge", classes="badge badge-muted")

                        # Title
                        yield Static("", id="track-title", classes="title-xl")

                        # Artist (clickable)
                        yield Static("", id="track-artist", classes="subtitle link")

                        # Quick stats
                        with Horizontal(id="track-stats", classes="stats-row"):
                            yield Static("", id="track-duration", classes="stat-item")
                            yield Static("", id="track-album", classes="stat-item link")
                            yield Static("", id="track-year", classes="stat-item")
                            yield Static("", id="track-key", classes="stat-item")

                        # Genres
                        with Horizontal(id="track-genres", classes="genre-row"):
                            pass  # Will be populated dynamically

                        # Action buttons
                        with Horizontal(id="track-actions", classes="actions-row"):
                            yield Button(
                                "Download Best Match",
                                id="download-btn",
                                variant="primary",
                            )
                            yield Button("Refresh", id="refresh-btn", variant="default")

            # Main content grid
            with Horizontal(id="track-content"):
                # Left column (2/3)
                with Vertical(id="track-main", classes="main-column"):
                    # Cross-platform matches card
                    with Vertical(classes="card"):
                        yield Static(
                            "Cross-Platform Matches",
                            classes="card-title",
                        )
                        yield Static(
                            "Available download sources ranked by match quality",
                            classes="card-subtitle",
                        )

                        with Container(id="matches-container"):
                            yield DataTable(id="matches-table")

                        yield Static("", id="matches-status", classes="status-muted")

                    yield Rule()

                    # Lyrics card
                    with Vertical(classes="card", id="lyrics-card"):
                        yield Static("Lyrics", classes="card-title")

                        with VerticalScroll(id="lyrics-container", classes="lyrics-scroll"):
                            yield Static("", id="lyrics-content", classes="lyrics-text")

                        yield Static("", id="lyrics-status", classes="status-muted")

                # Right column (1/3)
                with Vertical(id="track-sidebar", classes="sidebar-column"):
                    # Platform links
                    with Vertical(classes="card"):
                        yield Static("Platform Links", classes="card-title")
                        with Vertical(id="platform-links"):
                            yield Static("", id="platform-links-content")

                    # Audio features
                    with Vertical(classes="card", id="audio-features-card"):
                        yield Static("Audio Features", classes="card-title")
                        with Vertical(id="audio-features-content"):
                            # BPM
                            with Horizontal(classes="feature-row"):
                                yield Label("BPM", classes="feature-label")
                                yield Static("--", id="feature-bpm", classes="feature-value")

                            # Energy
                            with Horizontal(classes="feature-row"):
                                yield Label("Energy", classes="feature-label")
                                yield ProgressBar(id="feature-energy", total=100, show_eta=False)

                            # Danceability
                            with Horizontal(classes="feature-row"):
                                yield Label("Danceability", classes="feature-label")
                                yield ProgressBar(
                                    id="feature-danceability", total=100, show_eta=False
                                )

                            # Valence (happiness)
                            with Horizontal(classes="feature-row"):
                                yield Label("Valence", classes="feature-label")
                                yield ProgressBar(id="feature-valence", total=100, show_eta=False)

                    # Track details
                    with Vertical(classes="card", id="track-details-card"):
                        yield Static("Track Details", classes="card-title")
                        with Vertical(id="track-details-content"):
                            yield Static("", id="detail-isrc", classes="detail-row")
                            yield Static("", id="detail-label", classes="detail-row")
                            yield Static("", id="detail-popularity", classes="detail-row")
                            yield Static("", id="detail-platform-id", classes="detail-row")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        # Setup matches table
        table = self.query_one("#matches-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "#",
            "Platform",
            "Title",
            "Artist",
            "Duration",
            "Score",
            "Status",
        )

        # Display initial song data
        self._update_song_display()

        # Load detailed data
        await self._load_track_data()

    def _update_song_display(self) -> None:
        """Update display with current song data."""
        song = self._song

        # Title
        self.query_one("#track-title", Static).update(song.name)

        # Artist
        self.query_one("#track-artist", Static).update(f"by {song.artist}")

        # Duration
        duration_str = f"{song.duration // 60}:{song.duration % 60:02d}"
        self.query_one("#track-duration", Static).update(f"[dim]Duration:[/] {duration_str}")

        # Album
        if song.album_name:
            self.query_one("#track-album", Static).update(f"[dim]Album:[/] {song.album_name}")
        else:
            self.query_one("#track-album", Static).update("")

        # Year
        if song.year:
            self.query_one("#track-year", Static).update(f"[dim]Year:[/] {song.year}")

        # Track number
        if song.track_number:
            badge = self.query_one("#track-number-badge", Static)
            badge.update(f"Track {song.track_number}")
            badge.remove_class("hidden")

        # Explicit
        if song.explicit:
            badge = self.query_one("#explicit-badge", Static)
            badge.update("EXPLICIT")
            badge.remove_class("hidden")

        # Genres
        genres_container = self.query_one("#track-genres", Horizontal)
        for genre in (song.genres or [])[:4]:
            genres_container.mount(Static(genre, classes="badge badge-muted"))

        # Platform link
        platform_content = self.query_one("#platform-links-content", Static)
        platform_icon = self._get_platform_icon(song.platform.value)
        platform_content.update(
            f"{platform_icon} [{song.platform.value}]({song.url})"
        )

        # Cover art
        cover_widget = self.query_one("#track-cover", CoverArt)
        cover_widget.cover_url = song.cover_url

    async def _load_track_data(self) -> None:
        """Load detailed track data from API or offline."""
        status = self.query_one("#matches-status", Static)
        status.update("[dim]Loading matches...[/]")

        # Try online first
        if self.spotdl_app.is_online:
            await self._load_online_data()
        else:
            await self._load_offline_data()

    async def _load_online_data(self) -> None:
        """Load data from API server."""
        try:
            api_client = get_api_client()

            # Get track details
            try:
                self._track_details = await api_client.get_track(
                    self._track_id, self._platform
                )
                self._update_track_details()
            except APIError as e:
                logger.warning(f"Failed to get track details: {e}")

            # Get matches
            try:
                matches = await api_client.find_matches(self._song)
                self._matches = matches
                self._update_matches_table()
            except APIError as e:
                logger.warning(f"Failed to get matches: {e}")
                # Fall back to offline matching
                await self._find_offline_matches()

            # Get lyrics
            try:
                lyrics_data = await api_client.get_lyrics(self._track_id, self._platform)
                self._lyrics = lyrics_data.get("lyrics")
                self._update_lyrics_display()
            except APIError as e:
                logger.debug(f"No lyrics available: {e}")

            # Get audio features
            try:
                self._audio_features = await api_client.get_audio_features(
                    self._track_id, self._platform
                )
                self._update_audio_features()
            except APIError as e:
                logger.debug(f"No audio features available: {e}")

        except Exception as e:
            logger.error(f"Error loading online data: {e}")
            self.notify(f"Error loading data: {e}", severity="error")
            # Fall back to offline
            await self._load_offline_data()

    async def _load_offline_data(self) -> None:
        """Load data using offline providers."""
        await self._find_offline_matches()

        # Lyrics from song object if available
        if self._song.lyrics:
            self._lyrics = self._song.lyrics
            self._update_lyrics_display()
        else:
            lyrics_status = self.query_one("#lyrics-status", Static)
            lyrics_status.update("[dim]Lyrics not available offline[/]")

    async def _find_offline_matches(self) -> None:
        """Find matches using offline matcher."""
        status = self.query_one("#matches-status", Static)
        status.update("[dim]Searching for matches...[/]")

        try:
            offline_matcher = get_offline_matcher()
            results = await offline_matcher.find_matches(self._song, limit=10)

            self._matches = [
                DownloadResult.from_result(r, score=0.0) for r in results
            ]
            self._update_matches_table()

        except Exception as e:
            logger.error(f"Offline matching failed: {e}")
            status.update(f"[red]Error: {e}[/]")

    def _update_matches_table(self) -> None:
        """Update the matches table."""
        table = self.query_one("#matches-table", DataTable)
        table.clear()

        status = self.query_one("#matches-status", Static)

        if not self._matches:
            status.update("[yellow]No matches found[/]")
            return

        for i, match in enumerate(self._matches[:10], 1):
            duration = f"{match.duration // 60}:{match.duration % 60:02d}"
            platform_icon = self._get_platform_icon(match.platform.value)

            # Score display
            score_str = f"{match.score:.0f}%" if match.score > 0 else "—"

            # Status
            status_str = "[green]Verified[/]" if match.verified else "[dim]Unverified[/]"

            table.add_row(
                str(i),
                f"{platform_icon} {match.platform.value}",
                match.name[:35] + "..." if len(match.name) > 35 else match.name,
                match.artist[:20] + "..." if len(match.artist) > 20 else match.artist,
                duration,
                score_str,
                status_str,
            )

        status.update(f"[dim]Found {len(self._matches)} match(es)[/]")

    def _update_lyrics_display(self) -> None:
        """Update lyrics display."""
        lyrics_content = self.query_one("#lyrics-content", Static)
        lyrics_status = self.query_one("#lyrics-status", Static)

        if self._lyrics:
            # Truncate very long lyrics for display
            display_lyrics = self._lyrics
            if len(display_lyrics) > 2000:
                display_lyrics = display_lyrics[:2000] + "\n\n[dim]... (truncated)[/]"
            lyrics_content.update(display_lyrics)
            lyrics_status.update("")
        else:
            lyrics_content.update("[dim]No lyrics available[/]")

    def _update_audio_features(self) -> None:
        """Update audio features display."""
        if not self._audio_features:
            return

        # BPM
        bpm = self._audio_features.get("tempo") or self._audio_features.get("bpm")
        if bpm:
            self.query_one("#feature-bpm", Static).update(f"{bpm:.0f}")

        # Energy (0-1 scale to percentage)
        energy = self._audio_features.get("energy")
        if energy is not None:
            bar = self.query_one("#feature-energy", ProgressBar)
            bar.update(progress=int(energy * 100))

        # Danceability
        dance = self._audio_features.get("danceability")
        if dance is not None:
            bar = self.query_one("#feature-danceability", ProgressBar)
            bar.update(progress=int(dance * 100))

        # Valence
        valence = self._audio_features.get("valence")
        if valence is not None:
            bar = self.query_one("#feature-valence", ProgressBar)
            bar.update(progress=int(valence * 100))

    def _update_track_details(self) -> None:
        """Update track details from API response."""
        if not self._track_details:
            return

        # ISRC
        isrc = self._track_details.get("isrc")
        if isrc:
            self.query_one("#detail-isrc", Static).update(f"[dim]ISRC:[/] {isrc}")

        # Label
        label = self._track_details.get("label")
        if label:
            self.query_one("#detail-label", Static).update(f"[dim]Label:[/] {label}")

        # Popularity
        popularity = self._track_details.get("popularity")
        if popularity is not None:
            self.query_one("#detail-popularity", Static).update(
                f"[dim]Popularity:[/] {popularity}/100"
            )

        # Platform ID
        self.query_one("#detail-platform-id", Static).update(
            f"[dim]ID:[/] {self._track_id}"
        )

    @staticmethod
    def _get_platform_icon(platform: str) -> str:
        """Get icon for platform."""
        icons = {
            "spotify": "[green]●[/]",
            "youtube": "[red]●[/]",
            "youtube_music": "[red]●[/]",
            "deezer": "[magenta]●[/]",
            "soundcloud": "[#ff5500]●[/]",
            "bandcamp": "[cyan]●[/]",
            "apple_music": "[white]●[/]",
            "tidal": "[white]●[/]",
        }
        return icons.get(platform.lower(), "●")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "download-btn":
            await self._download_best_match()
        elif event.button.id == "refresh-btn":
            await self._load_track_data()

    async def _download_best_match(self) -> None:
        """Download the best available match."""
        if not self._matches:
            self.notify("No matches available to download", severity="warning")
            return

        best_match = self._matches[0]
        queue = self.spotdl_app.download_queue

        await queue.add(self._song, result=best_match)
        self.notify(f"Added to queue: {self._song.display_name}")

    def action_download(self) -> None:
        """Download action."""
        self.run_worker(self._download_best_match())

    def action_refresh(self) -> None:
        """Refresh action."""
        self.run_worker(self._load_track_data())
