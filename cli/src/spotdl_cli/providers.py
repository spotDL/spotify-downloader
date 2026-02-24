"""Command palette providers for SpotDL CLI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from textual.command import DiscoveryHit, Hit, Provider

from spotdl_cli.core import APIError, get_api_client
from spotdl_cli.theme import get_platform_icon

if TYPE_CHECKING:
    from spotdl_cli.app import SpotDLApp
    from spotdl_cli.core.types import UniversalSearchResponse

logger = logging.getLogger(__name__)


class SpotDLCommandProvider(Provider):
    """Universal search provider for the command palette."""

    async def search(self, query: str) -> None:
        """Search for songs, albums, artists, and playlists.

        Args:
            query: The search query from the command palette input.
        """
        if len(query) < 2:
            return

        matcher = self.matcher(query)
        api_client = get_api_client()

        try:
            # We use universal_search returning 5 of each for quick palette lookups
            results = await api_client.universal_search(query, limit=5)
            
            # Helper to create hits from entities
            hits = []
            
            # Process artists
            for artist in results.artists:
                name = artist.get("name", "Unknown Artist")
                platform = artist.get("platform", "spotify")
                desc = "Artist \u2022 " + platform.title()
                icon = get_platform_icon(platform)
                
                # Match against the artist name, and if it matches we show it
                score = matcher.match(name)
                if score > 0:
                    hits.append(Hit(
                        score,
                        matcher.highlight(f"{icon} {name}"),
                        self._make_navigate_callback("ArtistScreen", artist, "artist"),
                        help=desc,
                    ))

            # Process albums
            for album in results.albums:
                name = album.get("name", "Unknown Album")
                artist_name = album.get("artist_name", "") or album.get("artist", "")
                platform = album.get("platform", "spotify")
                desc = f"Album \u2022 {artist_name} \u2022 {platform.title()}"
                icon = get_platform_icon(platform)
                
                # Match against album name or artist name
                score = matcher.match(f"{name} {artist_name}")
                if score > 0:
                    hits.append(Hit(
                        score,
                        matcher.highlight(f"{icon} {name}"),
                        self._make_navigate_callback("AlbumScreen", album, "album"),
                        help=desc,
                    ))

            # Process playlists
            for playlist in results.playlists:
                name = playlist.get("name", "Unknown Playlist")
                owner = playlist.get("owner_name", "")
                platform = playlist.get("platform", "spotify")
                desc = f"Playlist \u2022 {owner} \u2022 {platform.title()}"
                icon = get_platform_icon(platform)
                
                score = matcher.match(f"{name} {owner}")
                if score > 0:
                    hits.append(Hit(
                        score,
                        matcher.highlight(f"{icon} {name}"),
                        self._make_navigate_callback("PlaylistScreen", playlist, "playlist"),
                        help=desc,
                    ))

            # Process tracks
            for track in results.tracks:
                name = track.get("name", "Unknown Track")
                artist_name = track.get("artist_name", "") or track.get("artist", "")
                platform = track.get("platform", "spotify")
                desc = f"Track \u2022 {artist_name} \u2022 {platform.title()}"
                icon = get_platform_icon(platform)
                
                score = matcher.match(f"{name} {artist_name}")
                if score > 0:
                    hits.append(Hit(
                        score,
                        matcher.highlight(f"{icon} {name}"),
                        self._make_track_callback(track, "track"),
                        help=desc,
                    ))

            # Sort by score and yield
            hits.sort(key=lambda hit: hit.score, reverse=True)
            for hit in hits:
                yield hit

        except APIError as e:
            logger.error(f"Search failed in command palette: {e}")
            yield Hit(1.0, f"Error: {e}", lambda: None, help="API Error")
        except Exception as e:
            logger.error(f"Error in command palette: {e}")

    def _make_navigate_callback(self, screen_type: str, item: dict[str, Any], entity_type: str) -> Any:
        """Create a callback that navigates to the given screen type."""
        app = self.app
        entity_id = item.get("id")
        platform = item.get("platform", "spotify")
        platform_id = item.get("platform_id", "")
        
        async def navigate() -> None:
            if screen_type == "ArtistScreen":
                from spotdl_cli.screens.artist import ArtistScreen
                await app.push_screen(ArtistScreen(platform_id, platform, initial_data=item, entity_id=entity_id))
            elif screen_type == "AlbumScreen":
                from spotdl_cli.screens.album import AlbumScreen
                await app.push_screen(AlbumScreen(platform_id, platform, initial_data=item, entity_id=entity_id))
            elif screen_type == "PlaylistScreen":
                from spotdl_cli.screens.playlist import PlaylistScreen
                await app.push_screen(PlaylistScreen(platform_id, platform, initial_data=item, entity_id=entity_id))
                
        return navigate
        
    def _make_track_callback(self, track: dict[str, Any], entity_type: str) -> Any:
        """Create a callback for track navigation."""
        app = self.app
        entity_id = track.get("id")
        platform = track.get("platform", "spotify")
        platform_id = track.get("platform_id", "")
        
        async def navigate() -> None:
            from spotdl_cli.screens.track import TrackScreen
            from spotdl_cli.core.types import Song, Platform
            
            song = Song(
                name=track.get("name", "Unknown"),
                artists=[track.get("artist_name") or track.get("artist", "Unknown")],
                artist=track.get("artist_name") or track.get("artist", "Unknown"),
                duration=track.get("duration", 0),
                platform=Platform(platform),
                platform_id=platform_id,
                url=track.get("url", ""),
                cover_url=track.get("cover_url"),
            )
            await app.push_screen(TrackScreen(song, platform_id, platform, initial_data=track, entity_id=entity_id))
            
        return navigate

