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
    Label,
    ProgressBar,
    Rule,
    Select,
    Static,
)

from spotdl_cli.widgets import CoverArt

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
                            yield Button(
                                "Refresh Metadata",
                                id="refresh-meta-btn",
                                variant="warning",
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

                    # Lyrics card
                    with Vertical(classes="card", id="lyrics-card"):
                        with Horizontal(classes="card-header-row"):
                            yield Static("Lyrics", classes="card-title")
                            yield Select(
                                [("Default", "default")],
                                value="default",
                                id="lyrics-source-select",
                            )

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

                            # Speechiness
                            with Horizontal(classes="feature-row"):
                                yield Label("Speechiness", classes="feature-label")
                                yield ProgressBar(id="feature-speechiness", total=100, show_eta=False)

                            # Acousticness
                            with Horizontal(classes="feature-row"):
                                yield Label("Acousticness", classes="feature-label")
                                yield ProgressBar(id="feature-acousticness", total=100, show_eta=False)

                            # Instrumentalness
                            with Horizontal(classes="feature-row"):
                                yield Label("Instrumental", classes="feature-label")
                                yield ProgressBar(id="feature-instrumentalness", total=100, show_eta=False)

                            # Liveness
                            with Horizontal(classes="feature-row"):
                                yield Label("Liveness", classes="feature-label")
                                yield ProgressBar(id="feature-liveness", total=100, show_eta=False)

                            # Loudness
                            with Horizontal(classes="feature-row"):
                                yield Label("Loudness", classes="feature-label")
                                yield Static("--", id="feature-loudness", classes="feature-value")

                            # Time Signature
                            with Horizontal(classes="feature-row"):
                                yield Label("Time Sig.", classes="feature-label")
                                yield Static("--", id="feature-time-sig", classes="feature-value")

                    # Track details
                    with Vertical(classes="card", id="track-details-card"):
                        yield Static("Track Details", classes="card-title")
                        with Vertical(id="track-details-content"):
                            yield Static("", id="detail-isrc", classes="detail-row")
                            yield Static("", id="detail-label", classes="detail-row")
                            yield Static("", id="detail-popularity", classes="detail-row")
                            yield Static("", id="detail-platform-id", classes="detail-row")

                    # Technical info
                    with Vertical(classes="card", id="technical-info-card"):
                        yield Static("Technical Info", classes="card-title")
                        with Vertical(id="technical-info-content"):
                            yield Static("", id="detail-internal-id", classes="detail-row")
                            yield Static("", id="detail-matches-count", classes="detail-row")
                            yield Static("", id="detail-musicbrainz-id", classes="detail-row")
                            yield Static("", id="detail-last-enriched", classes="detail-row")

                    # Rights information
                    with Vertical(classes="card", id="rights-info-card"):
                        yield Static("Rights", classes="card-title")
                        yield Static("", id="detail-copyright", classes="detail-row")

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
            "Votes",
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

        # Genres (clear old badges first)
        genres_container = self.query_one("#track-genres", Horizontal)
        genres_container.remove_children()
        for genre in (song.genres or [])[:4]:
            genres_container.mount(Static(genre, classes="badge badge-muted"))

        # Platform link
        platform_content = self.query_one("#platform-links-content", Static)
        platform_icon = get_platform_icon(song.platform.value)
        platform_name = song.platform.value.replace("_", " ").title()
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
                self._update_matches_table()
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
                            options = [(name.title(), name) for name in self._all_lyrics]
                            try:
                                select = self.query_one("#lyrics-source-select", Select)
                                select.set_options(options)
                                first_source = next(iter(self._all_lyrics))
                                select.value = first_source
                                self._active_lyrics_source = first_source
                            except Exception:
                                pass

                self._update_lyrics_display()
            except APIError as e:
                logger.debug(f"No lyrics available: {e}")

            # Audio features from entity response
            if self._track_details.get("audio_features"):
                self._audio_features = self._track_details.get("audio_features") or {}
                self._update_audio_features()

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

                # Populate lyrics source selector
                options = [(name, name) for name in all_lyrics]
                try:
                    select = self.query_one("#lyrics-source-select", Select)
                    select.set_options(options)
                    first_source = next(iter(all_lyrics))
                    select.value = first_source
                    self._active_lyrics_source = first_source
                except Exception:
                    pass
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
            result = match.result
            duration = f"{result.duration // 60}:{result.duration % 60:02d}"
            platform_icon = get_platform_icon(result.platform.value)

            # Score display
            score_str = f"{match.score:.0f}%" if match.score > 0 else "\u2014"

            # Color-coded votes
            net = match.net_votes
            if net > 0:
                votes_str = f"[green]+{net}[/green]"
            elif net < 0:
                votes_str = f"[red]{net}[/red]"
            else:
                votes_str = "0"

            # Status with badges
            badges: list[str] = []
            if i == 1 and result.verified:
                badges.append("[green]Best Match[/green]")
            if match.match_type == "user":
                badges.append("[cyan]User Submitted[/cyan]")
            if match.status == "pending":
                badges.append("[yellow]Pending Review[/yellow]")
            elif match.status == "verified":
                badges.append("[green]Verified[/green]")
            elif match.status:
                badges.append(match.status.title())
            elif result.verified:
                badges.append("[green]Verified[/green]")
            else:
                badges.append("[dim]Unverified[/dim]")
            status_str = " ".join(badges)

            table.add_row(
                str(i),
                f"{platform_icon} {result.platform.value}",
                result.name[:35] + "..." if len(result.name) > 35 else result.name,
                result.artist[:20] + "..." if len(result.artist) > 20 else result.artist,
                duration,
                score_str,
                votes_str,
                status_str,
            )

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
            if self._lyrics_sources_count:
                lyrics_status.update(f"[dim]{self._lyrics_sources_count} source(s)[/]")
            else:
                lyrics_status.update("")
        else:
            lyrics_content.update("[dim]No lyrics available[/]")

    def _update_audio_features(self) -> None:
        """Update audio features display."""
        if not self._audio_features:
            return

        def set_bar(feature_id: str, key: str) -> None:
            val = self._audio_features.get(key)
            if val is not None:
                try:
                    bar = self.query_one(f"#feature-{feature_id}", ProgressBar)
                    bar.update(progress=int(float(val) * 100))
                except Exception:
                    pass

        # BPM
        bpm = self._audio_features.get("tempo") or self._audio_features.get("bpm")
        if bpm:
            self.query_one("#feature-bpm", Static).update(f"{bpm:.0f}")

        # Progress bar features (0-1 scale)
        set_bar("energy", "energy")
        set_bar("danceability", "danceability")
        set_bar("valence", "valence")
        set_bar("speechiness", "speechiness")
        set_bar("acousticness", "acousticness")
        set_bar("instrumentalness", "instrumentalness")
        set_bar("liveness", "liveness")

        # Loudness (dB value)
        loudness = self._audio_features.get("loudness")
        if loudness is not None:
            self.query_one("#feature-loudness", Static).update(f"{loudness:.1f} dB")

        # Time signature
        time_sig = self._audio_features.get("time_signature")
        if time_sig is not None:
            self.query_one("#feature-time-sig", Static).update(f"{time_sig}/4")

        # Key signature (if available)
        key = self._audio_features.get("key")
        mode = self._audio_features.get("mode")
        if key is not None:
            key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            key_name = key_names[int(key) % 12]
            mode_name = "Major" if mode == 1 else "Minor" if mode == 0 else ""
            label = f"{key_name} {mode_name}".strip()
            self.query_one("#track-key", Static).update(f"[dim]Key:[/] {label}")

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

        # Technical info
        if self._entity_id:
            self.query_one("#detail-internal-id", Static).update(
                f"[dim]Internal ID:[/] {self._entity_id}"
            )

        matches_count = self._track_details.get("matches_count", len(self._matches))
        self.query_one("#detail-matches-count", Static).update(
            f"[dim]Matches:[/] {matches_count}"
        )

        # External IDs
        external_ids = self._track_details.get("external_ids", {})
        mb_id = external_ids.get("musicbrainz") or self._track_details.get("musicbrainz_id")
        if mb_id:
            self.query_one("#detail-musicbrainz-id", Static).update(
                f"[dim]MusicBrainz:[/] {mb_id}"
            )

        last_enriched = self._track_details.get("last_enriched") or self._track_details.get("updated_at")
        if last_enriched:
            date_str = last_enriched[:10] if len(last_enriched) >= 10 else last_enriched
            self.query_one("#detail-last-enriched", Static).update(
                f"[dim]Last Enriched:[/] {date_str}"
            )

        # Copyright / Rights
        copyright_text = (
            self._track_details.get("copyright")
            or self._track_details.get("label")
        )
        if copyright_text:
            self.query_one("#detail-copyright", Static).update(
                f"[dim]\u00a9[/] {copyright_text}"
            )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes."""
        if event.select.id == "lyrics-source-select" and self._all_lyrics:
            source = str(event.value)
            if source in self._all_lyrics:
                self._active_lyrics_source = source
                self._lyrics = self._all_lyrics[source]
                self._update_lyrics_display()

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
        table = self.query_one("#matches-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self._matches):
            self.notify("Select a match to vote", severity="warning")
            return

        match = self._matches[table.cursor_row]
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
            self._update_matches_table()
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
            self._update_matches_table()
