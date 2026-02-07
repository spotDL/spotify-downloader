"""Album detail screen for SpotDL CLI.

Displays detailed album information including:
- Album metadata (title, artist, release date, label)
- Track list with disc separation
- Album details and copyright info
- Platform links
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Static,
)

from spotdl_cli.widgets import CoverArt

from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIError,
    Song,
    get_api_client,
    get_offline_matcher,
)

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class AlbumScreen(Screen[None]):
    """Album detail screen matching frontend layout."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("d", "download_all", "Download All"),
        Binding("enter", "view_track", "View Track"),
        Binding("a", "add_all", "Add All to Queue"),
    ]

    def __init__(
        self,
        album_id: str,
        platform: str = "spotify",
        initial_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize album screen.

        Args:
            album_id: Album ID on the platform
            platform: Platform name
            initial_data: Pre-fetched album data (optional)
        """
        super().__init__()
        self._album_id = album_id
        self._platform = platform
        self._settings = get_settings()
        self._album_data: dict[str, Any] = initial_data or {}
        self._tracks: list[Song] = []

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="album-container"):
            # Hero section
            with Vertical(id="album-hero", classes="hero-section"):
                with Horizontal(id="album-hero-content"):
                    # Left: Cover art placeholder
                    yield CoverArt(id="album-cover", classes="cover-placeholder-large")

                    # Right: Album info
                    with Vertical(id="album-info"):
                        # Badges row
                        with Horizontal(id="album-badges"):
                            yield Static("ALBUM", id="album-type-badge", classes="badge badge-info")
                            yield Static(
                                "", id="album-popularity-badge", classes="badge badge-muted hidden"
                            )

                        # Title
                        yield Static("Loading...", id="album-title", classes="title-xl")

                        # Artist (clickable)
                        yield Static("", id="album-artist", classes="subtitle link")

                        # Quick stats
                        with Horizontal(id="album-stats", classes="stats-row"):
                            yield Static("", id="album-year", classes="stat-item")
                            yield Static("", id="album-tracks-count", classes="stat-item")
                            yield Static("", id="album-duration", classes="stat-item")
                            yield Static("", id="album-discs", classes="stat-item")

                        # Genres
                        with Horizontal(id="album-genres", classes="genre-row"):
                            pass

                        # Label
                        yield Static("", id="album-label", classes="detail-row")

                        # Action buttons
                        with Horizontal(id="album-actions", classes="actions-row"):
                            yield Button(
                                "Download Album",
                                id="download-all-btn",
                                variant="primary",
                            )
                            yield Button("Add to Queue", id="add-queue-btn", variant="success")
                            yield Button("Refresh", id="refresh-btn", variant="default")

            # Main content grid
            with Horizontal(id="album-content"):
                # Left column (2/3) - Track list
                with Vertical(id="album-main", classes="main-column"):
                    with Vertical(classes="card"):
                        yield Static("Track List", classes="card-title")

                        with Vertical(id="tracks-container"):
                            yield DataTable(id="tracks-table")

                        yield Static("", id="tracks-status", classes="status-muted")

                # Right column (1/3)
                with Vertical(id="album-sidebar", classes="sidebar-column"):
                    # Platform links
                    with Vertical(classes="card"):
                        yield Static("Platform Links", classes="card-title")
                        with Vertical(id="platform-links"):
                            yield Static("", id="platform-links-content")

                    # Album details
                    with Vertical(classes="card"):
                        yield Static("Album Details", classes="card-title")
                        with Vertical(id="album-details"):
                            yield Static("", id="detail-type")
                            yield Static("", id="detail-release-date")
                            yield Static("", id="detail-label")
                            yield Static("", id="detail-copyright")
                            yield Static("", id="detail-total-tracks")
                            yield Static("", id="detail-total-duration")

                    # Quick stats card
                    with Vertical(classes="card"):
                        yield Static("Quick Stats", classes="card-title")
                        with Horizontal(id="quick-stats", classes="stats-grid"):
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-tracks", classes="stat-value")
                                yield Static("Tracks", classes="stat-label")
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-duration", classes="stat-value")
                                yield Static("Duration", classes="stat-label")
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-discs", classes="stat-value")
                                yield Static("Discs", classes="stat-label")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        # Setup tracks table
        table = self.query_one("#tracks-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "#",
            "Title",
            "Artist",
            "Duration",
            "Disc",
        )

        # Load album data
        await self._load_album_data()

    async def _load_album_data(self) -> None:
        """Load album data from API or offline."""
        status = self.query_one("#tracks-status", Static)
        status.update("[dim]Loading album...[/]")

        if self.spotdl_app.is_online and not self._album_data:
            await self._load_online_data()
        elif self._album_data:
            self._update_display()
        else:
            await self._load_offline_data()

    async def _load_online_data(self) -> None:
        """Load album data from API server."""
        try:
            api_client = get_api_client()
            self._album_data = await api_client.get_album(self._album_id, self._platform)
            self._update_display()

        except APIError as e:
            logger.error(f"Failed to load album: {e}")
            self.notify(f"Error loading album: {e}", severity="error")
            await self._load_offline_data()

    async def _load_offline_data(self) -> None:
        """Load album data using offline resolver."""
        status = self.query_one("#tracks-status", Static)

        # Try to resolve album URL
        url = f"https://open.spotify.com/album/{self._album_id}"
        if self._platform == "deezer":
            url = f"https://www.deezer.com/album/{self._album_id}"

        try:
            offline_matcher = get_offline_matcher()
            songs = await offline_matcher.resolve_url(url)

            if songs:
                self._tracks = songs
                # Build album data from tracks
                first_song = songs[0]
                self._album_data = {
                    "name": first_song.album_name or "Unknown Album",
                    "artist": first_song.artist,
                    "artists": first_song.artists,
                    "tracks": [self._song_to_dict(s) for s in songs],
                    "total_tracks": len(songs),
                    "release_date": first_song.date,
                    "year": first_song.year,
                    "platform": self._platform,
                    "platform_id": self._album_id,
                }
                self._update_display()
            else:
                status.update("[yellow]Album not found[/]")

        except Exception as e:
            logger.error(f"Offline album load failed: {e}")
            status.update(f"[red]Error: {e}[/]")

    def _song_to_dict(self, song: Song) -> dict[str, Any]:
        """Convert Song to dict for internal use."""
        return {
            "name": song.name,
            "artist": song.artist,
            "artists": song.artists,
            "duration": song.duration,
            "track_number": song.track_number,
            "disc_number": song.disc_number,
            "explicit": song.explicit,
            "platform": song.platform.value,
            "platform_id": song.platform_id,
            "url": song.url,
        }

    def _update_display(self) -> None:
        """Update display with album data."""
        if not self._album_data:
            return

        data = self._album_data

        # Title
        self.query_one("#album-title", Static).update(data.get("name", "Unknown Album"))

        # Cover art
        cover_url = data.get("cover_url") or data.get("image_url")
        if cover_url:
            self.query_one("#album-cover", CoverArt).cover_url = cover_url

        # Artist
        artist = data.get("artist") or ", ".join(data.get("artists", ["Unknown"]))
        self.query_one("#album-artist", Static).update(f"by {artist}")

        # Type badge
        album_type = data.get("album_type", data.get("type", "album")).upper()
        type_badge = self.query_one("#album-type-badge", Static)
        type_badge.update(album_type)

        # Popularity
        popularity = data.get("popularity")
        if popularity:
            pop_badge = self.query_one("#album-popularity-badge", Static)
            pop_badge.update(f"{popularity}%")
            pop_badge.remove_class("hidden")

        # Year/Release date
        release = data.get("release_date", "")
        year = data.get("year") or (release[:4] if release else "")
        if year:
            self.query_one("#album-year", Static).update(f"[dim]Year:[/] {year}")

        # Track count
        track_count = data.get("total_tracks", len(data.get("tracks", [])))
        self.query_one("#album-tracks-count", Static).update(f"[dim]Tracks:[/] {track_count}")

        # Total duration
        tracks = data.get("tracks", [])
        total_duration = sum(t.get("duration", 0) for t in tracks)
        if total_duration:
            hours, remainder = divmod(total_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes}m {seconds}s"
            self.query_one("#album-duration", Static).update(f"[dim]Duration:[/] {duration_str}")

        # Disc count
        disc_numbers = {t.get("disc_number", 1) for t in tracks}
        if len(disc_numbers) > 1:
            self.query_one("#album-discs", Static).update(f"[dim]Discs:[/] {len(disc_numbers)}")

        # Genres
        genres = data.get("genres", [])
        genres_container = self.query_one("#album-genres", Horizontal)
        for genre in genres[:4]:
            genres_container.mount(Static(genre, classes="badge badge-muted"))

        # Label
        label = data.get("label")
        if label:
            self.query_one("#album-label", Static).update(f"[dim]Label:[/] {label}")

        # Platform link
        url = data.get("url") or f"https://open.spotify.com/album/{self._album_id}"
        platform_icon = self._get_platform_icon(self._platform)
        self.query_one("#platform-links-content", Static).update(
            f"{platform_icon} [{self._platform.title()}]({url})"
        )

        # Details panel
        self.query_one("#detail-type", Static).update(f"[dim]Type:[/] {album_type.title()}")
        release_date = data.get("release_date", "")
        if release_date:
            detail_release = self.query_one("#detail-release-date", Static)
            detail_release.update(f"[dim]Released:[/] {release_date}")
        if label:
            self.query_one("#detail-label", Static).update(f"[dim]Label:[/] {label}")

        copyright_text = data.get("copyright") or data.get("copyrights")
        if copyright_text:
            if isinstance(copyright_text, list):
                copyright_text = copyright_text[0].get("text", "") if copyright_text else ""
            self.query_one("#detail-copyright", Static).update(
                f"[dim]Copyright:[/] {copyright_text[:50]}..."
                if len(str(copyright_text)) > 50
                else f"[dim]Copyright:[/] {copyright_text}"
            )

        self.query_one("#detail-total-tracks", Static).update(f"[dim]Tracks:[/] {track_count}")
        dur_display = duration_str if total_duration else "--"
        self.query_one("#detail-total-duration", Static).update(f"[dim]Duration:[/] {dur_display}")

        # Quick stats
        self.query_one("#stat-tracks", Static).update(str(track_count))
        self.query_one("#stat-duration", Static).update(duration_str if total_duration else "--")
        self.query_one("#stat-discs", Static).update(str(len(disc_numbers)))

        # Update tracks table
        self._update_tracks_table(tracks)

    def _update_tracks_table(self, tracks: list[dict[str, Any]]) -> None:
        """Update the tracks table."""
        table = self.query_one("#tracks-table", DataTable)
        table.clear()

        # Sort by disc and track number
        sorted_tracks = sorted(
            tracks,
            key=lambda t: (t.get("disc_number", 1), t.get("track_number", 0)),
        )

        # Convert to Song objects for internal use
        self._tracks = []

        # Check if there are multiple discs
        all_disc_numbers = {t.get("disc_number", 1) for t in tracks}
        has_multiple_discs = len(all_disc_numbers) > 1

        current_disc = 0
        for track in sorted_tracks:
            disc = track.get("disc_number", 1)

            # Add disc separator if needed
            if disc != current_disc and has_multiple_discs:
                current_disc = disc

            track_num = track.get("track_number", "")
            duration = track.get("duration", 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "--"

            # Create Song object
            from spotdl_cli.core.types import Platform

            song = Song(
                name=track.get("name", "Unknown"),
                artists=track.get("artists", [track.get("artist", "Unknown")]),
                artist=track.get("artist", "Unknown"),
                duration=duration,
                platform=Platform(track.get("platform", "spotify")),
                platform_id=track.get("platform_id", ""),
                url=track.get("url", ""),
                album_name=self._album_data.get("name"),
                track_number=track.get("track_number", 0),
                disc_number=track.get("disc_number", 1),
                explicit=track.get("explicit", False),
            )
            self._tracks.append(song)

            table.add_row(
                str(track_num),
                track.get("name", "Unknown")[:40],
                track.get("artist", "Unknown")[:25],
                duration_str,
                str(disc) if has_multiple_discs else "",
            )

        status = self.query_one("#tracks-status", Static)
        status.update(f"[dim]{len(tracks)} track(s)[/]")

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
        if event.button.id == "download-all-btn":
            await self._download_all()
        elif event.button.id == "add-queue-btn":
            await self._add_all_to_queue()
        elif event.button.id == "refresh-btn":
            self._album_data = {}
            await self._load_album_data()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle track selection."""
        if event.row_key is not None and event.row_key.value is not None:
            row_index = event.cursor_row
            if 0 <= row_index < len(self._tracks):
                track = self._tracks[row_index]
                await self._view_track(track)

    async def _view_track(self, track: Song) -> None:
        """Navigate to track detail screen."""
        from spotdl_cli.screens.track import TrackScreen

        await self.app.push_screen(
            TrackScreen(track, track.platform_id, track.platform.value)
        )

    async def _download_all(self) -> None:
        """Download all tracks using concurrent batch operations."""
        if not self._tracks:
            self.notify("No tracks to download", severity="warning")
            return

        queue = self.spotdl_app.download_queue

        # Batch add tracks concurrently for better performance
        batch_size = 10
        for i in range(0, len(self._tracks), batch_size):
            batch = self._tracks[i : i + batch_size]
            await asyncio.gather(*[queue.add(track) for track in batch])

        self.notify(f"Added {len(self._tracks)} tracks to download queue")
        await self.app.push_screen("queue")

    async def _add_all_to_queue(self) -> None:
        """Add all tracks to queue using concurrent batch operations."""
        if not self._tracks:
            self.notify("No tracks to add", severity="warning")
            return

        queue = self.spotdl_app.download_queue

        # Batch add tracks concurrently for better performance
        batch_size = 10
        for i in range(0, len(self._tracks), batch_size):
            batch = self._tracks[i : i + batch_size]
            await asyncio.gather(*[queue.add(track) for track in batch])

        self.notify(f"Added {len(self._tracks)} tracks to queue")

    def action_download_all(self) -> None:
        """Download all action."""
        self.run_worker(self._download_all())

    def action_add_all(self) -> None:
        """Add all to queue action."""
        self.run_worker(self._add_all_to_queue())

    def action_view_track(self) -> None:
        """View selected track."""
        table = self.query_one("#tracks-table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self._tracks):
            track = self._tracks[table.cursor_row]
            self.run_worker(self._view_track(track))
