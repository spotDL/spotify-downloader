"""Artist detail screen for SpotDL CLI.

Displays detailed artist information including:
- Artist metadata (name, genres, followers)
- Discography (albums, singles, EPs)
- Top tracks
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
    Rule,
    Static,
    TabbedContent,
    TabPane,
)

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


class ArtistScreen(Screen[None]):
    """Artist detail screen matching frontend layout."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("d", "download_all", "Download All"),
        Binding("enter", "view_selected", "View"),
        Binding("tab", "next_tab", "Next Tab", show=False),
    ]

    def __init__(
        self,
        artist_id: str,
        platform: str = "spotify",
        initial_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize artist screen.

        Args:
            artist_id: Artist ID on the platform
            platform: Platform name
            initial_data: Pre-fetched artist data (optional)
        """
        super().__init__()
        self._artist_id = artist_id
        self._platform = platform
        self._settings = get_settings()
        self._artist_data: dict[str, Any] = initial_data or {}
        self._albums: list[dict[str, Any]] = []
        self._top_tracks: list[Song] = []
        self._current_tab = "all"

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="artist-container"):
            # Hero section
            with Vertical(id="artist-hero", classes="hero-section"):
                with Horizontal(id="artist-hero-content"):
                    # Left: Avatar placeholder (circle)
                    yield Static("", id="artist-avatar", classes="avatar-placeholder")

                    # Right: Artist info
                    with Vertical(id="artist-info"):
                        # Badge
                        yield Static("ARTIST", classes="badge badge-info")

                        # Name
                        yield Static("Loading...", id="artist-name", classes="title-xl")

                        # Quick stats
                        with Horizontal(id="artist-stats", classes="stats-row"):
                            yield Static("", id="artist-followers", classes="stat-item")
                            yield Static("", id="artist-albums-count", classes="stat-item")
                            yield Static("", id="artist-tracks-count", classes="stat-item")

                        # Genres
                        with Horizontal(id="artist-genres", classes="genre-row"):
                            pass

                        # Action buttons
                        with Horizontal(id="artist-actions", classes="actions-row"):
                            yield Button(
                                "Download All",
                                id="download-all-btn",
                                variant="primary",
                            )
                            yield Button("Refresh", id="refresh-btn", variant="default")

            # Main content grid
            with Horizontal(id="artist-content"):
                # Left column (2/3)
                with Vertical(id="artist-main", classes="main-column"):
                    # Top tracks section
                    with Vertical(classes="card"):
                        yield Static("Top Tracks", classes="card-title")

                        with Vertical(id="top-tracks-container"):
                            yield DataTable(id="top-tracks-table")

                        yield Static("", id="top-tracks-status", classes="status-muted")

                    yield Rule()

                    # Discography section with tabs
                    with Vertical(classes="card"):
                        yield Static("Discography", classes="card-title")

                        with TabbedContent(id="discography-tabs"):
                            with TabPane("All", id="tab-all"):
                                yield DataTable(id="albums-table-all")
                            with TabPane("Albums", id="tab-albums"):
                                yield DataTable(id="albums-table-albums")
                            with TabPane("Singles", id="tab-singles"):
                                yield DataTable(id="albums-table-singles")
                            with TabPane("EPs", id="tab-eps"):
                                yield DataTable(id="albums-table-eps")

                        yield Static("", id="discography-status", classes="status-muted")

                # Right column (1/3)
                with Vertical(id="artist-sidebar", classes="sidebar-column"):
                    # Platform links
                    with Vertical(classes="card"):
                        yield Static("Platform Links", classes="card-title")
                        with Vertical(id="platform-links"):
                            yield Static("", id="platform-links-content")

                    # About section
                    with Vertical(classes="card", id="about-card"):
                        yield Static("About", classes="card-title")
                        yield Static("", id="artist-bio", classes="bio-text")

                    # Quick stats
                    with Vertical(classes="card"):
                        yield Static("Stats", classes="card-title")
                        with Horizontal(id="quick-stats", classes="stats-grid"):
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-albums", classes="stat-value")
                                yield Static("Albums", classes="stat-label")
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-singles", classes="stat-value")
                                yield Static("Singles", classes="stat-label")
                            with Vertical(classes="stat-box"):
                                yield Static("", id="stat-followers", classes="stat-value")
                                yield Static("Followers", classes="stat-label")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        # Setup tables
        self._setup_table("#top-tracks-table", ["#", "Title", "Album", "Duration"])
        self._setup_table("#albums-table-all", ["Title", "Type", "Tracks", "Year"])
        self._setup_table("#albums-table-albums", ["Title", "Tracks", "Year"])
        self._setup_table("#albums-table-singles", ["Title", "Year"])
        self._setup_table("#albums-table-eps", ["Title", "Tracks", "Year"])

        # Load artist data
        await self._load_artist_data()

    def _setup_table(self, table_id: str, columns: list[str]) -> None:
        """Setup a data table with columns."""
        table = self.query_one(table_id, DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(*columns)

    async def _load_artist_data(self) -> None:
        """Load artist data from API or offline."""
        status = self.query_one("#top-tracks-status", Static)
        status.update("[dim]Loading artist...[/]")

        if self.spotdl_app.is_online and not self._artist_data:
            await self._load_online_data()
        elif self._artist_data:
            self._update_display()
        else:
            await self._load_offline_data()

    async def _load_online_data(self) -> None:
        """Load artist data from API server."""
        try:
            api_client = get_api_client()
            self._artist_data = await api_client.get_artist(self._artist_id, self._platform)
            self._update_display()

        except APIError as e:
            logger.error(f"Failed to load artist: {e}")
            self.notify(f"Error loading artist: {e}", severity="error")
            await self._load_offline_data()

    async def _load_offline_data(self) -> None:
        """Load artist data using offline search."""
        status = self.query_one("#top-tracks-status", Static)

        # Try to search for artist
        try:
            offline_matcher = get_offline_matcher()

            # Search for artist's tracks
            songs = await offline_matcher.search_all(f"artist:{self._artist_id}", limit=50)

            if songs:
                # Build artist data from tracks
                first_song = songs[0]
                self._top_tracks = songs[:10]

                # Group by album
                albums: dict[str, dict[str, Any]] = {}
                for song in songs:
                    album_name = song.album_name or "Unknown"
                    if album_name not in albums:
                        albums[album_name] = {
                            "name": album_name,
                            "type": "album",
                            "total_tracks": 0,
                            "year": song.year,
                            "platform_id": "",
                        }
                    albums[album_name]["total_tracks"] += 1

                self._albums = list(albums.values())
                self._artist_data = {
                    "name": first_song.artist,
                    "genres": first_song.genres or [],
                    "albums": self._albums,
                    "top_tracks": [self._song_to_dict(s) for s in self._top_tracks],
                    "platform": self._platform,
                    "platform_id": self._artist_id,
                }
                self._update_display()
            else:
                status.update("[yellow]Artist not found[/]")

        except Exception as e:
            logger.error(f"Offline artist load failed: {e}")
            status.update(f"[red]Error: {e}[/]")

    def _song_to_dict(self, song: Song) -> dict[str, Any]:
        """Convert Song to dict."""
        return {
            "name": song.name,
            "artist": song.artist,
            "artists": song.artists,
            "album": song.album_name,
            "duration": song.duration,
            "platform": song.platform.value,
            "platform_id": song.platform_id,
            "url": song.url,
        }

    def _update_display(self) -> None:
        """Update display with artist data."""
        if not self._artist_data:
            return

        data = self._artist_data

        # Name
        self.query_one("#artist-name", Static).update(data.get("name", "Unknown Artist"))

        # Followers
        followers = data.get("followers", {})
        if isinstance(followers, dict):
            followers = followers.get("total", 0)
        if followers:
            followers_str = self._format_number(followers)
            self.query_one("#artist-followers", Static).update(
                f"[dim]Followers:[/] {followers_str}"
            )
            self.query_one("#stat-followers", Static).update(followers_str)

        # Albums count
        albums = data.get("albums", [])
        self._albums = albums
        album_count = len([a for a in albums if a.get("type", "").lower() == "album"])
        single_count = len([a for a in albums if a.get("type", "").lower() == "single"])

        self.query_one("#artist-albums-count", Static).update(
            f"[dim]Albums:[/] {album_count}"
        )
        self.query_one("#stat-albums", Static).update(str(album_count))
        self.query_one("#stat-singles", Static).update(str(single_count))

        # Genres
        genres = data.get("genres", [])
        genres_container = self.query_one("#artist-genres", Horizontal)
        for genre in genres[:4]:
            genres_container.mount(Static(genre, classes="badge badge-muted"))

        # Bio
        bio = data.get("bio") or data.get("description", "")
        if bio:
            # Truncate long bios
            if len(bio) > 300:
                bio = bio[:300] + "..."
            self.query_one("#artist-bio", Static).update(bio)
        else:
            self.query_one("#about-card", Vertical).add_class("hidden")

        # Platform link
        url = data.get("url") or f"https://open.spotify.com/artist/{self._artist_id}"
        platform_icon = self._get_platform_icon(self._platform)
        self.query_one("#platform-links-content", Static).update(
            f"{platform_icon} [{self._platform.title()}]({url})"
        )

        # Update top tracks
        self._update_top_tracks(data.get("top_tracks", []))

        # Update discography
        self._update_discography(albums)

    def _update_top_tracks(self, tracks: list[dict[str, Any]]) -> None:
        """Update top tracks table."""
        table = self.query_one("#top-tracks-table", DataTable)
        table.clear()

        self._top_tracks = []

        for i, track in enumerate(tracks[:10], 1):
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
                album_name=track.get("album"),
            )
            self._top_tracks.append(song)

            table.add_row(
                str(i),
                track.get("name", "Unknown")[:35],
                (track.get("album") or "")[:20],
                duration_str,
            )

        status = self.query_one("#top-tracks-status", Static)
        status.update(f"[dim]{len(tracks)} track(s)[/]")

    def _update_discography(self, albums: list[dict[str, Any]]) -> None:
        """Update discography tables."""
        # All albums table
        table_all = self.query_one("#albums-table-all", DataTable)
        table_all.clear()

        table_albums = self.query_one("#albums-table-albums", DataTable)
        table_albums.clear()

        table_singles = self.query_one("#albums-table-singles", DataTable)
        table_singles.clear()

        table_eps = self.query_one("#albums-table-eps", DataTable)
        table_eps.clear()

        for album in albums:
            name = album.get("name", "Unknown")[:40]
            album_type = album.get("type", album.get("album_type", "album")).title()
            tracks = str(album.get("total_tracks", "--"))
            year = str(album.get("year") or album.get("release_date", "")[:4] or "--")

            # All table
            table_all.add_row(name, album_type, tracks, year)

            # Type-specific tables
            type_lower = album_type.lower()
            if type_lower == "album":
                table_albums.add_row(name, tracks, year)
            elif type_lower == "single":
                table_singles.add_row(name, year)
            elif type_lower in ("ep", "compilation"):
                table_eps.add_row(name, tracks, year)

        status = self.query_one("#discography-status", Static)
        status.update(f"[dim]{len(albums)} release(s)[/]")

    @staticmethod
    def _format_number(num: int) -> str:
        """Format large numbers with suffixes."""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

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
        elif event.button.id == "refresh-btn":
            self._artist_data = {}
            await self._load_artist_data()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        table_id = event.data_table.id

        if table_id == "top-tracks-table":
            # View track
            if event.cursor_row < len(self._top_tracks):
                track = self._top_tracks[event.cursor_row]
                await self._view_track(track)
        elif table_id and table_id.startswith("albums-table"):
            # View album
            if event.cursor_row < len(self._albums):
                album = self._albums[event.cursor_row]
                await self._view_album(album)

    async def _view_track(self, track: Song) -> None:
        """Navigate to track screen."""
        from spotdl_cli.screens.track import TrackScreen

        await self.app.push_screen(
            TrackScreen(track, track.platform_id, track.platform.value)
        )

    async def _view_album(self, album: dict[str, Any]) -> None:
        """Navigate to album screen."""
        from spotdl_cli.screens.album import AlbumScreen

        album_id = album.get("platform_id") or album.get("id", "")
        if album_id:
            await self.app.push_screen(
                AlbumScreen(album_id, self._platform, initial_data=album)
            )

    async def _download_all(self) -> None:
        """Download all top tracks using concurrent batch operations."""
        if not self._top_tracks:
            self.notify("No tracks to download", severity="warning")
            return

        queue = self.spotdl_app.download_queue

        # Batch add tracks concurrently for better performance
        batch_size = 10
        for i in range(0, len(self._top_tracks), batch_size):
            batch = self._top_tracks[i : i + batch_size]
            await asyncio.gather(*[queue.add(track) for track in batch])

        self.notify(f"Added {len(self._top_tracks)} tracks to download queue")
        await self.app.push_screen("queue")

    def action_download_all(self) -> None:
        """Download all action."""
        self.run_worker(self._download_all())

    def action_view_selected(self) -> None:
        """View selected item."""
        # Try top tracks table first
        table = self.query_one("#top-tracks-table", DataTable)
        if table.has_focus and table.cursor_row is not None:
            if table.cursor_row < len(self._top_tracks):
                track = self._top_tracks[table.cursor_row]
                self.run_worker(self._view_track(track))

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one("#discography-tabs", TabbedContent)
        tabs.action_next_tab()
