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
    Collapsible,
    DataTable,
    Input,
    Rule,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from spotdl_cli.config import get_settings
from spotdl_cli.core import (
    APIError,
    DownloadResult,
    MatchEntry,
    Song,
    get_api_client,
    get_offline_matcher,
)
from spotdl_cli.core.types import Platform
from spotdl_cli.theme import get_platform_icon
from spotdl_cli.widgets import AudioMeter, CoverArt, MatchBar, StatChip

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp

logger = logging.getLogger(__name__)


class TrackScreen(Screen[None]):
    """Track detail screen matching frontend layout."""

    TITLE = "Track Detail"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("d", "download", "Download"),
        Binding("r", "refresh", "Refresh"),
        Binding("m", "refresh_metadata", "Refresh Metadata"),
        Binding("s", "submit_match", "Submit Match"),
        Binding("l", "submit_lyrics", "Submit Lyrics"),
        Binding("p", "report", "Report Data"),
        Binding("u", "vote_up", "Upvote Match"),
        Binding("n", "vote_down", "Downvote Match"),
    ]

    def __init__(
        self,
        song: Song,
        track_id: str | None = None,
        platform: str = "spotify",
        entity_id: str | None = None,
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
        self._entity_id = entity_id
        self._settings = get_settings()
        self._matches: list[MatchEntry] = []
        self._lyrics: str | None = None
        self._lyrics_sources_count: int | None = None
        self._all_lyrics: dict[str, str] = {}  # source -> lyrics text
        self._active_lyrics_source: str | None = None
        self._audio_features: dict[str, Any] = {}
        self._track_details: dict[str, Any] = {}
        self._snapshots: list[dict[str, Any]] = []
        # Track selected match index for voting
        self._selected_match_idx: int = 0

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
                    # Left: Cover art with entity_type
                    yield CoverArt(entity_type="track", id="track-cover", classes="cover-placeholder")

                    # Right: Track info
                    with Vertical(id="track-info"):
                        # Type label as small muted text
                        yield Static(
                            "[dim]TRACK[/dim]",
                            id="track-type-label",
                            classes="type-label-muted",
                        )

                        # Title
                        yield Static("", id="track-title", classes="title-xl")

                        # Artist (clickable)
                        yield Static("", id="track-artist", classes="subtitle link")

                        # Platform badges as subtle text
                        yield Static(
                            "", id="track-platform-badge", classes="platform-badge-subtle"
                        )

                        # Quick stats using StatChip widgets
                        with Horizontal(id="track-stats", classes="stats-row"):
                            yield StatChip("Duration", "--", id="stat-duration")
                            yield StatChip("Album", "--", id="stat-album")
                            yield StatChip("Year", "--", id="stat-year")
                            yield StatChip("Key", "--", id="stat-key")

                        # Badges row (explicit, track number)
                        with Horizontal(id="track-badges"):
                            yield Static(
                                "", id="explicit-badge", classes="badge badge-warning hidden"
                            )
                            yield Static("", id="track-number-badge", classes="badge badge-muted")

                        # Genres
                        with Horizontal(id="track-genres", classes="genre-row"):
                            pass  # Will be populated dynamically

                        # Action buttons: minimal toolbar row (no emoji)
                        with Horizontal(id="track-actions", classes="actions-row"):
                            yield Button(
                                "Download Best Match",
                                id="download-btn",
                                variant="primary",
                            )
                            yield Button("Refresh", id="refresh-btn", variant="default")
                            yield Button(
                                "Refresh Metadata",
                                id="refresh-meta-btn",
                                variant="default",
                            )
                            yield Button(
                                "Submit Match",
                                id="submit-match-btn",
                                variant="default",
                            )
                            yield Button(
                                "Report Data",
                                id="report-btn",
                                variant="default",
                            )

            # Main content: responsive 2-column split
            with Horizontal(id="track-content"):
                # Left column (2/3) — matches + lyrics
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
                            pass  # MatchBar widgets mounted dynamically

                        yield Static("", id="matches-status", classes="status-muted")

                    yield Rule()

                    # Inline match submission form
                    with Collapsible(title="Submit a Match", id="submit-match-form"):
                        with Horizontal(classes="setting-row"):
                            yield Select(
                                [
                                    ("YouTube", "youtube"),
                                    ("YouTube Music", "youtube_music"),
                                    ("SoundCloud", "soundcloud"),
                                    ("Bandcamp", "bandcamp"),
                                ],
                                value="youtube",
                                id="submit-platform-select",
                            )
                            yield Input(
                                placeholder="Paste match URL here",
                                id="submit-match-url",
                            )
                            yield Button("Submit", id="inline-submit-btn", variant="primary")

                    yield Rule()

                    # Lyrics card with tabbed multi-source display
                    with Vertical(classes="card", id="lyrics-card"):
                        with Horizontal(classes="card-header-row"):
                            yield Static("Lyrics", classes="card-title")
                            yield Button(
                                "Fetch All Sources",
                                id="fetch-all-lyrics-btn",
                                variant="default",
                            )
                            yield Button(
                                "Submit Lyrics",
                                id="submit-lyrics-btn",
                                variant="default",
                            )

                        with TabbedContent(id="lyrics-tabs"):
                            with TabPane("Default", id="lyrics-tab-default"):
                                with VerticalScroll(id="lyrics-container", classes="lyrics-scroll"):
                                    yield Static("", id="lyrics-content", classes="lyrics-text")

                        yield Static("", id="lyrics-status", classes="status-muted")

                    yield Rule()

                    # Metadata Sources card
                    with Collapsible(title="Metadata Sources", id="metadata-sources-section"):
                        yield DataTable(id="metadata-sources-table")
                        with Vertical(id="snapshot-detail-container"):
                            yield Static("", id="snapshot-detail-content", classes="status-muted")

                # Right column (1/3) — details + audio features
                with Vertical(id="track-sidebar", classes="sidebar-column"):
                    # Platform links
                    with Vertical(classes="card"):
                        yield Static("Platform Links", classes="card-title")
                        with Vertical(id="platform-links"):
                            yield Static("[dim]Loading...[/]", id="platform-links-content")

                    # Audio features using AudioMeter widgets
                    with Vertical(classes="card", id="audio-features-card"):
                        yield Static("Audio Features", classes="card-title")
                        with Vertical(id="audio-features-content"):
                            yield StatChip("BPM", "--", id="feature-bpm")
                            yield AudioMeter("Energy", 0.0, id="meter-energy")
                            yield AudioMeter("Danceability", 0.0, id="meter-danceability")
                            yield AudioMeter("Valence", 0.0, id="meter-valence")
                            yield AudioMeter("Speechiness", 0.0, id="meter-speechiness")
                            yield AudioMeter("Acousticness", 0.0, id="meter-acousticness")
                            yield AudioMeter("Instrumental", 0.0, id="meter-instrumentalness")
                            yield AudioMeter("Liveness", 0.0, id="meter-liveness")
                            yield StatChip("Loudness", "--", id="feature-loudness")
                            yield StatChip("Time Sig.", "--", id="feature-time-sig")

                    # Track details
                    with Vertical(classes="card", id="track-details-card"):
                        yield Static("Track Details", classes="card-title")
                        with Vertical(id="track-details-content"):
                            yield Static("[dim]ISRC:[/] --", id="detail-isrc", classes="detail-row")
                            yield Static("[dim]Label:[/] --", id="detail-label", classes="detail-row")
                            yield Static("[dim]Popularity:[/] --", id="detail-popularity", classes="detail-row")
                            yield Static("[dim]ID:[/] --", id="detail-platform-id", classes="detail-row")

                    # Technical info
                    with Vertical(classes="card", id="technical-info-card"):
                        yield Static("Technical Info", classes="card-title")
                        with Vertical(id="technical-info-content"):
                            yield Static("[dim]Internal ID:[/] --", id="detail-internal-id", classes="detail-row")
                            yield Static("[dim]Matches:[/] --", id="detail-matches-count", classes="detail-row")
                            yield Static("[dim]MusicBrainz:[/] --", id="detail-musicbrainz-id", classes="detail-row")
                            yield Static("[dim]Last Enriched:[/] --", id="detail-last-enriched", classes="detail-row")

                    # Rights information
                    with Vertical(classes="card", id="rights-info-card"):
                        yield Static("Rights", classes="card-title")
                        yield Static("[dim]Copyright:[/] --", id="detail-copyright", classes="detail-row")

    async def on_mount(self) -> None:
        """Handle screen mount."""
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
        try:
            self.query_one("#stat-duration", StatChip).update_value(duration_str)
        except Exception:
            pass

        # Album
        if song.album_name:
            try:
                self.query_one("#stat-album", StatChip).update_value(song.album_name)
            except Exception:
                pass
        else:
            try:
                self.query_one("#stat-album", StatChip).update_value("--")
            except Exception:
                pass

        # Year
        if song.year:
            try:
                self.query_one("#stat-year", StatChip).update_value(str(song.year))
            except Exception:
                pass

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

        # Genres (clear old badges first)
        genres_container = self.query_one("#track-genres", Horizontal)
        genres_container.remove_children()
        for genre in (song.genres or [])[:4]:
            genres_container.mount(Static(genre, classes="badge badge-muted"))

        # Platform link — subtle text
        platform_icon = get_platform_icon(song.platform.value)
        platform_name = song.platform.value.replace("_", " ").title()
        platform_badge = self.query_one("#track-platform-badge", Static)
        if song.url:
            platform_badge.update(
                f"{platform_icon} {platform_name}  [dim]{song.url}[/dim]"
            )
        else:
            platform_badge.update(f"{platform_icon} {platform_name}")

        # Update platform links sidebar
        platform_content = self.query_one("#platform-links-content", Static)
        if song.url:
            platform_content.update(
                f"{platform_icon} {platform_name}\n[dim]{song.url}[/dim]"
            )
        else:
            platform_content.update(f"{platform_icon} {platform_name}")

        # Cover art
        cover_widget = self.query_one("#track-cover", CoverArt)
        cover_widget.cover_url = song.cover_url

    async def _load_track_data(self, force_refresh: bool = False) -> None:
        """Load detailed track data from API or offline."""
        status = self.query_one("#matches-status", Static)
        status.update("[dim]Loading matches...[/]")

        # Try online first
        if self.spotdl_app.is_online:
            await self._load_online_data(use_cache=not force_refresh)
        else:
            await self._load_offline_data()

    async def _load_online_data(self, use_cache: bool = True) -> None:
        """Load data from API server."""
        try:
            api_client = get_api_client()

            # Get track details
            try:
                if self._entity_id:
                    self._track_details = await api_client.get_entity_song(
                        self._entity_id, use_cache=use_cache
                    )
                    self._sync_song_from_entity(self._track_details)
                else:
                    self._track_details = await api_client.get_track(
                        self._track_id, self._platform, use_cache=use_cache
                    )
                    if self._track_details.get("id"):
                        self._entity_id = self._track_details["id"]
                self._update_track_details()
            except APIError as e:
                logger.warning(f"Failed to get track details: {e}")

            # Get matches
            try:
                if self._entity_id:
                    matches = await api_client.get_song_matches(
                        self._entity_id, self._song
                    )
                    if matches:
                        self._matches = matches
                    else:
                        dl_matches = await api_client.find_matches(self._song)
                        self._matches = [
                            self._wrap_download_result(m) for m in dl_matches
                        ]
                else:
                    dl_matches = await api_client.find_matches(self._song)
                    self._matches = [
                        self._wrap_download_result(m) for m in dl_matches
                    ]
                self._update_matches_display()
            except APIError as e:
                logger.warning(f"Failed to get matches: {e}")
                # Fall back to offline matching
                await self._find_offline_matches()

            # Get lyrics
            try:
                if self._entity_id:
                    lyrics_data = await api_client.get_lyrics(self._entity_id)
                    self._lyrics = (
                        lyrics_data.get("lyrics_text")
                        or lyrics_data.get("lyrics")
                        or lyrics_data.get("lyrics_synced")
                    )
                    all_lyrics = await api_client.get_all_lyrics(self._entity_id)
                    self._lyrics_sources_count = all_lyrics.get("total_sources")

                    # Populate all lyrics sources
                    sources = all_lyrics.get("sources", [])
                    if sources:
                        self._all_lyrics = {}
                        for src in sources:
                            name = src.get("source", src.get("name", "unknown"))
                            text = (
                                src.get("lyrics_text")
                                or src.get("lyrics")
                                or src.get("lyrics_synced")
                                or ""
                            )
                            if text:
                                self._all_lyrics[name] = text
                        if self._all_lyrics:
                            first_source = next(iter(self._all_lyrics))
                            self._active_lyrics_source = first_source

                self._update_lyrics_display()
            except APIError as e:
                logger.debug(f"No lyrics available: {e}")

            # Audio features from entity response
            if self._track_details.get("audio_features"):
                self._audio_features = self._track_details.get("audio_features") or {}
                self._update_audio_features()

            # Load metadata snapshots
            try:
                if self._entity_id:
                    snapshots_data = await api_client.get_metadata_sources(
                        self._entity_id
                    )
                    self._snapshots = snapshots_data.get("snapshots", [])
                    self._update_snapshots_display()
            except APIError as e:
                logger.debug(f"No metadata snapshots available: {e}")

        except Exception as e:
            logger.error(f"Error loading online data: {e}")
            self.notify(f"Error loading data: {e}", severity="error")
            # Fall back to offline
            await self._load_offline_data()

    def _sync_song_from_entity(self, data: dict[str, Any]) -> None:
        """Sync Song fields from an internal entity response."""
        platforms = data.get("platforms", [])
        primary = platforms[0] if platforms else {}
        platform = primary.get("platform") or self._platform
        platform_id = primary.get("platform_id") or self._track_id
        url = primary.get("url") or self._song.url

        if platform:
            try:
                self._song.platform = Platform(platform)
            except ValueError:
                pass
            self._platform = platform
        if platform_id:
            self._track_id = platform_id
            self._song.platform_id = platform_id
        if url:
            self._song.url = url

        self._song.name = data.get("name", self._song.name)
        self._song.artists = data.get("artists", self._song.artists)
        self._song.artist = data.get("artist", self._song.artist)
        self._song.duration = data.get("duration", self._song.duration)
        self._song.album_name = data.get("album_name", self._song.album_name)
        self._song.isrc = data.get("isrc", self._song.isrc)
        self._song.cover_url = data.get("cover_url", self._song.cover_url)

    async def _load_offline_data(self) -> None:
        """Load data using offline providers, mirroring online data flow."""
        offline_matcher = get_offline_matcher()

        # Enrich song metadata
        try:
            self._song = await offline_matcher.enrich_song(self._song)
            self._update_song_display()
        except Exception as e:
            logger.warning(f"Offline enrichment failed: {e}")

        # Build track_details from Song object so _update_track_details works
        self._track_details = self._build_track_details_from_song()
        self._update_track_details()

        # Audio features from Spotify API
        try:
            features = await offline_matcher.get_audio_features(self._song)
            if features:
                self._audio_features = features
                self._update_audio_features()
        except Exception as e:
            logger.debug(f"Audio features unavailable: {e}")

        # Find matches
        await self._find_offline_matches()

        # Lyrics from all providers
        if self._song.lyrics:
            self._lyrics = self._song.lyrics

        try:
            all_lyrics = await offline_matcher.get_all_lyrics(self._song)
            if all_lyrics:
                self._all_lyrics = all_lyrics
                self._lyrics_sources_count = len(all_lyrics)

                # Use first available if we don't already have lyrics
                if not self._lyrics:
                    self._lyrics = next(iter(all_lyrics.values()))

                # Set active lyrics source
                first_source = next(iter(all_lyrics))
                self._active_lyrics_source = first_source
        except Exception as e:
            logger.warning(f"Offline lyrics fetch failed: {e}")

        self._update_lyrics_display()

    def _build_track_details_from_song(self) -> dict[str, Any]:
        """Build a track_details dict from the Song object for offline display."""
        song = self._song
        details: dict[str, Any] = {
            "name": song.name,
            "artist": song.artist,
            "artists": song.artists,
            "duration": song.duration,
            "album_name": song.album_name,
            "isrc": song.isrc,
            "label": song.publisher or None,
            "popularity": song.popularity,
            "copyright": song.copyright_text,
            "cover_url": song.cover_url,
            "matches_count": len(self._matches),
        }
        if self._entity_id:
            details["id"] = self._entity_id
        return details

    async def _find_offline_matches(self) -> None:
        """Find matches using offline matcher."""
        status = self.query_one("#matches-status", Static)
        status.update("[dim]Searching for matches...[/]")

        try:
            from spotdl_core import TargetPlatform

            # If the song itself is already from a downloadable platform,
            # include it as the first match
            downloadable_platforms = {
                "youtube_music": TargetPlatform.YOUTUBE_MUSIC,
                "soundcloud": TargetPlatform.SOUNDCLOUD,
                "bandcamp": TargetPlatform.BANDCAMP,
                "youtube": TargetPlatform.YOUTUBE,
            }
            self._matches = []

            if self._song.platform.value in downloadable_platforms and self._song.url:
                tp = downloadable_platforms[self._song.platform.value]
                result = DownloadResult(
                    name=self._song.name,
                    artists=list(self._song.artists),
                    artist=self._song.artist,
                    duration=self._song.duration,
                    platform=tp,
                    platform_id=self._song.platform_id,
                    url=self._song.url,
                    score=100.0,
                    cover_url=self._song.cover_url,
                    album_name=self._song.album_name or None,
                )
                self._matches.append(self._wrap_download_result(result))

            # Also search for additional matches
            offline_matcher = get_offline_matcher()
            results = await offline_matcher.find_matches(self._song, limit=10)

            seen_ids = {m.result.platform_id for m in self._matches}
            for r in results:
                if r.platform_id not in seen_ids:
                    dl_result = DownloadResult.from_result(r, score=0.0)
                    self._matches.append(self._wrap_download_result(dl_result))
                    seen_ids.add(r.platform_id)

            self._update_matches_display()

        except Exception as e:
            logger.error(f"Offline matching failed: {e}")
            status.update(f"[red]Error: {e}[/]")

    def _update_matches_display(self) -> None:
        """Update the matches display using MatchBar widgets."""
        container = self.query_one("#matches-container", Container)
        container.remove_children()

        status = self.query_one("#matches-status", Static)

        if not self._matches:
            status.update("[yellow]No matches found[/]")
            return

        for i, match in enumerate(self._matches[:10]):
            result = match.result

            # Build title: name + artist truncated
            title = result.name
            if result.artist:
                title = f"{result.name} - {result.artist}"

            # Score
            score = match.score if match.score > 0 else 0.0

            # Net votes
            net = match.net_votes

            bar = MatchBar(
                platform=result.platform.value,
                title=title,
                score=score,
                votes=net,
                match_data={
                    "index": i,
                    "match_id": match.id,
                    "platform": result.platform.value,
                    "url": result.url,
                },
                id=f"match-bar-{i}",
            )
            container.mount(bar)

        status.update(f"[dim]Found {len(self._matches)} match(es)[/]")

        # Update matches count in sidebar
        try:
            self.query_one("#detail-matches-count", Static).update(
                f"[dim]Matches:[/] {len(self._matches)}"
            )
        except Exception:
            pass

    def _wrap_download_result(self, result: DownloadResult) -> MatchEntry:
        """Wrap a download result into a match entry."""
        return MatchEntry(
            id=None,
            source_url=self._song.url,
            target_url=result.url,
            target_platform=result.platform.value,
            score=result.score,
            confidence=0.0,
            match_type="system",
            status=None,
            result=result,
        )

    def _format_lyrics_text(self, text: str) -> str:
        """Format lyrics text for display, handling LRC timestamps."""
        if not text:
            return "[dim]No lyrics available[/]"
        # Truncate very long lyrics for display
        if len(text) > 2000:
            text = text[:2000] + "\n\n[dim]... (truncated)[/]"
        return text

    def _update_lyrics_display(self) -> None:
        """Update lyrics display with tabbed multi-source view."""
        lyrics_status = self.query_one("#lyrics-status", Static)

        # Update the default tab content
        try:
            lyrics_content = self.query_one("#lyrics-content", Static)
            if self._lyrics:
                lyrics_content.update(self._format_lyrics_text(self._lyrics))
            else:
                lyrics_content.update("[dim]No lyrics available[/]")
        except Exception:
            pass

        # Build tabs for all lyrics sources
        if self._all_lyrics:
            try:
                tabbed = self.query_one("#lyrics-tabs", TabbedContent)
                # Remove existing extra tabs (keep default)
                existing_panes = list(tabbed.query(TabPane))
                for pane in existing_panes:
                    if pane.id != "lyrics-tab-default":
                        pane.remove()

                # Add a tab per source
                for source_name, source_text in self._all_lyrics.items():
                    tab_id = f"lyrics-tab-{source_name.lower().replace(' ', '-')}"
                    # Skip if already present
                    try:
                        tabbed.query_one(f"#{tab_id}")
                        continue
                    except Exception:
                        pass
                    pane = TabPane(source_name.title(), id=tab_id)
                    tabbed.add_pane(pane)
                    formatted = self._format_lyrics_text(source_text)
                    pane.mount(
                        VerticalScroll(
                            Static(formatted, classes="lyrics-text"),
                            classes="lyrics-scroll",
                        )
                    )
            except Exception:
                pass

        if self._lyrics_sources_count:
            lyrics_status.update(f"[dim]{self._lyrics_sources_count} source(s)[/]")
        elif self._all_lyrics:
            lyrics_status.update(f"[dim]{len(self._all_lyrics)} source(s)[/]")
        else:
            lyrics_status.update("")

    def _update_audio_features(self) -> None:
        """Update audio features display using AudioMeter and StatChip widgets."""
        if not self._audio_features:
            return

        def set_meter(meter_id: str, key: str) -> None:
            val = self._audio_features.get(key)
            if val is not None:
                try:
                    meter = self.query_one(f"#meter-{meter_id}", AudioMeter)
                    meter.update_value(float(val))
                except Exception:
                    pass

        # BPM
        bpm = self._audio_features.get("tempo") or self._audio_features.get("bpm")
        if bpm:
            try:
                self.query_one("#feature-bpm", StatChip).update_value(f"{bpm:.0f}")
            except Exception:
                pass

        # AudioMeter features (0-1 scale)
        set_meter("energy", "energy")
        set_meter("danceability", "danceability")
        set_meter("valence", "valence")
        set_meter("speechiness", "speechiness")
        set_meter("acousticness", "acousticness")
        set_meter("instrumentalness", "instrumentalness")
        set_meter("liveness", "liveness")

        # Loudness (dB value)
        loudness = self._audio_features.get("loudness")
        if loudness is not None:
            try:
                self.query_one("#feature-loudness", StatChip).update_value(f"{loudness:.1f} dB")
            except Exception:
                pass

        # Time signature
        time_sig = self._audio_features.get("time_signature")
        if time_sig is not None:
            try:
                self.query_one("#feature-time-sig", StatChip).update_value(f"{time_sig}/4")
            except Exception:
                pass

        # Key signature (if available)
        key = self._audio_features.get("key")
        mode = self._audio_features.get("mode")
        if key is not None:
            key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            key_name = key_names[int(key) % 12]
            mode_name = "Major" if mode == 1 else "Minor" if mode == 0 else ""
            label = f"{key_name} {mode_name}".strip()
            try:
                self.query_one("#stat-key", StatChip).update_value(label)
            except Exception:
                pass

    def _update_track_details(self) -> None:
        """Update track details and technical info sidebar cards.

        Always updates every field, using '--' for missing values so
        widgets maintain height and the layout stays stable.
        """
        data = self._track_details or {}

        # Track Details card
        isrc = data.get("isrc")
        self.query_one("#detail-isrc", Static).update(
            f"[dim]ISRC:[/] {isrc}" if isrc else "[dim]ISRC:[/] --"
        )

        label = data.get("label")
        self.query_one("#detail-label", Static).update(
            f"[dim]Label:[/] {label}" if label else "[dim]Label:[/] --"
        )

        popularity = data.get("popularity")
        self.query_one("#detail-popularity", Static).update(
            f"[dim]Popularity:[/] {popularity}/100"
            if popularity is not None
            else "[dim]Popularity:[/] --"
        )

        self.query_one("#detail-platform-id", Static).update(
            f"[dim]ID:[/] {self._track_id or '--'}"
        )

        # Technical Info card
        self.query_one("#detail-internal-id", Static).update(
            f"[dim]Internal ID:[/] {self._entity_id}"
            if self._entity_id
            else "[dim]Internal ID:[/] --"
        )

        matches_count = data.get("matches_count", len(self._matches))
        self.query_one("#detail-matches-count", Static).update(
            f"[dim]Matches:[/] {matches_count}"
        )

        external_ids = data.get("external_ids", {})
        mb_id = external_ids.get("musicbrainz") or data.get("musicbrainz_id")
        self.query_one("#detail-musicbrainz-id", Static).update(
            f"[dim]MusicBrainz:[/] {mb_id}" if mb_id else "[dim]MusicBrainz:[/] --"
        )

        last_enriched = data.get("last_enriched") or data.get("updated_at")
        if last_enriched:
            date_str = last_enriched[:10] if len(last_enriched) >= 10 else last_enriched
            self.query_one("#detail-last-enriched", Static).update(
                f"[dim]Last Enriched:[/] {date_str}"
            )
        else:
            self.query_one("#detail-last-enriched", Static).update(
                "[dim]Last Enriched:[/] --"
            )

        # Copyright / Rights
        copyright_text = data.get("copyright") or data.get("label")
        self.query_one("#detail-copyright", Static).update(
            f"[dim]\u00a9[/] {copyright_text}" if copyright_text else "[dim]Copyright:[/] --"
        )

    def _update_snapshots_display(self) -> None:
        """Update metadata snapshots table."""
        try:
            table = self.query_one("#metadata-sources-table", DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True
            if len(table.columns) == 0:
                table.add_columns("Provider", "Confidence", "Fetched At")
            table.clear()

            if not self._snapshots:
                return

            for snap in self._snapshots:
                provider = snap.get("provider", snap.get("source", "unknown"))
                confidence = snap.get("confidence", snap.get("quality_score", 0))
                if isinstance(confidence, float):
                    confidence_str = f"{confidence:.0%}"
                else:
                    confidence_str = str(confidence)
                fetched_at = snap.get("fetched_at", snap.get("created_at", "--"))
                if fetched_at and len(fetched_at) > 19:
                    fetched_at = fetched_at[:19]
                table.add_row(
                    str(provider).title(),
                    confidence_str,
                    str(fetched_at),
                    key=str(provider),
                )
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in metadata sources table."""
        if event.data_table.id == "metadata-sources-table" and self._snapshots:
            key = str(event.row_key.value) if event.row_key else None
            if key is None:
                return
            # Find the matching snapshot
            for snap in self._snapshots:
                provider = snap.get("provider", snap.get("source", "unknown"))
                if str(provider) == key:
                    payload = snap.get("normalized_payload", snap.get("canonical", {}))
                    if payload:
                        lines = []
                        for k, v in payload.items():
                            if v is not None and v != "" and v != []:
                                lines.append(f"[dim]{k}:[/] {v}")
                        detail_text = "\n".join(lines) if lines else "[dim]No fields[/]"
                    else:
                        detail_text = "[dim]No payload data[/]"
                    try:
                        self.query_one("#snapshot-detail-content", Static).update(detail_text)
                    except Exception:
                        pass
                    break

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        pass

    def on_match_bar_selected(self, message: MatchBar.Selected) -> None:
        """Handle MatchBar selection — track selected index for voting."""
        idx = message.match_data.get("index", 0)
        self._selected_match_idx = idx

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "download-btn":
            await self._download_best_match()
        elif event.button.id == "refresh-btn":
            await self._load_track_data(force_refresh=True)
        elif event.button.id == "refresh-meta-btn":
            await self._refresh_metadata()
        elif event.button.id == "submit-match-btn":
            await self._open_submit_match()
        elif event.button.id == "report-btn":
            await self._open_report()
        elif event.button.id == "inline-submit-btn":
            await self._inline_submit_match()
        elif event.button.id == "fetch-all-lyrics-btn":
            await self._fetch_all_lyrics()
        elif event.button.id == "submit-lyrics-btn":
            await self._open_submit_lyrics()

    async def _download_best_match(self) -> None:
        """Download the best available match."""
        if not self._matches:
            self.notify("No matches available to download", severity="warning")
            return

        best_match = self._matches[0]
        queue = self.spotdl_app.download_queue

        await queue.add(self._song, result=best_match.result)
        self.notify(f"Added to queue: {self._song.display_name}")

    def action_download(self) -> None:
        """Download action."""
        self.run_worker(self._download_best_match())

    def action_refresh(self) -> None:
        """Refresh action."""
        self.run_worker(self._load_track_data(force_refresh=True))

    def action_refresh_metadata(self) -> None:
        """Refresh metadata action."""
        self.run_worker(self._refresh_metadata())

    def action_submit_match(self) -> None:
        """Submit match action."""
        self.run_worker(self._open_submit_match())

    def action_report(self) -> None:
        """Report data action."""
        self.run_worker(self._open_report())

    def action_submit_lyrics(self) -> None:
        """Submit lyrics action."""
        self.run_worker(self._open_submit_lyrics())

    def action_vote_up(self) -> None:
        """Upvote selected match."""
        self.run_worker(self._vote_selected("up"))

    def action_vote_down(self) -> None:
        """Downvote selected match."""
        self.run_worker(self._vote_selected("down"))

    async def _refresh_metadata(self) -> None:
        """Refresh metadata and enrichment for the current track."""
        if not self.spotdl_app.is_online:
            try:
                self.notify("Refreshing metadata from local providers...")
                await self._load_offline_data()
                self._update_song_display()
                self.notify("Metadata refreshed")
            except Exception as e:
                self.notify(f"Offline refresh failed: {e}", severity="error")
            return

        if not self._entity_id:
            self.notify("Metadata refresh requires online mode", severity="warning")
            return

        try:
            api_client = get_api_client()
            await api_client.refresh_entity("songs", self._entity_id)
            await api_client.enrich_song_all_sources(self._entity_id)
            await api_client.fetch_all_lyrics(self._entity_id)
            self._track_details = await api_client.get_entity_song(
                self._entity_id, use_cache=False
            )
            self._sync_song_from_entity(self._track_details)
            self._audio_features = self._track_details.get("audio_features") or {}
            await self._load_track_data(force_refresh=True)
            self.notify("Metadata refreshed")
        except APIError as e:
            self.notify(f"Metadata refresh failed: {e}", severity="error")

    async def _open_submit_match(self) -> None:
        """Open submit match screen."""
        if not self.spotdl_app.is_online:
            self.notify("Submit match requires online mode", severity="warning")
            return
        if not await self._ensure_authenticated():
            return
        if not self._song.url:
            self.notify("Source URL unavailable", severity="warning")
            return

        from spotdl_cli.screens.submit_match import SubmitMatchScreen

        self.app.push_screen(
            SubmitMatchScreen(
                source_url=self._song.url,
                song=self._song,
                on_submit=self._on_match_submitted,
            )
        )

    async def _fetch_all_lyrics(self) -> None:
        """Fetch lyrics from all sources."""
        if not self.spotdl_app.is_online:
            self.notify("Fetch all lyrics requires online mode", severity="warning")
            return
        if not self._entity_id:
            self.notify("Entity ID required", severity="warning")
            return

        try:
            self.notify("Fetching lyrics from all sources...")
            api_client = get_api_client()
            await api_client.fetch_all_lyrics(self._entity_id)

            # Reload lyrics data
            all_lyrics = await api_client.get_all_lyrics(self._entity_id)
            self._lyrics_sources_count = all_lyrics.get("total_sources")
            sources = all_lyrics.get("sources", [])
            if sources:
                self._all_lyrics = {}
                for src in sources:
                    name = src.get("source", src.get("name", "unknown"))
                    text = (
                        src.get("lyrics_text")
                        or src.get("lyrics")
                        or src.get("lyrics_synced")
                        or ""
                    )
                    if text:
                        self._all_lyrics[name] = text
                if self._all_lyrics and not self._lyrics:
                    self._lyrics = next(iter(self._all_lyrics.values()))
            self._update_lyrics_display()
            self.notify(f"Fetched {len(self._all_lyrics)} lyrics source(s)")
        except APIError as e:
            self.notify(f"Fetch failed: {e}", severity="error")

    async def _open_submit_lyrics(self) -> None:
        """Open submit lyrics screen."""
        if not self.spotdl_app.is_online:
            self.notify("Submit lyrics requires online mode", severity="warning")
            return
        if not await self._ensure_authenticated():
            return
        if not self._entity_id:
            self.notify("Entity ID required", severity="warning")
            return

        from spotdl_cli.screens.submit_lyrics import SubmitLyricsScreen

        self.app.push_screen(
            SubmitLyricsScreen(
                entity_id=self._entity_id,
                song_name=self._song.name,
                on_submit=self._on_lyrics_submitted,
            )
        )

    def _on_lyrics_submitted(self) -> None:
        """Handle lyrics submission callback."""
        self.run_worker(self._reload_lyrics())

    async def _reload_lyrics(self) -> None:
        """Reload lyrics data after submission."""
        if not self._entity_id:
            return
        try:
            api_client = get_api_client()
            all_lyrics = await api_client.get_all_lyrics(self._entity_id)
            self._lyrics_sources_count = all_lyrics.get("total_sources")
            sources = all_lyrics.get("sources", [])
            if sources:
                self._all_lyrics = {}
                for src in sources:
                    name = src.get("source", src.get("name", "unknown"))
                    text = (
                        src.get("lyrics_text")
                        or src.get("lyrics")
                        or src.get("lyrics_synced")
                        or ""
                    )
                    if text:
                        self._all_lyrics[name] = text
                if self._all_lyrics and not self._lyrics:
                    self._lyrics = next(iter(self._all_lyrics.values()))
            self._update_lyrics_display()
        except APIError as e:
            logger.debug(f"Lyrics reload failed: {e}")

    async def _open_report(self) -> None:
        """Open report data screen."""
        if not self._entity_id:
            self.notify("Report requires internal entity ID", severity="warning")
            return

        fields = self._build_report_fields()
        if not fields:
            self.notify("No reportable fields available", severity="warning")
            return

        from spotdl_cli.screens.report import ReportScreen

        self.app.push_screen(
            ReportScreen(
                entity_type="song",
                entity_id=self._entity_id,
                entity_name=self._song.name,
                fields=fields,
            )
        )

    async def _ensure_authenticated(self) -> bool:
        """Check if user is authenticated, prompt login if not. Returns True if authenticated."""
        if not self.spotdl_app.is_online:
            self.notify("This feature requires online mode", severity="warning")
            return False

        settings = get_settings()
        if settings.auth_token:
            return True

        from spotdl_cli.screens.login import LoginScreen
        result = await self.app.push_screen_wait(LoginScreen())
        return result is True

    async def _vote_selected(self, vote_type: str) -> None:
        """Vote on the selected match."""
        if self._selected_match_idx >= len(self._matches):
            self.notify("Select a match to vote", severity="warning")
            return

        match = self._matches[self._selected_match_idx]
        if not match.id:
            self.notify("Voting requires a saved match", severity="warning")
            return

        if not await self._ensure_authenticated():
            return

        try:
            api_client = get_api_client()
            summary = await api_client.get_match_votes(match.id)
            user_vote = summary.get("user_vote")

            if user_vote == vote_type:
                summary = await api_client.remove_vote(match.id)
            else:
                summary = await api_client.cast_vote(match.id, vote_type)

            match.upvotes = summary.get("upvotes", match.upvotes)
            match.downvotes = summary.get("downvotes", match.downvotes)
            self._update_matches_display()
        except APIError as e:
            self.notify(f"Vote failed: {e}", severity="error")

    def _build_report_fields(self) -> list[dict[str, str]]:
        """Build reportable fields for the current track."""
        fields: list[dict[str, str]] = []
        track = self._track_details or {}

        def add_field(name: str, label: str, value: str | None) -> None:
            if value is None:
                return
            fields.append({"name": name, "label": label, "current_value": str(value)})

        add_field("name", "Title", track.get("name") or self._song.name)
        add_field("artist", "Artist", track.get("artist") or self._song.artist)
        add_field("album_name", "Album", track.get("album_name") or self._song.album_name)
        add_field("release_date", "Release Date", track.get("release_date"))
        add_field("label", "Label", track.get("label"))
        add_field("isrc", "ISRC", track.get("isrc") or self._song.isrc)
        add_field("genres", "Genres", ", ".join(track.get("genres", []) or []))
        add_field("track_number", "Track Number", track.get("track_number"))
        add_field("disc_number", "Disc Number", track.get("disc_number"))
        return fields

    async def _inline_submit_match(self) -> None:
        """Submit a match from the inline form."""
        if not self.spotdl_app.is_online:
            self.notify("Submit match requires online mode", severity="warning")
            return

        if not await self._ensure_authenticated():
            return

        url = self.query_one("#submit-match-url", Input).value.strip()
        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        try:
            api_client = get_api_client()
            match = await api_client.submit_match(
                source_url=self._song.url,
                target_url=url,
                fallback_song=self._song,
            )
            self.notify("Match submitted successfully")
            self.query_one("#submit-match-url", Input).value = ""
            if isinstance(match, dict) and match.get("id"):
                await self._load_track_data()
        except APIError as e:
            self.notify(f"Submit failed: {e}", severity="error")

    def _on_match_submitted(self, match: MatchEntry) -> None:
        """Handle new match submission."""
        existing_ids = {m.id for m in self._matches if m.id}
        if match.id and match.id not in existing_ids:
            self._matches.append(match)
            self._update_matches_display()
