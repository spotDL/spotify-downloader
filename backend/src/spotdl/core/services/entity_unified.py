"""Unified entity service facade -- delegates to discovery, relations, and merge sub-modules."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.capabilities import (
    Capability,
    DownloadCapability,
    DownloadHookResult,
    ProviderEntityBundle,
)
from spotdl.core.provider_registry import get_provider_registry
from spotdl.core.services.discovery import (
    SOURCE_ID_TO_PLATFORM,
    DiscoverResult,
    DiscoveryService,
)
from spotdl.core.services.download import DownloadRequest, create_download_id
from spotdl.core.services.match import get_match_service
from spotdl.core.services.merge_engine import MergeEngine
from spotdl.core.services.relations import (
    RelationService,
    relation_confidence,  # noqa: F401 — re-exported
)
from spotdl.core.services.song import get_song_service
from spotdl.core.types.song import Song
from spotdl.core.utils.opengraph import _fetch_open_graph
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
)
from spotdl.providers.sources import extract_url_info
from spotdl.providers.targets import (
    BandcampProvider,
    SoundCloudProvider,
    YouTubeMusicProvider,
    YouTubeProvider,
)

logger = logging.getLogger(__name__)


class UnifiedEntityError(Exception):
    """Base exception for unified entity service."""


class EntityNotFoundError(UnifiedEntityError):
    """Raised when canonical entity does not exist."""


class CapabilityUnsupportedError(UnifiedEntityError):
    """Raised when requested capability is unavailable for an entity/provider."""


@dataclass(slots=True)
class RefreshResult:
    entity: Entity
    refreshed_snapshots: int
    failed_providers: list[dict[str, str]]


class UnifiedEntityService:
    """Canonical entity orchestration with provider snapshots and capabilities."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session
        self._song_service = get_song_service()
        self._registry = get_provider_registry()
        self._merge = MergeEngine()
        self._target_providers = {
            "youtube": YouTubeProvider(),
            "youtube_music": YouTubeMusicProvider(),
            "soundcloud": SoundCloudProvider(),
            "bandcamp": BandcampProvider(),
        }
        self._discovery = DiscoveryService(
            session,
            song_service=self._song_service,
            registry=self._registry,
            merge_engine=self._merge,
            target_providers=self._target_providers,
            fetch_open_graph_fn=_fetch_open_graph,
        )
        self._relations = RelationService(session)

    async def close(self) -> None:
        for name, provider in self._target_providers.items():
            try:
                await provider.close()
            except Exception as exc:
                logger.debug("Failed to close provider %s: %s", name, exc)
                continue

    async def discover(
        self,
        *,
        value: str,
        entity_types: list[str] | None = None,
        provider_ids: list[str] | None = None,
        limit: int = 20,
    ) -> DiscoverResult:
        return await self._discovery.discover(
            value=value,
            entity_types=entity_types,
            provider_ids=provider_ids,
            limit=limit,
        )

    async def discover_from_url(
        self,
        *,
        url: str,
        entity_types: list[str] | None = None,
        provider_ids: list[str] | None = None,
        limit: int = 20,
    ) -> DiscoverResult:
        return await self._discovery.discover_from_url(
            url=url,
            entity_types=entity_types,
            provider_ids=provider_ids,
            limit=limit,
        )

    async def discover_from_query(
        self,
        *,
        query: str,
        entity_types: list[str] | None = None,
        provider_ids: list[str] | None = None,
        limit: int = 20,
    ) -> DiscoverResult:
        return await self._discovery.discover_from_query(
            query=query,
            entity_types=entity_types,
            provider_ids=provider_ids,
            limit=limit,
        )

    async def get_entity(self, entity_id: uuid.UUID) -> Entity:
        return await self._discovery._get_entity(entity_id)

    async def get_entity_snapshots(
        self,
        entity_id: uuid.UUID,
    ) -> tuple[list[EntitySnapshot], list[EntityFieldProvenance]]:
        snapshots = await self._discovery._get_snapshots(entity_id)
        prov_query = (
            select(EntityFieldProvenance)
            .where(EntityFieldProvenance.entity_id == entity_id)
            .order_by(
                EntityFieldProvenance.field_name.asc(),
                EntityFieldProvenance.score.desc(),
            )
        )
        prov_result = await self._db.execute(prov_query)
        provenance = list(prov_result.scalars().all())
        return snapshots, provenance

    def _song_from_entity(
        self, entity: Entity, snapshots: list[EntitySnapshot], ec: EntityCanonical | None = None
    ) -> Song:
        return self._discovery._song_from_entity(entity, snapshots, ec)

    def _capability_map_for_entity(
        self, entity_type: str, provider_ids: list[str]
    ) -> dict[str, Any]:
        return self._discovery._capability_map_for_entity(entity_type, provider_ids)

    async def discover_relations(
        self,
        entity_id: uuid.UUID,
        *,
        target_provider_ids: list[str] | None = None,
        limit: int = 6,
    ) -> list[EntityRelation]:
        return await self._relations.discover_relations(
            entity_id,
            target_provider_ids=target_provider_ids,
            limit=limit,
            get_entity=self._discovery._get_entity,
            get_snapshots=self._discovery._get_snapshots,
            get_entity_canonical=self._discovery._get_entity_canonical,
            song_from_entity=self._song_from_entity,
            bundle_from_result=self._discovery._bundle_from_result,
            upsert_entity_snapshot=self._discovery._upsert_entity_snapshot,
            create_or_update_relation=self._discovery._create_or_update_relation,
            match_service_factory=get_match_service,
        )

    async def list_relations(
        self,
        entity_id: uuid.UUID,
        relation_type: str = "audio_match",
        limit: int = 50,
    ) -> list[EntityRelation]:
        return await self._relations.list_relations(entity_id, relation_type, limit)

    async def get_relation(self, relation_id: uuid.UUID) -> EntityRelation:
        return await self._relations.get_relation(relation_id)

    async def get_user_relation_vote(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> str | None:
        return await self._relations.get_user_relation_vote(relation_id, user_id)

    async def create_relation(
        self,
        from_entity_id: uuid.UUID,
        *,
        to_entity_id: uuid.UUID | None = None,
        to_url: str | None = None,
        relation_type: str = "audio_match",
        match_score: float | None = None,
        discovered_by: str = "user",
    ) -> EntityRelation:
        return await self._relations.create_relation(
            from_entity_id,
            to_entity_id=to_entity_id,
            to_url=to_url,
            relation_type=relation_type,
            match_score=match_score,
            discovered_by=discovered_by,
            get_entity=self._discovery._get_entity,
            discover_from_url=self.discover_from_url,
            create_or_update_relation=self._discovery._create_or_update_relation,
        )

    async def vote_relation(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID,
        vote_type: str | None,
    ) -> EntityRelation:
        return await self._relations.vote_relation(relation_id, user_id, vote_type)

    async def refresh_entity(
        self,
        entity_id: uuid.UUID,
        provider_ids: list[str] | None = None,
    ) -> RefreshResult:
        entity = await self._discovery._get_entity(entity_id)
        snapshots = await self._discovery._get_snapshots(entity_id)
        wanted = set(provider_ids or [snapshot.provider_id for snapshot in snapshots])

        refreshed = 0
        failed: list[dict[str, str]] = []

        for snapshot in snapshots:
            if snapshot.provider_id not in wanted:
                continue
            provider_url = snapshot.provider_url or ""
            try:
                bundle: ProviderEntityBundle | None = None
                source_platform = SOURCE_ID_TO_PLATFORM.get(snapshot.provider_id)
                if source_platform and provider_url:
                    info = extract_url_info(provider_url)
                    source_type = (info.get("type") or "track").lower()
                    if source_type == "track":
                        track = await self._song_service.get_track(provider_url, enrich=True)
                        bundle = self._discovery._bundle_from_song(track)
                    elif source_type == "album":
                        album = await self._song_service.get_album(provider_url)
                        bundle = self._discovery._bundle_from_songlist(album, "album")
                        # Rebuild track relations
                        current_track_ids: set[uuid.UUID] = set()
                        for track in album.songs:
                            track_bundle = self._discovery._bundle_from_song(track)
                            track_entity, _ = await self._discovery._upsert_entity_snapshot(
                                track_bundle
                            )
                            current_track_ids.add(track_entity.id)
                            await self._discovery._create_or_update_relation(
                                entity_id,
                                track_entity.id,
                                "contains",
                                None,
                                snapshot.provider_id,
                                relation_data={"position": track.track_number},
                            )
                        await self._cleanup_stale_relations(
                            entity_id, "contains", current_track_ids
                        )
                    elif source_type == "artist":
                        artist = await self._song_service.get_artist(provider_url)
                        bundle = self._discovery._bundle_from_songlist(artist, "artist")
                        # Rebuild track relations
                        current_track_ids_artist: set[uuid.UUID] = set()
                        for track in artist.songs:
                            track_bundle = self._discovery._bundle_from_song(track)
                            track_entity, _ = await self._discovery._upsert_entity_snapshot(
                                track_bundle
                            )
                            current_track_ids_artist.add(track_entity.id)
                            await self._discovery._create_or_update_relation(
                                entity_id,
                                track_entity.id,
                                "performed",
                                None,
                                snapshot.provider_id,
                            )
                        await self._cleanup_stale_relations(
                            entity_id, "performed", current_track_ids_artist
                        )
                    elif source_type == "playlist":
                        playlist = await self._song_service.get_playlist(provider_url)
                        bundle = self._discovery._bundle_from_songlist(playlist, "playlist")
                        # Rebuild track relations
                        current_track_ids_playlist: set[uuid.UUID] = set()
                        for idx, track in enumerate(playlist.songs):
                            track_bundle = self._discovery._bundle_from_song(track)
                            track_entity, _ = await self._discovery._upsert_entity_snapshot(
                                track_bundle
                            )
                            current_track_ids_playlist.add(track_entity.id)
                            await self._discovery._create_or_update_relation(
                                entity_id,
                                track_entity.id,
                                "contains",
                                None,
                                snapshot.provider_id,
                                relation_data={"position": idx + 1},
                            )
                        await self._cleanup_stale_relations(
                            entity_id, "contains", current_track_ids_playlist
                        )
                elif snapshot.provider_id in self._target_providers and provider_url:
                    bundle = await self._discovery._resolve_target_url(
                        provider_url, snapshot.provider_id
                    )
                elif snapshot.provider_id == "open_graph" and provider_url:
                    og_payload = await _fetch_open_graph(provider_url)
                    if og_payload:
                        bundle = self._discovery._bundle_from_open_graph(provider_url, og_payload)

                if bundle is None:
                    failed.append(
                        {
                            "provider_id": snapshot.provider_id,
                            "error": "Refresh capability not available for provider/url",
                        }
                    )
                    continue

                bundle.provider_entity_id = snapshot.provider_entity_id or bundle.provider_entity_id
                await self._discovery._upsert_entity_snapshot(bundle)
                refreshed += 1
            except Exception as exc:
                logger.warning(
                    "Refresh failed for provider %s on entity %s: %s",
                    snapshot.provider_id,
                    entity_id,
                    exc,
                )
                failed.append(
                    {
                        "provider_id": snapshot.provider_id,
                        "error": str(exc),
                    }
                )

        ec = await self._merge.merge(self._db, entity)
        ec.capabilities = self._discovery._capability_map_for_entity(
            entity.entity_type,
            [snapshot.provider_id for snapshot in await self._discovery._get_snapshots(entity.id)],
        )
        await self._db.flush()
        return RefreshResult(entity=entity, refreshed_snapshots=refreshed, failed_providers=failed)

    async def download_entity(
        self,
        entity_id: uuid.UUID,
        *,
        relation_id: uuid.UUID | None = None,
        provider_id: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings = settings or {}
        entity = await self._discovery._get_entity(entity_id)
        snapshots = await self._discovery._get_snapshots(entity_id)
        ec = await self._discovery._get_entity_canonical(entity_id)
        if entity.entity_type != "track":
            raise CapabilityUnsupportedError("Download is only supported for track entities.")

        relation: EntityRelation | None = None
        relation_entity: Entity | None = None
        relation_ec: EntityCanonical | None = None
        if relation_id:
            relation_query = select(EntityRelation).where(EntityRelation.id == relation_id)
            relation_result = await self._db.execute(relation_query)
            relation = relation_result.scalar_one_or_none()
            if relation is None:
                raise EntityNotFoundError(f"Relation not found: {relation_id}")
            relation_entity = await self._discovery._get_entity(relation.to_entity_id)
            relation_ec = await self._discovery._get_entity_canonical(relation.to_entity_id)
        else:
            relations = await self.list_relations(entity_id)
            relation = relations[0] if relations else None
            if relation:
                relation_entity = await self._discovery._get_entity(relation.to_entity_id)
                relation_ec = await self._discovery._get_entity_canonical(relation.to_entity_id)

        canonical = (ec.canonical if ec else None) or {}
        relation_payload = (relation_ec.canonical if relation_ec else None) or (
            None if relation_entity is None else {}
        )

        candidate_provider = provider_id
        if not candidate_provider and relation and relation.relation_data:
            candidate_provider = str(relation.relation_data.get("provider_id") or "")
        if not candidate_provider and snapshots:
            candidate_provider = snapshots[0].provider_id

        plugin = self._registry.get(candidate_provider or "") if candidate_provider else None
        if (
            plugin is not None
            and Capability.DOWNLOAD in plugin.capabilities
            and isinstance(plugin, DownloadCapability)
        ):
            try:
                hook_result: DownloadHookResult = await plugin.download_entity(
                    canonical_entity=canonical,
                    relation_entity=relation_payload,
                    settings=settings,
                )
                return {
                    "download_id": hook_result.download_id,
                    "status": hook_result.status,
                    "provider_id": hook_result.provider_id,
                    "used_provider_hook": hook_result.used_provider_hook,
                    "fallback_used": False,
                }
            except Exception as exc:
                logger.warning(
                    "Provider hook download failed for provider %s: %s; falling back.",
                    candidate_provider,
                    exc,
                )

        target = relation_payload or canonical
        url = str(target.get("url") or canonical.get("url") or "")
        if not url:
            raise CapabilityUnsupportedError("No downloadable URL available for entity.")

        entity_name = ec.name if ec else "Unknown"
        artist = str(target.get("artist") or canonical.get("artist") or "Unknown")
        artists = list(target.get("artists") or canonical.get("artists") or [artist])
        title = str(target.get("name") or canonical.get("name") or entity_name)

        download_id = create_download_id()
        request = DownloadRequest(
            download_id=download_id,
            url=url,
            title=title,
            artist=artist,
            artists=[str(item) for item in artists if str(item).strip()] or [artist],
            album=target.get("album_name") or canonical.get("album_name"),
            cover_url=target.get("cover_url") or canonical.get("cover_url"),
            duration=target.get("duration") or canonical.get("duration"),
            output_format=str(settings.get("output_format") or "mp3"),
            quality=str(settings.get("quality") or "best"),
            year=target.get("year") or canonical.get("year"),
            isrc=target.get("isrc") or canonical.get("isrc"),
            explicit=bool(target.get("explicit") or canonical.get("explicit") or False),
            song_url=url,
        )
        from spotdl.core.services.download import get_download_service

        manager = get_download_service()
        await manager.start_download(request)
        return {
            "download_id": download_id,
            "status": "started",
            "provider_id": candidate_provider or "fallback",
            "used_provider_hook": False,
            "fallback_used": True,
        }

    async def _cleanup_stale_relations(
        self,
        from_entity_id: uuid.UUID,
        relation_type: str,
        valid_target_ids: set[uuid.UUID],
    ) -> int:
        """Delete relations from entity that point to targets not in valid_target_ids."""
        if not valid_target_ids:
            return 0
        result = await self._db.execute(
            delete(EntityRelation).where(
                and_(
                    EntityRelation.from_entity_id == from_entity_id,
                    EntityRelation.relation_type == relation_type,
                    EntityRelation.to_entity_id.not_in(valid_target_ids),
                )
            )
        )
        return result.rowcount or 0

    async def _upsert_entity_snapshot(
        self, bundle: ProviderEntityBundle
    ) -> tuple[Entity, bool]:
        return await self._discovery._upsert_entity_snapshot(bundle)

    async def _get_entity(self, entity_id: uuid.UUID) -> Entity:
        return await self._discovery._get_entity(entity_id)

    async def _get_entity_canonical(self, entity_id: uuid.UUID) -> EntityCanonical | None:
        return await self._discovery._get_entity_canonical(entity_id)

    async def _get_snapshots(self, entity_id: uuid.UUID) -> list[EntitySnapshot]:
        return await self._discovery._get_snapshots(entity_id)

    def _bundle_from_song_artist(self, song: Song) -> ProviderEntityBundle | None:
        return self._discovery._bundle_from_song_artist(song)

    def _bundle_from_song_album(self, song: Song) -> ProviderEntityBundle | None:
        return self._discovery._bundle_from_song_album(song)

    def _bundle_from_open_graph(
        self, url: str, og_payload: dict[str, Any]
    ) -> ProviderEntityBundle:
        return self._discovery._bundle_from_open_graph(url, og_payload)

    @staticmethod
    def _normalize_isrc(isrc: str | None) -> str | None:
        return DiscoveryService._normalize_isrc(isrc)
