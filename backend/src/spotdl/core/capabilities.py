"""Capability interfaces for unified provider plugins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class Capability(StrEnum):
    """Supported provider capabilities."""

    RESOLVE = "resolve"
    SEARCH = "search"
    MATCH = "match"
    ENRICH = "enrich"
    DOWNLOAD = "download"
    LYRICS = "lyrics"


@dataclass(slots=True)
class ProviderEntityBundle:
    """Normalized provider output for one or more entities."""

    provider_id: str
    provider_entity_id: str | None
    provider_url: str | None
    entity_type: str
    normalized_payload: dict[str, Any]
    raw_payload: dict[str, Any]
    confidence: float = 0.7


@dataclass(slots=True)
class ProviderMatch:
    """Match candidate emitted by MatchCapability."""

    provider_id: str
    entity_type: str
    normalized_payload: dict[str, Any]
    raw_payload: dict[str, Any]
    provider_entity_id: str | None
    provider_url: str | None
    score: float
    confidence: float


@dataclass(slots=True)
class DownloadHookResult:
    """Standardized provider download hook result."""

    download_id: str
    status: str
    provider_id: str
    used_provider_hook: bool


@runtime_checkable
class ResolveCapability(Protocol):
    async def resolve_url(self, url: str) -> list[ProviderEntityBundle]:
        """Resolve provider-specific URL into normalized entity bundles."""


@runtime_checkable
class SearchCapability(Protocol):
    async def search(
        self,
        query: str,
        entity_types: list[str],
        limit: int,
    ) -> list[ProviderEntityBundle]:
        """Search provider and return normalized entity bundles."""


@runtime_checkable
class MatchCapability(Protocol):
    async def find_matches(
        self,
        canonical_entity: dict[str, Any],
        target_provider_ids: list[str],
        limit: int,
    ) -> list[ProviderMatch]:
        """Find cross-provider relation candidates."""


@runtime_checkable
class EnrichCapability(Protocol):
    async def enrich(self, canonical_entity: dict[str, Any]) -> ProviderEntityBundle | None:
        """Fetch richer metadata snapshot for canonical entity."""


@runtime_checkable
class DownloadCapability(Protocol):
    async def download_entity(
        self,
        canonical_entity: dict[str, Any],
        relation_entity: dict[str, Any] | None,
        settings: dict[str, Any],
    ) -> DownloadHookResult:
        """Download via provider-specific custom logic."""


@runtime_checkable
class LyricsCapability(Protocol):
    async def get_lyrics(self, canonical_entity: dict[str, Any]) -> dict[str, Any] | None:
        """Fetch lyrics for canonical entity."""


class ProviderPlugin:
    """Base provider plugin with explicit capability declarations."""

    provider_id: str = "unknown"
    display_name: str = "Unknown"
    capabilities: set[Capability] = set()

    def capability_ids(self) -> list[str]:
        return sorted(cap.value for cap in self.capabilities)
