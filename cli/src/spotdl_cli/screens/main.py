"""Main search screen for SpotDL CLI.

Matches frontend layout with:
- Universal search returning all entity types
- Filter tabs (All, Songs, Artists, Albums, Playlists)
- Entity-specific result sections
- Lazy loading with "Load More" buttons
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
from spotdl_cli.core.types import PlatformInfo, Platform, Song
from spotdl_cli.theme import truncate as _truncate
from spotdl_cli.widgets import CoverArt

# Regex for sanitizing strings into valid Textual CSS identifiers
import re
_ID_INVALID = re.compile(r"[^a-zA-Z0-9_-]")


def _sanitize_id(text: str) -> str:
    """Convert arbitrary text to a valid Textual widget ID."""
    return _ID_INVALID.sub("-", text).strip("-") or "unknown"

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

# Display limits (lazy loading)
INITIAL_DISPLAY_LIMIT = {
    EntityType.ARTIST: 6,
    EntityType.ALBUM: 8,
    EntityType.TRACK: 10,
    EntityType.PLAYLIST: 6,
}

LOAD_MORE_INCREMENT = {
    EntityType.ARTIST: 6,
    EntityType.ALBUM: 8,
    EntityType.TRACK: 10,
    EntityType.PLAYLIST: 6,
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
        # Track display counts for lazy loading
        self._display_counts: dict[EntityType, int] = {
            EntityType.ARTIST: INITIAL_DISPLAY_LIMIT[EntityType.ARTIST],
            EntityType.ALBUM: INITIAL_DISPLAY_LIMIT[EntityType.ALBUM],
            EntityType.TRACK: INITIAL_DISPLAY_LIMIT[EntityType.TRACK],
            EntityType.PLAYLIST: INITIAL_DISPLAY_LIMIT[EntityType.PLAYLIST],
        }
        # Cache songs from offline search for navigation
        self._offline_songs: dict[str, Song] = {}

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

                    with Vertical(id="artists-list", classes="entity-list"):
                        pass  # Populated dynamically

                    yield Button(
                        "Load More Artists",
                        id="load-more-artists",
                        classes="load-more-btn hidden",
                    )

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

                    yield Button(
                        "Load More Albums",
                        id="load-more-albums",
                        classes="load-more-btn hidden",
                    )

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

                    yield Button(
                        "Load More Songs",
                        id="load-more-tracks",
                        classes="load-more-btn hidden",
                    )

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

                    yield Button(
                        "Load More Playlists",
                        id="load-more-playlists",
                        classes="load-more-btn hidden",
                    )

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
        elif button_id and button_id.startswith("load-more-"):
            entity_type_str = button_id.replace("load-more-", "")
            await self._load_more(entity_type_str)
        elif button_id and button_id.startswith("entity-"):
            # Handle entity card click
            await self._handle_entity_click(button_id)

    def _set_active_filter(self, filter_type: str) -> None:
        """Set the active filter and update display."""
        if self._active_filter == filter_type:
            return  # No change needed

        # Update only the affected buttons (optimization)
        old_btn = self.query_one(f"#filter-{self._active_filter}", Button)
        old_btn.remove_class("active")

        new_btn = self.query_one(f"#filter-{filter_type}", Button)
        new_btn.add_class("active")

        self._active_filter = filter_type

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

        # Reset display counts for new search
        for entity_type in EntityType:
            self._display_counts[entity_type] = INITIAL_DISPLAY_LIMIT[entity_type]

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
        """Search using offline providers, deriving artists/albums from tracks."""
        offline_matcher = get_offline_matcher()

        # Search across all platforms
        songs = await offline_matcher.search_all(query, limit=20)

        results: list[EntityResult] = []
        seen_artists: dict[str, EntityResult] = {}
        seen_albums: dict[str, EntityResult] = {}

        for song in songs:
            # Cache the full Song object for later use in detail screens
            self._offline_songs[song.platform_id] = song

            # Track entity
            results.append(EntityResult(
                id=song.platform_id,
                entity_type=EntityType.TRACK,
                name=song.name,
                subtitle=song.artist,
                image_url=song.cover_url,
                platforms=[PlatformInfo(
                    platform=song.platform.value,
                    platform_id=song.platform_id,
                    url=song.url,
                )],
                duration=song.duration,
            ))

            # Derive artist entity (deduplicate by lowercase name)
            artist_key = song.artist.lower().strip()
            if artist_key and artist_key not in seen_artists:
                safe_artist_id = _sanitize_id(f"offline-artist-{artist_key}")
                seen_artists[artist_key] = EntityResult(
                    id=safe_artist_id,
                    entity_type=EntityType.ARTIST,
                    name=song.artist,
                    image_url=song.cover_url,
                    platforms=[PlatformInfo(
                        platform=song.platform.value,
                        platform_id=song.artist_id or song.artist,
                        url=song.url,
                    )],
                )

            # Derive album entity (deduplicate by artist+album)
            if song.album_name:
                album_key = f"{artist_key}|{song.album_name.lower().strip()}"
                if album_key not in seen_albums:
                    safe_album_id = _sanitize_id(f"offline-album-{artist_key}-{song.album_name.lower().strip()}")
                    seen_albums[album_key] = EntityResult(
                        id=safe_album_id,
                        entity_type=EntityType.ALBUM,
                        name=song.album_name,
                        subtitle=song.artist,
                        image_url=song.cover_url,
                        platforms=[PlatformInfo(
                            platform=song.platform.value,
                            platform_id=song.album_id or song.album_name,
                            url=song.url,
                        )],
                    )

        # Combine: artists first, then albums, then tracks
        all_results = (
            list(seen_artists.values())
            + list(seen_albums.values())
            + results
        )

        return UniversalSearchResponse(
            query=query,
            query_type="text",
            results=all_results,
            entities_created=0,
            total=len(all_results),
        )

    def _display_results(self, response: UniversalSearchResponse) -> None:
        """Display search results grouped by entity type."""
        # Clear existing results
        self._clear_results()

        if not response.results:
            self.query_one("#no-results", Vertical).remove_class("hidden")
            return

        # Display each entity type with lazy loading
        if response.artists:
            self._display_entity_section(
                EntityType.ARTIST, response.artists, "artists"
            )

        if response.albums:
            self._display_entity_section(
                EntityType.ALBUM, response.albums, "albums"
            )

        if response.tracks:
            self._display_entity_section(
                EntityType.TRACK, response.tracks, "tracks"
            )

        if response.playlists:
            self._display_entity_section(
                EntityType.PLAYLIST, response.playlists, "playlists"
            )

        # Update section visibility based on filter
        self._update_section_visibility()

    def _clear_results(self) -> None:
        """Clear all result sections."""
        for section_id in ["artists-list", "albums-list", "tracks-list", "playlists-list"]:
            container = self.query_one(f"#{section_id}")
            container.remove_children()

        # Hide all sections and load more buttons
        for section_id in [
            "artists-section", "albums-section", "tracks-section", "playlists-section"
        ]:
            self.query_one(f"#{section_id}", Vertical).add_class("hidden")

        for btn_id in [
            "load-more-artists", "load-more-albums", "load-more-tracks", "load-more-playlists"
        ]:
            self.query_one(f"#{btn_id}", Button).add_class("hidden")

    def _display_entity_section(
        self,
        entity_type: EntityType,
        entities: list[EntityResult],
        section_name: str,
    ) -> None:
        """Display a section of entities with lazy loading."""
        section = self.query_one(f"#{section_name}-section", Vertical)
        container = self.query_one(f"#{section_name}-list", Vertical)
        count_label = self.query_one(f"#{section_name}-count", Static)
        load_more_btn = self.query_one(f"#load-more-{section_name}", Button)

        count_label.update(f"({len(entities)})")

        # Get display limit
        display_limit = self._display_counts[entity_type]
        entities_to_show = entities[:display_limit]

        # Create cards in batch
        cards: list[Container] = []
        for entity in entities_to_show:
            if entity_type == EntityType.ARTIST:
                card = self._create_artist_card(entity)
            else:
                card = self._create_entity_card(entity, entity_type)
            cards.append(card)

        # Batch mount all cards at once (much faster than individual mounts)
        container.mount(*cards)

        # Show/hide load more button
        if len(entities) > display_limit:
            load_more_btn.remove_class("hidden")
        else:
            load_more_btn.add_class("hidden")

        section.remove_class("hidden")

    async def _load_more(self, entity_type_str: str) -> None:
        """Load more entities for a section."""
        if not self._search_response:
            return

        # Map string to entity type and data
        type_map = {
            "artists": (EntityType.ARTIST, self._search_response.artists, "artists"),
            "albums": (EntityType.ALBUM, self._search_response.albums, "albums"),
            "tracks": (EntityType.TRACK, self._search_response.tracks, "tracks"),
            "playlists": (EntityType.PLAYLIST, self._search_response.playlists, "playlists"),
        }

        if entity_type_str not in type_map:
            return

        entity_type, entities, section_name = type_map[entity_type_str]

        # Update display count
        old_limit = self._display_counts[entity_type]
        new_limit = old_limit + LOAD_MORE_INCREMENT[entity_type]
        self._display_counts[entity_type] = new_limit

        # Get new entities to show
        new_entities = entities[old_limit:new_limit]

        if not new_entities:
            return

        # Create and mount new cards
        container = self.query_one(f"#{section_name}-list", Vertical)
        cards: list[Container] = []
        for entity in new_entities:
            if entity_type == EntityType.ARTIST:
                card = self._create_artist_card(entity)
            else:
                card = self._create_entity_card(entity, entity_type)
            cards.append(card)

        container.mount(*cards)

        # Hide load more if no more entities
        load_more_btn = self.query_one(f"#load-more-{section_name}", Button)
        if new_limit >= len(entities):
            load_more_btn.add_class("hidden")

    def _create_artist_card(self, artist: EntityResult) -> Container:
        """Create an artist card for display."""
        platform_badges = self._get_platform_badges(artist)
        cover = CoverArt(classes="card-cover card-cover-small")
        cover.cover_url = artist.image_url
        safe_id = _sanitize_id(artist.id)

        card = Horizontal(
            cover,
            Vertical(
                Horizontal(
                    Static("ARTIST", classes="badge badge-artist"),
                    Static(platform_badges, classes="platform-badges"),
                    classes="card-meta-row",
                ),
                Static(
                    f"[bold]{_truncate(artist.name, 30)}[/bold]",
                    classes="card-title",
                ),
                classes="card-info",
            ),
            Button("View", id=f"entity-artist-{safe_id}", classes="card-action"),
            classes="entity-card",
            id=f"artist-card-{safe_id}",
        )
        return card

    def _create_entity_card(
        self, entity: EntityResult, entity_type: EntityType
    ) -> Container:
        """Create an entity card for list display."""
        platform_badges = self._get_platform_badges(entity)
        cover = CoverArt(classes="card-cover card-cover-small")
        cover.cover_url = entity.image_url
        safe_id = _sanitize_id(entity.id)

        # Build info line
        info_parts = []
        if entity.subtitle:
            info_parts.append(entity.subtitle)
        if entity.duration:
            info_parts.append(entity.duration_str)
        info_line = " • ".join(info_parts) if info_parts else ""

        # Type label
        type_labels = {
            EntityType.TRACK: "SONG",
            EntityType.ALBUM: "ALBUM",
            EntityType.PLAYLIST: "PLAYLIST",
        }
        type_label = type_labels.get(entity_type, entity_type.value.upper())
        badge_class = f"badge badge-{entity_type.value}"

        card = Horizontal(
            cover,
            Vertical(
                Horizontal(
                    Static(type_label, classes=badge_class),
                    Static(platform_badges, classes="platform-badges"),
                    classes="card-meta-row",
                ),
                Static(
                    f"[bold]{_truncate(entity.name, 40)}[/bold]",
                    classes="card-title",
                ),
                Static(
                    f"[dim]{_truncate(info_line, 50)}[/dim]",
                    classes="card-subtitle",
                ) if info_line else Static(""),
                classes="card-info",
            ),
            Button("View", id=f"entity-{entity_type.value}-{safe_id}", classes="card-action"),
            Button("Download", id=f"dl-{entity_type.value}-{safe_id}", classes="card-action"),
            classes="entity-card",
            id=f"card-{entity_type.value}-{safe_id}",
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
        from spotdl_cli.screens.album import AlbumScreen
        from spotdl_cli.screens.artist import ArtistScreen
        from spotdl_cli.screens.playlist import PlaylistScreen
        from spotdl_cli.screens.track import TrackScreen

        try:
            entity_type = EntityType(entity_type_str)
        except ValueError:
            return

        entity = self._find_entity(entity_id)
        if not entity or not entity.primary_platform:
            return

        pp = entity.primary_platform

        if entity_type == EntityType.TRACK:
            # Use cached Song from offline search if available
            song = self._offline_songs.get(pp.platform_id)
            if song is None:
                song = Song(
                    name=entity.name,
                    artists=[entity.subtitle or "Unknown"],
                    artist=entity.subtitle or "Unknown",
                    duration=entity.duration or 0,
                    platform=Platform(pp.platform),
                    platform_id=pp.platform_id,
                    url=pp.url,
                    cover_url=entity.image_url,
                )
            await self.app.push_screen(
                TrackScreen(song, pp.platform_id, pp.platform)
            )

        elif entity_type == EntityType.ALBUM:
            # For offline-derived albums, pass name and artist for search
            initial_data = None
            if not self.spotdl_app.is_online:
                initial_data = {"name": entity.name}
                if entity.subtitle:
                    initial_data["artist"] = entity.subtitle
            await self.app.push_screen(
                AlbumScreen(pp.platform_id, pp.platform, initial_data=initial_data)
            )

        elif entity_type == EntityType.ARTIST:
            # For offline-derived artists, pass the name for search
            await self.app.push_screen(
                ArtistScreen(
                    pp.platform_id, pp.platform,
                    initial_data={"name": entity.name} if not self.spotdl_app.is_online else None,
                )
            )

        elif entity_type == EntityType.PLAYLIST:
            initial_data = None
            if not self.spotdl_app.is_online:
                initial_data = {"name": entity.name}
            await self.app.push_screen(
                PlaylistScreen(pp.platform_id, pp.platform, initial_data=initial_data)
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
            pp = entity.primary_platform
            song = self._offline_songs.get(pp.platform_id)
            if song is None:
                song = Song(
                    name=entity.name,
                    artists=[entity.subtitle or "Unknown"],
                    artist=entity.subtitle or "Unknown",
                    duration=entity.duration or 0,
                    platform=Platform(pp.platform),
                    platform_id=pp.platform_id,
                    url=pp.url,
                    cover_url=entity.image_url,
                )
            await self.spotdl_app.download_queue.add(song)
            self.notify(f"Added to queue: {entity.name}")
        else:
            await self._view_entity(entity_type_str, entity_id)

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
