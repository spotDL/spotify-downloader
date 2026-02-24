"""Unified provider plugin registry and capability matrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spotdl.core.capabilities import (
    Capability,
    DownloadCapability,
    DownloadHookResult,
    ProviderPlugin,
)
from spotdl.core.services.download import DownloadRequest, create_download_id, get_download_manager


@dataclass(slots=True)
class ProviderHealth:
    provider_id: str
    display_name: str
    capabilities: list[str]
    status: str = "healthy"


class GenericProviderPlugin(ProviderPlugin):
    """Simple capability declaration plugin."""

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        capabilities: set[Capability],
    ) -> None:
        self.provider_id = provider_id
        self.display_name = display_name
        self.capabilities = capabilities


class HookedDownloadPlugin(GenericProviderPlugin, DownloadCapability):
    """Provider plugin with custom download hook contract."""

    async def download_entity(
        self,
        canonical_entity: dict[str, Any],
        relation_entity: dict[str, Any] | None,
        settings: dict[str, Any],
    ) -> DownloadHookResult:
        target = relation_entity or canonical_entity
        url = str(target.get("url") or canonical_entity.get("url") or "")
        artists = list(target.get("artists") or canonical_entity.get("artists") or [])
        artist = str(target.get("artist") or canonical_entity.get("artist") or "Unknown")
        title = str(target.get("name") or canonical_entity.get("name") or "Unknown")

        request = DownloadRequest(
            download_id=create_download_id(),
            url=url,
            title=title,
            artist=artist,
            artists=artists or [artist],
            album=target.get("album_name") or canonical_entity.get("album_name"),
            cover_url=target.get("cover_url") or canonical_entity.get("cover_url"),
            duration=target.get("duration") or canonical_entity.get("duration"),
            output_format=str(settings.get("output_format") or "mp3"),
            quality=str(settings.get("quality") or "best"),
            year=target.get("year") or canonical_entity.get("year"),
            isrc=target.get("isrc") or canonical_entity.get("isrc"),
            explicit=bool(target.get("explicit") or canonical_entity.get("explicit") or False),
            song_url=url,
        )

        manager = get_download_manager()
        await manager.start_download(request)
        return DownloadHookResult(
            download_id=request.download_id,
            status="started",
            provider_id=self.provider_id,
            used_provider_hook=True,
        )


class ProviderRegistry:
    """In-repo plugin registry for provider capabilities."""

    def __init__(self) -> None:
        self._plugins: dict[str, ProviderPlugin] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            HookedDownloadPlugin(
                provider_id="youtube_music",
                display_name="YouTube Music",
                capabilities={
                    Capability.RESOLVE,
                    Capability.SEARCH,
                    Capability.MATCH,
                    Capability.ENRICH,
                    Capability.DOWNLOAD,
                },
            )
        )
        self.register(
            HookedDownloadPlugin(
                provider_id="youtube",
                display_name="YouTube",
                capabilities={
                    Capability.MATCH,
                    Capability.DOWNLOAD,
                },
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="piped",
                display_name="Piped",
                capabilities={
                    Capability.MATCH,
                    Capability.DOWNLOAD,
                },
            )
        )
        self.register(
            HookedDownloadPlugin(
                provider_id="soundcloud",
                display_name="SoundCloud",
                capabilities={
                    Capability.RESOLVE,
                    Capability.SEARCH,
                    Capability.MATCH,
                    Capability.DOWNLOAD,
                    Capability.ENRICH,
                },
            )
        )
        self.register(
            HookedDownloadPlugin(
                provider_id="bandcamp",
                display_name="Bandcamp",
                capabilities={
                    Capability.RESOLVE,
                    Capability.SEARCH,
                    Capability.MATCH,
                    Capability.DOWNLOAD,
                    Capability.ENRICH,
                },
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="spotify",
                display_name="Spotify",
                capabilities={Capability.RESOLVE, Capability.SEARCH, Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="deezer",
                display_name="Deezer",
                capabilities={Capability.RESOLVE, Capability.SEARCH, Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="apple_music",
                display_name="Apple Music",
                capabilities={Capability.RESOLVE, Capability.SEARCH, Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="tidal",
                display_name="Tidal",
                capabilities={Capability.RESOLVE, Capability.SEARCH, Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="musicbrainz",
                display_name="MusicBrainz",
                capabilities={Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="discogs",
                display_name="Discogs",
                capabilities={Capability.ENRICH},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="genius",
                display_name="Genius",
                capabilities={Capability.LYRICS},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="musixmatch",
                display_name="Musixmatch",
                capabilities={Capability.LYRICS},
            )
        )
        self.register(
            GenericProviderPlugin(
                provider_id="synced",
                display_name="Synced Lyrics",
                capabilities={Capability.LYRICS},
            )
        )

    def register(self, plugin: ProviderPlugin) -> None:
        self._plugins[plugin.provider_id] = plugin

    def get(self, provider_id: str) -> ProviderPlugin | None:
        return self._plugins.get(provider_id)

    def all(self) -> list[ProviderPlugin]:
        return list(self._plugins.values())

    def get_with_capability(self, capability: Capability) -> list[ProviderPlugin]:
        return [plugin for plugin in self._plugins.values() if capability in plugin.capabilities]

    def health_matrix(self) -> list[ProviderHealth]:
        return [
            ProviderHealth(
                provider_id=plugin.provider_id,
                display_name=plugin.display_name,
                capabilities=plugin.capability_ids(),
                status="healthy",
            )
            for plugin in self._plugins.values()
        ]


_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
