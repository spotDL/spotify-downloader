"""Main search screen for SpotDL CLI.

Matches frontend layout with:
- Universal search returning all entity types
- Filter tabs (All, Songs, Artists, Albums, Playlists)
- Entity-specific result sections
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Rule,
    Static,
)

from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIError,
    EntityResult,
    EntityType,
    UniversalSearchResponse,
    get_api_client,
    get_offline_matcher,
)

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)

# Color scheme by entity type (matching frontend)
ENTITY_COLORS = {
    EntityType.ARTIST: "#ffd93d",  # accent-needle (golden)
    EntityType.ALBUM: "#4ecdc4",  # accent-cool (blue/teal)
    EntityType.TRACK: "#00d084",  # accent-safe (green)
    EntityType.PLAYLIST: "#ff6b35",  # accent-warm (orange)
}

ENTITY_ICONS = {
    EntityType.ARTIST: "👤",
    EntityType.ALBUM: "💿",
    EntityType.TRACK: "🎵",
    EntityType.PLAYLIST: "📋",
}


class MainScreen(Screen[None]):
    """Main search screen matching frontend layout."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "submit_search", "Search", show=False),
        Binding("tab", "next_filter", "Next Filter", show=False),
        Binding("1", "filter_all", "All", show=False),
        Binding("2", "filter_tracks", "Tracks", show=False),
        Binding("3", "filter_artists", "Artists", show=False),
        Binding("4", "filter_albums", "Albums", show=False),
        Binding("5", "filter_playlists", "Playlists", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._settings = get_settings()
        self._search_response: UniversalSearchResponse | None = None
        self._active_filter: str = "all"
        self._filter_buttons: list[str] = [
            "all", "track", "artist", "album", "playlist"
        ]

    @property
    def spotdl_app(self) -> SpotDLApp:
        """Get the typed app instance."""
        from spotdl_cli.app import SpotDLApp

        assert isinstance(self.app, SpotDLApp)
        return self.app

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with VerticalScroll(id="main-container"):
            # Search header section
            with Vertical(id="search-header"):
                yield Static("Search", id="page-title", classes="title-xl")

                # Search form
                with Horizontal(id="search-form"):
                    yield Input(
                        placeholder="Search for songs, artists, albums, or paste a URL...",
                        id="search-input",
                    )
                    yield Button("Search", id="search-btn", variant="primary")

                # Status bar
                yield Static("", id="status-bar", classes="status-muted")

            # Filter tabs
            with Horizontal(id="filter-tabs"):
                yield Button("All", id="filter-all", classes="filter-btn active")
                yield Button("Songs", id="filter-track", classes="filter-btn")
                yield Button("Artists", id="filter-artist", classes="filter-btn")
                yield Button("Albums", id="filter-album", classes="filter-btn")
                yield Button("Playlists", id="filter-playlist", classes="filter-btn")

            yield Rule()

            # Results container
            with Vertical(id="results-container"):
                # Empty state (shown before search)
                with Vertical(id="empty-state"):
                    yield Static(
                        "🔍 Enter a search query above",
                        id="empty-title",
                        classes="empty-message",
                    )
                    yield Static(
                        "Search for artists, albums, tracks, or playlists\n"
                        "You can also paste URLs from Spotify, YouTube, etc.",
                        id="empty-subtitle",
                        classes="empty-hint",
                    )

                # Artists section
                with Vertical(id="artists-section", classes="entity-section hidden"):
                    with Horizontal(classes="section-header"):
                        yield Static(
                            f"{ENTITY_ICONS[EntityType.ARTIST]} Artists",
                            classes="section-title artist-color",
                        )
                        yield Static("", id="artists-count", classes="section-count")

                    with Horizontal(id="artists-grid", classes="entity-grid"):
                        pass  # Populated dynamically

                # Albums section
                with Vertical(id="albums-section", classes="entity-section hidden"):
                    with Horizontal(classes="section-header"):
                        yield Static(
                            f"{ENTITY_ICONS[EntityType.ALBUM]} Albums",
                            classes="section-title album-color",
                        )
                        yield Static("", id="albums-count", classes="section-count")

                    with Vertical(id="albums-list", classes="entity-list"):
                        pass  # Populated dynamically

                # Tracks section
                with Vertical(id="tracks-section", classes="entity-section hidden"):
                    with Horizontal(classes="section-header"):
                        yield Static(
                            f"{ENTITY_ICONS[EntityType.TRACK]} Songs",
                            classes="section-title track-color",
                        )
                        yield Static("", id="tracks-count", classes="section-count")

                    with Vertical(id="tracks-list", classes="entity-list"):
                        pass  # Populated dynamically

                # Playlists section
                with Vertical(id="playlists-section", classes="entity-section hidden"):
                    with Horizontal(classes="section-header"):
                        yield Static(
                            f"{ENTITY_ICONS[EntityType.PLAYLIST]} Playlists",
                            classes="section-title playlist-color",
                        )
                        yield Static("", id="playlists-count", classes="section-count")

                    with Vertical(id="playlists-list", classes="entity-list"):
                        pass  # Populated dynamically

                # No results state
                with Vertical(id="no-results", classes="hidden"):
                    yield Static(
                        "No results found",
                        classes="empty-message",
                    )
                    yield Static(
                        "Try a different search query",
                        classes="empty-hint",
                    )

    async def on_mount(self) -> None:
        """Handle screen mount."""
        self.query_one("#search-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            await self._do_search()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "search-btn":
            await self._do_search()
        elif button_id and button_id.startswith("filter-"):
            filter_type = button_id.replace("filter-", "")
            self._set_active_filter(filter_type)
        elif button_id and button_id.startswith("entity-"):
            # Handle entity card click
            await self._handle_entity_click(button_id)

    def _set_active_filter(self, filter_type: str) -> None:
        """Set the active filter and update display."""
        self._active_filter = filter_type

        # Update button states
        for btn_type in self._filter_buttons:
            btn = self.query_one(f"#filter-{btn_type}", Button)
            if btn_type == filter_type:
                btn.add_class("active")
            else:
                btn.remove_class("active")

        # Update visible sections
        self._update_section_visibility()

    def _update_section_visibility(self) -> None:
        """Update which sections are visible based on filter."""
        if not self._search_response:
            return

        sections = {
            "artist": ("artists-section", self._search_response.artists),
            "album": ("albums-section", self._search_response.albums),
            "track": ("tracks-section", self._search_response.tracks),
            "playlist": ("playlists-section", self._search_response.playlists),
        }

        for entity_type, (section_id, results) in sections.items():
            section = self.query_one(f"#{section_id}", Vertical)

            if self._active_filter == "all":
                # Show section if it has results
                if results:
                    section.remove_class("hidden")
                else:
                    section.add_class("hidden")
            elif self._active_filter == entity_type:
                # Show only this section if it has results
                if results:
                    section.remove_class("hidden")
                else:
                    section.add_class("hidden")
            else:
                section.add_class("hidden")

    async def _do_search(self) -> None:
        """Perform universal search."""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.strip()

        if not query:
            self.notify("Please enter a search query", severity="warning")
            return

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("Searching...")

        # Hide empty state
        self.query_one("#empty-state", Vertical).add_class("hidden")
        self.query_one("#no-results", Vertical).add_class("hidden")

        try:
            # Try online search first
            if self.spotdl_app.is_online:
                response = await self._search_online(query)
            else:
                response = await self._search_offline(query)

            self._search_response = response
            self._display_results(response)

            # Update status
            total = response.total
            status_bar.update(
                f"Found {total} result{'s' if total != 1 else ''} "
                f"({'online' if self.spotdl_app.is_online else 'offline'})"
            )

        except APIError as e:
            status_bar.update(f"Error: {e}")
            self.notify(str(e), severity="error")
        except Exception as e:
            logger.exception("Search failed")
            status_bar.update(f"Error: {e}")
            self.notify(f"Search failed: {e}", severity="error")

    async def _search_online(self, query: str) -> UniversalSearchResponse:
        """Search using the API server."""
        api_client = get_api_client()
        return await api_client.universal_search(query, limit=30)

    async def _search_offline(self, query: str) -> UniversalSearchResponse:
        """Search using offline providers."""
        offline_matcher = get_offline_matcher()

        # Search across platforms
        songs = await offline_matcher.search_all(query, limit=20)

        # Convert to EntityResults
        results: list[EntityResult] = []
        for song in songs:
            from spotdl_cli.core.types import PlatformInfo

            result = EntityResult(
                id=song.platform_id,
                entity_type=EntityType.TRACK,
                name=song.name,
                subtitle=song.artist,
                image_url=song.cover_url,
                platforms=[
                    PlatformInfo(
                        platform=song.platform.value,
                        platform_id=song.platform_id,
                        url=song.url,
                    )
                ],
                duration=song.duration,
            )
            results.append(result)

        return UniversalSearchResponse(
            query=query,
            query_type="text",
            results=results,
            entities_created=0,
            total=len(results),
        )

    def _display_results(self, response: UniversalSearchResponse) -> None:
        """Display search results grouped by entity type."""
        # Clear existing results
        self._clear_results()

        if not response.results:
            self.query_one("#no-results", Vertical).remove_class("hidden")
            return

        # Display artists
        if response.artists:
            self._display_artists(response.artists)

        # Display albums
        if response.albums:
            self._display_albums(response.albums)

        # Display tracks
        if response.tracks:
            self._display_tracks(response.tracks)

        # Display playlists
        if response.playlists:
            self._display_playlists(response.playlists)

        # Update section visibility based on filter
        self._update_section_visibility()

    def _clear_results(self) -> None:
        """Clear all result sections."""
        for section_id in ["artists-grid", "albums-list", "tracks-list", "playlists-list"]:
            container = self.query_one(f"#{section_id}")
            container.remove_children()

        # Hide all sections
        for section_id in [
            "artists-section", "albums-section", "tracks-section", "playlists-section"
        ]:
            self.query_one(f"#{section_id}", Vertical).add_class("hidden")

    def _display_artists(self, artists: list[EntityResult]) -> None:
        """Display artist results in horizontal grid."""
        section = self.query_one("#artists-section", Vertical)
        grid = self.query_one("#artists-grid", Horizontal)
        count = self.query_one("#artists-count", Static)

        count.update(f"({len(artists)})")

        for artist in artists[:10]:  # Limit to 10
            card = self._create_artist_card(artist)
            grid.mount(card)

        section.remove_class("hidden")

    def _display_albums(self, albums: list[EntityResult]) -> None:
        """Display album results in list."""
        section = self.query_one("#albums-section", Vertical)
        container = self.query_one("#albums-list", Vertical)
        count = self.query_one("#albums-count", Static)

        count.update(f"({len(albums)})")

        for album in albums[:12]:  # Limit to 12
            card = self._create_entity_card(album, EntityType.ALBUM)
            container.mount(card)

        section.remove_class("hidden")

    def _display_tracks(self, tracks: list[EntityResult]) -> None:
        """Display track results in list."""
        section = self.query_one("#tracks-section", Vertical)
        container = self.query_one("#tracks-list", Vertical)
        count = self.query_one("#tracks-count", Static)

        count.update(f"({len(tracks)})")

        for track in tracks[:15]:  # Limit to 15
            card = self._create_entity_card(track, EntityType.TRACK)
            container.mount(card)

        section.remove_class("hidden")

    def _display_playlists(self, playlists: list[EntityResult]) -> None:
        """Display playlist results in list."""
        section = self.query_one("#playlists-section", Vertical)
        container = self.query_one("#playlists-list", Vertical)
        count = self.query_one("#playlists-count", Static)

        count.update(f"({len(playlists)})")

        for playlist in playlists[:10]:  # Limit to 10
            card = self._create_entity_card(playlist, EntityType.PLAYLIST)
            container.mount(card)

        section.remove_class("hidden")

    def _create_artist_card(self, artist: EntityResult) -> Container:
        """Create an artist card for horizontal display."""
        platform_badges = self._get_platform_badges(artist)

        card = Vertical(
            Static(f"[bold]{self._truncate(artist.name, 15)}[/bold]", classes="card-name"),
            Static(platform_badges, classes="platform-badges"),
            Button("View", id=f"entity-artist-{artist.id}", classes="card-action"),
            classes="artist-card",
            id=f"artist-card-{artist.id}",
        )
        return card

    def _create_entity_card(
        self, entity: EntityResult, entity_type: EntityType
    ) -> Container:
        """Create an entity card for list display."""
        icon = ENTITY_ICONS.get(entity_type, "●")
        platform_badges = self._get_platform_badges(entity)

        # Build info line
        info_parts = []
        if entity.subtitle:
            info_parts.append(entity.subtitle)
        if entity.duration:
            info_parts.append(entity.duration_str)

        info_line = " • ".join(info_parts) if info_parts else ""

        # Determine color class
        color_class = f"{entity_type.value}-color"

        card = Horizontal(
            Static(icon, classes=f"entity-icon {color_class}"),
            Vertical(
                Static(
                    f"[bold]{self._truncate(entity.name, 40)}[/bold]",
                    classes="card-title",
                ),
                Static(
                    f"[dim]{self._truncate(info_line, 50)}[/dim]",
                    classes="card-subtitle",
                ),
                Static(platform_badges, classes="platform-badges"),
                classes="card-info",
            ),
            Button("View", id=f"entity-{entity_type.value}-{entity.id}", classes="card-action"),
            Button("Download", id=f"dl-{entity_type.value}-{entity.id}", classes="card-action"),
            classes="entity-card",
            id=f"card-{entity_type.value}-{entity.id}",
        )
        return card

    def _get_platform_badges(self, entity: EntityResult) -> str:
        """Get platform badge string for an entity."""
        platform_icons = {
            "spotify": "[green]●[/green]",
            "youtube_music": "[red]●[/red]",
            "youtube": "[red]●[/red]",
            "deezer": "[magenta]●[/magenta]",
            "soundcloud": "[#ff5500]●[/#ff5500]",
            "apple_music": "[#fc3c44]●[/#fc3c44]",
            "tidal": "[white]●[/white]",
            "bandcamp": "[cyan]●[/cyan]",
        }

        badges = []
        for pinfo in entity.platforms[:3]:  # Limit to 3 platforms
            icon = platform_icons.get(pinfo.platform, "●")
            badges.append(icon)

        return " ".join(badges) if badges else ""

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) > max_len:
            return text[: max_len - 3] + "..."
        return text

    async def _handle_entity_click(self, button_id: str) -> None:
        """Handle click on entity card."""
        # Parse button ID: entity-{type}-{id} or dl-{type}-{id}
        parts = button_id.split("-", 2)
        if len(parts) < 3:
            return

        action = parts[0]
        entity_type_str = parts[1]
        entity_id = parts[2]

        if action == "dl":
            # Download action
            await self._download_entity(entity_type_str, entity_id)
        else:
            # View action
            await self._view_entity(entity_type_str, entity_id)

    async def _view_entity(self, entity_type_str: str, entity_id: str) -> None:
        """Navigate to entity detail screen."""
        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            return

        if entity_type == EntityType.TRACK:
            from spotdl_cli.screens.track import TrackScreen
            from spotdl_cli.core.types import Song, Platform

            # Find the entity in results
            entity = self._find_entity(entity_id)
            if entity and entity.primary_platform:
                song = Song(
                    name=entity.name,
                    artists=[entity.subtitle or "Unknown"],
                    artist=entity.subtitle or "Unknown",
                    duration=entity.duration or 0,
                    platform=Platform(entity.primary_platform.platform),
                    platform_id=entity.primary_platform.platform_id,
                    url=entity.primary_platform.url,
                )
                await self.app.push_screen(
                    TrackScreen(song, entity.id, entity.primary_platform.platform)
                )

        elif entity_type == EntityType.ALBUM:
            from spotdl_cli.screens.album import AlbumScreen

            entity = self._find_entity(entity_id)
            if entity and entity.primary_platform:
                await self.app.push_screen(
                    AlbumScreen(
                        entity.primary_platform.platform_id,
                        entity.primary_platform.platform,
                    )
                )

        elif entity_type == EntityType.ARTIST:
            from spotdl_cli.screens.artist import ArtistScreen

            entity = self._find_entity(entity_id)
            if entity and entity.primary_platform:
                await self.app.push_screen(
                    ArtistScreen(
                        entity.primary_platform.platform_id,
                        entity.primary_platform.platform,
                    )
                )

        elif entity_type == EntityType.PLAYLIST:
            from spotdl_cli.screens.playlist import PlaylistScreen

            entity = self._find_entity(entity_id)
            if entity and entity.primary_platform:
                await self.app.push_screen(
                    PlaylistScreen(
                        entity.primary_platform.platform_id,
                        entity.primary_platform.platform,
                    )
                )

    async def _download_entity(self, entity_type_str: str, entity_id: str) -> None:
        """Add entity to download queue."""
        entity = self._find_entity(entity_id)
        if not entity:
            self.notify("Entity not found", severity="error")
            return

        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            return

        if entity_type == EntityType.TRACK and entity.primary_platform:
            from spotdl_cli.core.types import Song, Platform

            song = Song(
                name=entity.name,
                artists=[entity.subtitle or "Unknown"],
                artist=entity.subtitle or "Unknown",
                duration=entity.duration or 0,
                platform=Platform(entity.primary_platform.platform),
                platform_id=entity.primary_platform.platform_id,
                url=entity.primary_platform.url,
            )
            await self.spotdl_app.download_queue.add(song)
            self.notify(f"Added to queue: {entity.name}")
        else:
            # For albums/artists/playlists, navigate to detail screen
            await self._view_entity(entity_type_str, entity_id)
            self.notify("Navigate to view all tracks and download")

    def _find_entity(self, entity_id: str) -> EntityResult | None:
        """Find an entity by ID in the current results."""
        if not self._search_response:
            return None

        for result in self._search_response.results:
            if result.id == entity_id:
                return result
        return None

    def action_submit_search(self) -> None:
        """Submit search action."""
        self.run_worker(self._do_search())

    def action_next_filter(self) -> None:
        """Move to next filter."""
        current_idx = self._filter_buttons.index(self._active_filter)
        next_idx = (current_idx + 1) % len(self._filter_buttons)
        self._set_active_filter(self._filter_buttons[next_idx])

    def action_filter_all(self) -> None:
        """Filter: All."""
        self._set_active_filter("all")

    def action_filter_tracks(self) -> None:
        """Filter: Tracks."""
        self._set_active_filter("track")

    def action_filter_artists(self) -> None:
        """Filter: Artists."""
        self._set_active_filter("artist")

    def action_filter_albums(self) -> None:
        """Filter: Albums."""
        self._set_active_filter("album")

    def action_filter_playlists(self) -> None:
        """Filter: Playlists."""
        self._set_active_filter("playlist")
