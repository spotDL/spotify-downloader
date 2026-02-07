"""Playlist detail screen for SpotDL CLI.

Displays detailed playlist information including:
- Playlist metadata (title, owner, description)
- Track list with duration and artist info
- Playlist stats (followers, total tracks, duration)
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
from spotdl_cli.theme import format_number, get_platform_icon, truncate

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class PlaylistScreen(Screen[None]):
    """Playlist detail screen matching frontend layout."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("d", "download_all", "Download All"),
        Binding("enter", "view_track", "View Track"),
        Binding("a", "add_all", "Add All to Queue"),
    ]

    def __init__(
        self,
        playlist_id: str,
        platform: str = "spotify",
        initial_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize playlist screen.

        Args:
            playlist_id: Playlist ID on the platform
            platform: Platform name
            initial_data: Pre-fetched playlist data (optional)
        """
        super().__init__()
        self._playlist_id = playlist_id
        self._platform = platform
        self._settings = get_settings()
        self._playlist_data: dict[str, Any] = initial_data or {}
        self._tracks: list[Song] = []

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="playlist-container"):
            # Hero section
            with Vertical(id="playlist-hero", classes="hero-section"):
                with Horizontal(id="playlist-hero-content"):
                    # Left: Cover art placeholder
                    yield CoverArt(id="playlist-cover", classes="cover-placeholder-large")

                    # Right: Playlist info
                    with Vertical(id="playlist-info"):
                        # Badge
                        yield Static("PLAYLIST", classes="badge badge-info")

                        # Title
                        yield Static("Loading...", id="playlist-title", classes="title-xl")

                        # Owner
                        yield Static("", id="playlist-owner", classes="subtitle")

                        # Description
                        yield Static("", id="playlist-description", classes="description-text")

                        # Quick stats
                        with Horizontal(id="playlist-stats", classes="stats-row"):
                            yield Static("", id="playlist-tracks-count", classes="stat-item")
                            yield Static("", id="playlist-followers", classes="stat-item")
                            yield Static("", id="playlist-duration", classes="stat-item")
                            yield Static("", id="playlist-visibility", classes="stat-item")

                        # Action buttons
                        with Horizontal(id="playlist-actions", classes="actions-row"):
                            yield Button(
                                "Download All",
                                id="download-all-btn",
                                variant="primary",
                            )
                            yield Button("Add to Queue", id="add-queue-btn", variant="success")
                            yield Button("Refresh", id="refresh-btn", variant="default")

            # Main content grid
            with Horizontal(id="playlist-content"):
                # Left column (2/3) - Track list
                with Vertical(id="playlist-main", classes="main-column"):
                    with Vertical(classes="card"):
                        yield Static("Tracks", classes="card-title")
                        yield Static(
                            "All tracks in this playlist",
                            classes="card-subtitle",
                        )

                        with Vertical(id="tracks-container"):
                            yield DataTable(id="tracks-table")

                        yield Static("", id="tracks-status", classes="status-muted")

                # Right column (1/3)
                with Vertical(id="playlist-sidebar", classes="sidebar-column"):
                    # Platform links
                    with Vertical(classes="card"):
                        yield Static("Platform Links", classes="card-title")
                        with Vertical(id="platform-links"):
                            yield Static("", id="platform-links-content")

                    # Playlist details
                    with Vertical(classes="card"):
                        yield Static("Playlist Details", classes="card-title")
                        with Vertical(id="playlist-details"):
                            yield Static("", id="detail-owner")
                            yield Static("", id="detail-visibility")
                            yield Static("", id="detail-collaborative")
                            yield Static("", id="detail-created")
                            yield Static("", id="detail-platform-id")

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
                                yield Static("", id="stat-followers", classes="stat-value")
                                yield Static("Followers", classes="stat-label")

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
            "Album",
            "Duration",
            "Added",
        )

        # Load playlist data
        await self._load_playlist_data()

    async def _load_playlist_data(self) -> None:
        """Load playlist data from API or offline."""
        status = self.query_one("#tracks-status", Static)
        status.update("[dim]Loading playlist...[/]")

        if self.spotdl_app.is_online and not self._playlist_data:
            await self._load_online_data()
        elif self._playlist_data and self._playlist_data.get("tracks"):
            # We already have full data with tracks
            self._update_display()
        else:
            # We have partial data (just name) or no data - load offline
            await self._load_offline_data()

    async def _load_online_data(self) -> None:
        """Load playlist data from API server."""
        try:
            api_client = get_api_client()
            self._playlist_data = await api_client.get_playlist(
                self._playlist_id, self._platform
            )
            self._update_display()

        except APIError as e:
            logger.error(f"Failed to load playlist: {e}")
            self.notify(f"Error loading playlist: {e}", severity="error")
            await self._load_offline_data()

    async def _load_offline_data(self) -> None:
        """Load playlist data using offline resolver."""
        status = self.query_one("#tracks-status", Static)

        try:
            offline_matcher = get_offline_matcher()
            songs: list[Song] = []

            # If the ID looks like a real platform ID, try URL resolution
            if not self._playlist_id.startswith("offline-"):
                url = f"https://open.spotify.com/playlist/{self._playlist_id}"
                if self._platform == "deezer":
                    url = f"https://www.deezer.com/playlist/{self._playlist_id}"
                try:
                    songs = await offline_matcher.resolve_url(url)
                except Exception:
                    pass

            # Fall back to searching by playlist name from initial_data
            if not songs:
                playlist_name = (self._playlist_data or {}).get("name", "")
                query = playlist_name or self._playlist_id
                songs = await offline_matcher.search_all(query, limit=50)

            if songs:
                self._tracks = songs
                first_song = songs[0]
                self._playlist_data = {
                    **self._playlist_data,
                    "name": self._playlist_data.get("name") or "Playlist",
                    "owner": self._playlist_data.get("owner", {"display_name": "Unknown"}),
                    "tracks": [self._song_to_dict(s) for s in songs],
                    "total_tracks": len(songs),
                    "cover_url": first_song.cover_url,
                    "platform": self._platform,
                    "platform_id": self._playlist_id,
                    "public": True,
                }
                self._update_display()
            else:
                status.update("[yellow]Playlist not found[/]")

        except Exception as e:
            logger.error(f"Offline playlist load failed: {e}")
            status.update(f"[red]Error: {e}[/]")

    def _song_to_dict(self, song: Song) -> dict[str, Any]:
        """Convert Song to dict for internal use."""
        return {
            "name": song.name,
            "artist": song.artist,
            "artists": song.artists,
            "album": song.album_name,
            "duration": song.duration,
            "platform": song.platform.value,
            "platform_id": song.platform_id,
            "url": song.url,
            "added_at": None,
        }

    def _update_display(self) -> None:
        """Update display with playlist data."""
        if not self._playlist_data:
            return

        data = self._playlist_data

        # Title
        self.query_one("#playlist-title", Static).update(
            data.get("name", "Unknown Playlist")
        )

        # Cover art
        cover_url = data.get("cover_url") or data.get("image_url")
        if cover_url:
            self.query_one("#playlist-cover", CoverArt).cover_url = cover_url

        # Owner
        owner = data.get("owner", {})
        if isinstance(owner, str):
            owner_name = owner
        elif isinstance(owner, dict):
            owner_name = owner.get("display_name") or owner.get("name") or "Unknown"
        else:
            owner_name = "Unknown"
        self.query_one("#playlist-owner", Static).update(f"by {owner_name}")

        # Description
        description = data.get("description", "")
        if description:
            # Truncate long descriptions
            if len(description) > 200:
                description = description[:200] + "..."
            self.query_one("#playlist-description", Static).update(description)

        # Track count
        tracks = data.get("tracks", [])
        # Handle Spotify's tracks.items structure
        if isinstance(tracks, dict):
            tracks = tracks.get("items", [])
        track_count = data.get("total_tracks", len(tracks))
        self.query_one("#playlist-tracks-count", Static).update(
            f"[dim]Tracks:[/] {track_count}"
        )

        # Followers
        followers = data.get("followers", {})
        if isinstance(followers, dict):
            followers = followers.get("total", 0)
        if followers:
            followers_str = format_number(followers)
            self.query_one("#playlist-followers", Static).update(
                f"[dim]Followers:[/] {followers_str}"
            )
            self.query_one("#stat-followers", Static).update(followers_str)
        else:
            self.query_one("#stat-followers", Static).update("--")

        # Total duration
        total_duration = self._calculate_total_duration(tracks)
        if total_duration:
            hours, remainder = divmod(total_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes}m {seconds}s"
            self.query_one("#playlist-duration", Static).update(
                f"[dim]Duration:[/] {duration_str}"
            )
            self.query_one("#stat-duration", Static).update(
                f"{hours}h {minutes}m" if hours else f"{minutes}m"
            )
        else:
            self.query_one("#stat-duration", Static).update("--")

        # Visibility
        is_public = data.get("public", True)
        visibility = "Public" if is_public else "Private"
        self.query_one("#playlist-visibility", Static).update(f"[dim]{visibility}[/]")

        # Platform link
        url = data.get("url") or data.get("external_urls", {}).get(
            "spotify", f"https://open.spotify.com/playlist/{self._playlist_id}"
        )
        platform_icon = get_platform_icon(self._platform)
        platform_name = self._platform.replace("_", " ").title()
        self.query_one("#platform-links-content", Static).update(
            f"{platform_icon} {platform_name}\n[dim]{url}[/dim]"
        )

        # Details panel
        self.query_one("#detail-owner", Static).update(f"[dim]Owner:[/] {owner_name}")
        self.query_one("#detail-visibility", Static).update(
            f"[dim]Visibility:[/] {visibility}"
        )

        collaborative = data.get("collaborative", False)
        self.query_one("#detail-collaborative", Static).update(
            f"[dim]Collaborative:[/] {'Yes' if collaborative else 'No'}"
        )

        self.query_one("#detail-platform-id", Static).update(
            f"[dim]ID:[/] {self._playlist_id}"
        )

        # Quick stats
        self.query_one("#stat-tracks", Static).update(str(track_count))

        # Update tracks table
        self._update_tracks_table(tracks)

    def _calculate_total_duration(self, tracks: list[dict[str, Any]]) -> int:
        """Calculate total duration from tracks."""
        total = 0
        for item in tracks:
            # Handle Spotify's tracks.items[].track structure
            track = item.get("track", item) if isinstance(item, dict) else item
            if track:
                duration = track.get("duration", 0) or track.get("duration_ms", 0) // 1000
                total += duration
        return total

    def _update_tracks_table(self, tracks: list[dict[str, Any]]) -> None:
        """Update the tracks table."""
        table = self.query_one("#tracks-table", DataTable)
        table.clear()

        # Convert to Song objects for internal use
        self._tracks = []

        for i, item in enumerate(tracks, 1):
            # Handle Spotify's tracks.items[].track structure
            track = item.get("track", item) if isinstance(item, dict) else item
            if not track:
                continue

            duration = track.get("duration", 0) or track.get("duration_ms", 0) // 1000
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "--"

            # Get added_at date
            added_at = item.get("added_at", "")
            added_str = added_at[:10] if added_at else "--"

            # Create Song object
            from spotdl_cli.core.types import Platform

            artist = track.get("artist") or ", ".join(
                a.get("name", a) if isinstance(a, dict) else a
                for a in track.get("artists", ["Unknown"])
            )

            song = Song(
                name=track.get("name", "Unknown"),
                artists=track.get("artists", [artist]),
                artist=artist,
                duration=duration,
                platform=Platform(track.get("platform", "spotify")),
                platform_id=track.get("platform_id", track.get("id", "")),
                url=track.get("url", track.get("external_urls", {}).get("spotify", "")),
                album_name=track.get("album", {}).get("name")
                if isinstance(track.get("album"), dict)
                else track.get("album"),
            )
            self._tracks.append(song)

            # Get album name
            album = track.get("album", {})
            album_name = (
                album.get("name", "") if isinstance(album, dict) else (album or "")
            )

            table.add_row(
                str(i),
                truncate(track.get("name", "Unknown"), 35),
                truncate(artist, 25),
                truncate(album_name, 20),
                duration_str,
                added_str,
            )

        status = self.query_one("#tracks-status", Static)
        status.update(f"[dim]{len(self._tracks)} track(s)[/]")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "download-all-btn":
            await self._download_all()
        elif event.button.id == "add-queue-btn":
            await self._add_all_to_queue()
        elif event.button.id == "refresh-btn":
            self._playlist_data = {}
            await self._load_playlist_data()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle track selection."""
        row_index = event.cursor_row
        if row_index is not None and 0 <= row_index < len(self._tracks):
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
