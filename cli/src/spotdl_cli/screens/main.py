"""Main search screen for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Static,
)

from spotdl_cli.core import (
    APIError,
    DownloadResult,
    Song,
    get_offline_matcher,
)
from spotdl_cli.core.types import Platform

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class MainScreen(Screen[None]):
    """Main search and results screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "search", "Search", show=False),
        Binding("a", "add_all", "Add All"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._results: list[Song] = []
        self._offline_matcher = get_offline_matcher()

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp
        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with Vertical(id="search-container"):
            # Search input
            with Horizontal(id="search-input"):
                yield Input(
                    placeholder="Enter a URL or search query...",
                    id="search-box",
                )
                yield Button("Search", id="search-btn", variant="primary")

            # Status bar
            yield Static("Ready", id="status-bar")

            # Results table
            with Container(id="results-container"):
                yield DataTable(id="results-table")

            # Actions
            with Horizontal(id="actions-bar"):
                yield Button("Add Selected", id="add-selected-btn", variant="primary")
                yield Button("Add All", id="add-all-btn", variant="success")
                yield Button("Clear", id="clear-btn", variant="error")

    async def on_mount(self) -> None:
        """Handle screen mount."""
        # Setup results table
        table = self.query_one("#results-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            "Title",
            "Artist",
            "Album",
            "Duration",
            "Source",
        )

        # Focus search input
        self.query_one("#search-box", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-box":
            await self._do_search()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "search-btn":
            await self._do_search()
        elif event.button.id == "add-selected-btn":
            await self._add_selected()
        elif event.button.id == "add-all-btn":
            await self._add_all()
        elif event.button.id == "clear-btn":
            self._clear_results()

    async def _do_search(self) -> None:
        """Perform search."""
        search_box = self.query_one("#search-box", Input)
        query = search_box.value.strip()

        if not query:
            self.notify("Please enter a URL or search query", severity="warning")
            return

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("Searching...")

        try:
            # Check if it's a URL or search query
            if self._is_url(query):
                await self._resolve_url(query)
            else:
                await self._search_songs(query)

            mode = "online" if self.spotdl_app.is_online else "offline"
            status_bar.update(f"Found {len(self._results)} results ({mode})")

        except APIError as e:
            status_bar.update(f"Error: {e}")
            self.notify(str(e), severity="error")
        except Exception as e:
            logger.exception("Search failed")
            status_bar.update(f"Error: {e}")
            self.notify(f"Search failed: {e}", severity="error")

    @staticmethod
    def _is_url(text: str) -> bool:
        """Check if text is a URL."""
        return text.startswith(("http://", "https://", "spotify:", "deezer:"))

    async def _resolve_url(self, url: str) -> None:
        """Resolve a URL to songs."""
        # Try online first if available
        if self.spotdl_app.is_online:
            try:
                songs = await self.spotdl_app.api_client.resolve_url(url)
                self._results = songs
                self._update_table()
                return
            except APIError as e:
                logger.warning(f"Online URL resolution failed: {e}")

        # Offline: use local providers for supported URLs
        from spotdl_cli.core.offline import is_supported_url

        if is_supported_url(url):
            await self._resolve_offline_url(url)
        elif "youtube.com" in url or "youtu.be" in url:
            await self._resolve_youtube_url(url)
        else:
            self.notify(
                "URL not supported in offline mode",
                severity="warning",
            )

    async def _resolve_offline_url(self, url: str) -> None:
        """Resolve any supported URL using offline providers."""
        try:
            songs = await self._offline_matcher.resolve_url(url)
            if songs:
                self._results = songs
                self._update_table()
            else:
                self.notify("No songs found at URL", severity="warning")
        except Exception as e:
            logger.exception("Offline URL resolution failed")
            self.notify(f"Failed to resolve URL: {e}", severity="error")

    async def _resolve_youtube_url(self, url: str) -> None:
        """Resolve a YouTube URL to a song (offline mode)."""
        import yt_dlp

        options = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                self.notify("Could not extract video info", severity="error")
                return

            # Handle playlist
            if "entries" in info:
                songs = []
                for entry in info.get("entries", []):
                    if entry:
                        song = self._yt_entry_to_song(entry)
                        if song:
                            songs.append(song)
                self._results = songs
            else:
                # Single video
                song = self._yt_entry_to_song(info)
                if song:
                    self._results = [song]
                else:
                    self._results = []

            self._update_table()

        except Exception as e:
            logger.exception("YouTube URL resolution failed")
            self.notify(f"Failed to resolve URL: {e}", severity="error")

    def _yt_entry_to_song(self, entry: dict) -> Song | None:
        """Convert yt-dlp entry to Song object."""
        try:
            video_id = entry.get("id", "")
            title = entry.get("title", "")
            duration = entry.get("duration", 0) or 0
            channel = entry.get("channel", "") or entry.get("uploader", "") or "Unknown"

            if not video_id or not title:
                return None

            # Try to parse artist - title format
            artist = channel
            name = title
            if " - " in title:
                parts = title.split(" - ", 1)
                artist = parts[0].strip()
                name = parts[1].strip()

            return Song(
                name=name,
                artists=[artist],
                artist=artist,
                duration=int(duration),
                platform=Platform.YOUTUBE_MUSIC,
                platform_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                album_name=entry.get("album", ""),
                cover_url=entry.get("thumbnail"),
            )
        except Exception as e:
            logger.warning(f"Failed to convert entry to song: {e}")
            return None

    async def _search_songs(self, query: str) -> None:
        """Search for songs (online or offline)."""
        # Try online first if available
        if self.spotdl_app.is_online:
            try:
                songs = await self.spotdl_app.api_client.search(query)
                self._results = songs
                self._update_table()
                return
            except APIError as e:
                logger.warning(f"Online search failed, falling back to offline: {e}")

        # Offline search using yt-dlp
        await self._search_offline(query)

    async def _search_offline(self, query: str) -> None:
        """Search using offline providers (Deezer, YouTube, YouTube Music)."""
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("Searching across platforms...")

        try:
            # Search across all available platforms
            songs = await self._offline_matcher.search_all(query, limit=10)

            if not songs:
                # Fall back to YouTube search only
                status_bar.update("Searching YouTube...")
                yt_results = await self._offline_matcher.search_youtube(query, limit=10)

                for result in yt_results:
                    song = self._result_to_song(result)
                    songs.append(song)

            self._results = songs[:20]  # Limit to 20 results
            self._update_table()

        except Exception as e:
            logger.exception("Offline search failed")
            self.notify(f"Search failed: {e}", severity="error")

    def _result_to_song(self, result: DownloadResult) -> Song:
        """Convert a DownloadResult to a Song for display."""
        # Try to parse title for better artist/name extraction
        name = result.name
        artist = result.artist
        artists = result.artists

        # Check if title contains "Artist - Song" format
        if " - " in result.name and not result.verified:
            parts = result.name.split(" - ", 1)
            if len(parts) == 2:
                potential_artist = parts[0].strip()
                potential_name = parts[1].strip()
                # Only use if the potential artist seems reasonable
                if len(potential_artist) < 50:
                    artist = potential_artist
                    artists = [potential_artist]
                    name = potential_name

        return Song(
            name=name,
            artists=artists,
            artist=artist,
            duration=result.duration,
            platform=Platform.YOUTUBE_MUSIC,  # Mark as YTM for display
            platform_id=result.platform_id,
            url=result.url,
            album_name=result.album_name or "",
            cover_url=result.cover_url,
        )

    def _update_table(self) -> None:
        """Update the results table."""
        table = self.query_one("#results-table", DataTable)
        table.clear()

        for song in self._results:
            duration = f"{song.duration // 60}:{song.duration % 60:02d}"
            table.add_row(
                song.name[:50] + "..." if len(song.name) > 50 else song.name,
                song.artist[:30] + "..." if len(song.artist) > 30 else song.artist,
                (song.album_name[:20] + "..." if song.album_name and len(song.album_name) > 20
                 else song.album_name) or "-",
                duration,
                song.platform.value,
            )

    def _clear_results(self) -> None:
        """Clear search results."""
        self._results = []
        table = self.query_one("#results-table", DataTable)
        table.clear()
        self.query_one("#status-bar", Static).update("Cleared")

    async def _add_selected(self) -> None:
        """Add selected song to download queue."""
        table = self.query_one("#results-table", DataTable)

        if table.cursor_row is None:
            self.notify("No song selected", severity="warning")
            return

        if table.cursor_row >= len(self._results):
            return

        song = self._results[table.cursor_row]
        await self._add_song_to_queue(song)

    async def _add_all(self) -> None:
        """Add all songs to download queue."""
        if not self._results:
            self.notify("No songs to add", severity="warning")
            return

        count = 0
        for song in self._results:
            await self._add_song_to_queue(song, notify=False)
            count += 1

        self.notify(f"Added {count} songs to queue", severity="information")

    async def _add_song_to_queue(self, song: Song, notify: bool = True) -> None:
        """Add a song to the download queue."""
        queue = self.spotdl_app.download_queue

        # Find matches - try online first, then offline
        result = None

        if self.spotdl_app.is_online:
            try:
                matches = await self.spotdl_app.api_client.find_matches(song)
                if matches:
                    result = matches[0]
            except APIError as e:
                logger.warning(f"Online match finding failed: {e}")

        # If no result from online, use offline matching
        if result is None:
            try:
                result = await self._offline_matcher.get_best_match(song, min_score=60.0)
            except Exception as e:
                logger.warning(f"Offline match finding failed: {e}")

        # If still no result but song is from YouTube, create result from song
        if result is None and "youtube.com" in song.url:
            from spotdl_cli.core.types import TargetPlatform
            result = DownloadResult(
                name=song.name,
                artists=song.artists,
                artist=song.artist,
                duration=song.duration,
                platform=TargetPlatform.YOUTUBE,
                platform_id=song.platform_id,
                url=song.url,
                verified=False,
                score=100.0,  # Direct match
                cover_url=song.cover_url,
            )

        await queue.add(song, result=result)

        if notify:
            status = "with match" if result else "pending match"
            self.notify(f"Added: {song.display_name} ({status})")

    def action_search(self) -> None:
        """Action to trigger search."""
        self.run_worker(self._do_search())

    def action_add_all(self) -> None:
        """Action to add all songs."""
        self.run_worker(self._add_all())

    def action_refresh(self) -> None:
        """Action to refresh search."""
        self.run_worker(self._do_search())
