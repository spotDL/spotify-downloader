"""Unified entity service for capability-driven discovery, merge, relations, and downloads."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.capabilities import (
    Capability,
    DownloadCapability,
    DownloadHookResult,
    ProviderEntityBundle,
)
from spotdl.core.provider_registry import get_provider_registry
from spotdl.core.services.download import DownloadRequest, create_download_id
from spotdl.core.services.match import get_match_service
from spotdl.core.services.song import SongServiceError, UnsupportedURLError, get_song_service
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song, SongList
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
    RelationVote,
)
from spotdl.providers.sources import detect_platform, extract_url_info
from spotdl.providers.targets import (
    BandcampProvider,
    SoundCloudProvider,
    YouTubeMusicProvider,
    YouTubeProvider,
)

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_PRIORITIES: dict[str, float] = {
    "spotify": 1.0,
    "apple_music": 0.95,
    "deezer": 0.92,
    "tidal": 0.9,
    "youtube_music": 0.88,
    "youtube": 0.84,
    "soundcloud": 0.82,
    "bandcamp": 0.8,
    "musicbrainz": 0.78,
    "discogs": 0.76,
    "open_graph": 0.45,
}

SOURCE_PLATFORM_TO_ID: dict[Platform, str] = {
    Platform.SPOTIFY: "spotify",
    Platform.APPLE_MUSIC: "apple_music",
    Platform.DEEZER: "deezer",
    Platform.TIDAL: "tidal",
    Platform.YOUTUBE_MUSIC: "youtube_music",
    Platform.SOUNDCLOUD: "soundcloud",
    Platform.BANDCAMP: "bandcamp",
}

SOURCE_ID_TO_PLATFORM: dict[str, Platform] = {
    value: key for key, value in SOURCE_PLATFORM_TO_ID.items()
}

TARGET_ID_TO_PLATFORM: dict[str, TargetPlatform] = {
    "youtube": TargetPlatform.YOUTUBE,
    "youtube_music": TargetPlatform.YOUTUBE_MUSIC,
    "soundcloud": TargetPlatform.SOUNDCLOUD,
    "bandcamp": TargetPlatform.BANDCAMP,
    "piped": TargetPlatform.PIPED,
}


class UnifiedEntityError(Exception):
    """Base exception for unified entity service."""


class EntityNotFoundError(UnifiedEntityError):
    """Raised when canonical entity does not exist."""


class CapabilityUnsupportedError(UnifiedEntityError):
    """Raised when requested capability is unavailable for an entity/provider."""


@dataclass(slots=True)
class DiscoverResult:
    entities: list[Entity]
    relations: dict[str, list[EntityRelation]]
    created_entities: int = 0


@dataclass(slots=True)
class RefreshResult:
    entity: Entity
    refreshed_snapshots: int
    failed_providers: list[dict[str, str]]


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _safe_lower(text: str | None) -> str:
    return (text or "").strip().lower()


def _primary_artist(payload: dict[str, Any]) -> str:
    artists = payload.get("artists")
    if isinstance(artists, list) and artists and isinstance(artists[0], str):
        return artists[0]
    artist = payload.get("artist")
    if isinstance(artist, str) and artist.strip():
        return artist.strip()
    return "Unknown"


def _detect_target_platform(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    if "music.youtube.com" in host:
        return "youtube_music"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "soundcloud.com" in host:
        return "soundcloud"
    if "bandcamp.com" in host:
        return "bandcamp"
    return None


def _url_hash(url: str) -> str:
    """Stable short hash of a URL for use as provider_entity_id."""
    return hashlib.sha256(url.encode()).hexdigest()[:32]


def _extract_meta_tag(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
        tag = soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return str(tag.get("content")).strip() or None
    return None


async def _fetch_open_graph(url: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; SpotDLUnifiedBot/1.0; "
                    "+https://github.com/spotDL/spotify-downloader)"
                )
            },
        ) as client:
            response = await client.get(url)
    except Exception:
        return None

    if response.status_code >= 400 or not response.text:
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        return None

    title = _extract_meta_tag(soup, "og:title", "twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    description = _extract_meta_tag(soup, "og:description", "twitter:description", "description")
    site_name = _extract_meta_tag(soup, "og:site_name")
    image = _extract_meta_tag(soup, "og:image", "twitter:image")
    if image:
        image = urljoin(str(response.url), image)

    if not title and not description and not site_name and not image:
        return None

    return {
        "name": title or "Untitled",
        "artist": site_name or "Unknown",
        "artists": [site_name] if site_name else [],
        "description": description,
        "cover_url": image,
        "url": str(response.url),
        "site_name": site_name,
    }


class MergeEngine:
    """Field-level canonical merge with confidence, priority, recency, and validation."""

    def __init__(self, provider_priorities: dict[str, float] | None = None) -> None:
        self._priorities = provider_priorities or DEFAULT_PROVIDER_PRIORITIES

    def _priority(self, provider_id: str) -> float:
        return self._priorities.get(provider_id, 0.6)

    def _recency_factor(self, fetched_at: datetime) -> float:
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        else:
            fetched_at = fetched_at.astimezone(UTC)

        age_seconds = max((_now_utc() - fetched_at).total_seconds(), 0.0)
        age_days = age_seconds / 86400.0
        if age_days <= 1:
            return 1.0
        if age_days >= 180:
            return 0.5
        return max(0.5, 1.0 - (age_days / 360.0))

    def _field_validator_score(self, field_name: str, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            clean = value.strip()
            if not clean:
                return 0.0
            if field_name in {"url", "cover_url"}:
                return 1.0 if clean.startswith("http") else 0.1
            if field_name in {"name", "artist"}:
                return 1.0 if len(clean) >= 2 else 0.4
            return 1.0
        if isinstance(value, (int, float)):
            if field_name == "duration":
                return 1.0 if 10 <= int(value) <= 7200 else 0.35
            return 1.0
        if isinstance(value, list):
            return 0.0 if not value else 1.0
        if isinstance(value, dict):
            return 0.0 if not value else 1.0
        return 1.0

    def _score(self, snapshot: EntitySnapshot, field_name: str, value: Any) -> float:
        return (
            self._priority(snapshot.provider_id)
            * max(snapshot.confidence, 0.01)
            * self._recency_factor(snapshot.fetched_at)
            * self._field_validator_score(field_name, value)
        )

    async def merge(self, session: AsyncSession, entity: Entity) -> EntityCanonical:
        """Merge snapshots into EntityCanonical (create or update)."""
        snapshots_query = (
            select(EntitySnapshot)
            .where(EntitySnapshot.entity_id == entity.id)
            .order_by(desc(EntitySnapshot.fetched_at))
        )
        snapshots_result = await session.execute(snapshots_query)
        snapshots = list(snapshots_result.scalars().all())

        # Get or create EntityCanonical
        canonical_query = select(EntityCanonical).where(EntityCanonical.entity_id == entity.id)
        canonical_result = await session.execute(canonical_query)
        ec = canonical_result.scalar_one_or_none()
        if ec is None:
            ec = EntityCanonical(entity_id=entity.id)
            session.add(ec)

        if not snapshots:
            ec.canonical = ec.canonical or {}
            ec.name = str(ec.canonical.get("name") or ec.name or "Unknown")
            ec.merge_version = (ec.merge_version or 0) + 1
            ec.quality_score = 0.0
            return ec

        all_fields: set[str] = set()
        for snapshot in snapshots:
            all_fields.update(snapshot.normalized_payload.keys())

        canonical: dict[str, Any] = {}
        provenance_rows: list[EntityFieldProvenance] = []
        selected_scores: list[float] = []

        for field_name in sorted(all_fields):
            candidates: list[tuple[EntitySnapshot, Any, float]] = []
            for snapshot in snapshots:
                if field_name not in snapshot.normalized_payload:
                    continue
                value = snapshot.normalized_payload.get(field_name)
                score = self._score(snapshot, field_name, value)
                if score <= 0:
                    continue
                candidates.append((snapshot, value, score))

            if not candidates:
                continue

            candidates.sort(key=lambda item: item[2], reverse=True)
            best_snapshot, best_value, best_score = candidates[0]
            canonical[field_name] = best_value
            selected_scores.append(best_score)

            for snapshot, _value, score in candidates:
                provenance_rows.append(
                    EntityFieldProvenance(
                        entity_id=entity.id,
                        field_name=field_name,
                        snapshot_id=snapshot.id,
                        score=score,
                        selected=snapshot.id == best_snapshot.id,
                        reason=(
                            f"priority={self._priority(snapshot.provider_id):.3f};"
                            f"confidence={snapshot.confidence:.3f};"
                            f"recency={self._recency_factor(snapshot.fetched_at):.3f}"
                        ),
                    )
                )

        await session.execute(
            delete(EntityFieldProvenance).where(EntityFieldProvenance.entity_id == entity.id)
        )
        if provenance_rows:
            session.add_all(provenance_rows)

        ec.canonical = canonical
        ec.name = str(canonical.get("name") or ec.name or "Unknown")
        ec.quality_score = (
            float(sum(selected_scores) / len(selected_scores)) if selected_scores else 0.0
        )
        ec.merge_version = (ec.merge_version or 0) + 1
        return ec


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

    async def close(self) -> None:
        for provider in self._target_providers.values():
            try:
                await provider.close()
            except Exception:
                continue

    def _bundle_from_song(self, song: Song) -> ProviderEntityBundle:
        provider_id = SOURCE_PLATFORM_TO_ID.get(song.platform, "unknown")
        payload = {
            "name": song.name,
            "artists": list(song.artists),
            "artist": song.artist,
            "duration": song.duration,
            "platform": provider_id,
            "platform_id": song.platform_id,
            "url": song.url,
            "album_name": song.album_name or None,
            "album_artist": song.album_artist or None,
            "album_id": song.album_id,
            "track_number": song.track_number,
            "disc_number": song.disc_number,
            "year": song.year or None,
            "date": song.date or None,
            "genres": list(song.genres) if song.genres else [],
            "isrc": song.isrc,
            "explicit": bool(song.explicit),
            "cover_url": song.cover_url,
            "entity_type": "track",
            "artist_id": song.artist_id,
            "list_name": song.list_name,
            "list_url": song.list_url,
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=song.platform_id,
            provider_url=song.url,
            entity_type="track",
            normalized_payload=payload,
            raw_payload=song.json,
            confidence=0.9,
        )

    def _bundle_from_song_artist(self, song: Song) -> ProviderEntityBundle | None:
        """Build artist bundle. Returns None if no real artist_id from the provider."""
        artist_name = (song.artist or "").strip()
        if not artist_name:
            return None
        if not song.artist_id:
            return None
        provider_id = SOURCE_PLATFORM_TO_ID.get(song.platform, "unknown")
        payload = {
            "name": artist_name,
            "artists": [artist_name],
            "artist": artist_name,
            "platform": provider_id,
            "platform_id": song.artist_id,
            "url": None,
            "cover_url": song.cover_url,
            "genres": list(song.genres) if song.genres else [],
            "entity_type": "artist",
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=song.artist_id,
            provider_url=None,
            entity_type="artist",
            normalized_payload=payload,
            raw_payload=payload,
            confidence=0.72,
        )

    def _bundle_from_song_album(self, song: Song) -> ProviderEntityBundle | None:
        """Build album bundle. Returns None if no real album_id from the provider."""
        album_name = (song.album_name or "").strip()
        if not album_name:
            return None
        if not song.album_id:
            return None
        provider_id = SOURCE_PLATFORM_TO_ID.get(song.platform, "unknown")
        payload = {
            "name": album_name,
            "artists": list(song.artists),
            "artist": song.artist,
            "platform": provider_id,
            "platform_id": song.album_id,
            "url": song.list_url if song.list_url and "/album/" in song.list_url else None,
            "cover_url": song.cover_url,
            "year": song.year or None,
            "track_count": song.tracks_count or None,
            "entity_type": "album",
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=song.album_id,
            provider_url=payload["url"],  # type: ignore[arg-type]
            entity_type="album",
            normalized_payload=payload,
            raw_payload=payload,
            confidence=0.74,
        )

    def _bundle_from_result(self, result: Result) -> ProviderEntityBundle:
        provider_id = result.platform.value
        payload = {
            "name": result.name,
            "artists": list(result.artists),
            "artist": result.artist,
            "duration": result.duration,
            "platform": provider_id,
            "platform_id": result.platform_id,
            "url": result.url,
            "album_name": result.album_name,
            "cover_url": result.cover_url,
            "views": result.views,
            "explicit": bool(result.explicit),
            "verified": bool(result.verified),
            "year": result.year,
            "track_number": result.track_number,
            "entity_type": "track",
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=result.platform_id,
            provider_url=result.url,
            entity_type="track",
            normalized_payload=payload,
            raw_payload=result.json,
            confidence=0.76,
        )

    def _bundle_from_songlist(self, songlist: SongList, entity_type: str) -> ProviderEntityBundle:
        provider_id = SOURCE_PLATFORM_TO_ID.get(songlist.platform, "unknown")
        info = extract_url_info(songlist.url)
        provider_entity_id = info.get("id") or songlist.url
        first_song = songlist.songs[0] if songlist.songs else None
        payload = {
            "name": songlist.name,
            "url": songlist.url,
            "platform": provider_id,
            "platform_id": provider_entity_id,
            "entity_type": entity_type,
            "track_count": len(songlist.songs),
            "cover_url": first_song.cover_url if first_song else None,
            "artists": list(first_song.artists) if first_song else [],
            "artist": first_song.artist if first_song else None,
            "year": first_song.year if first_song else None,
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=str(provider_entity_id),
            provider_url=songlist.url,
            entity_type=entity_type,
            normalized_payload=payload,
            raw_payload=songlist.json,
            confidence=0.9,
        )

    def _bundle_from_open_graph(self, url: str, og_payload: dict[str, Any]) -> ProviderEntityBundle:
        payload = {
            "name": og_payload.get("name") or "Untitled",
            "artists": og_payload.get("artists") or [],
            "artist": og_payload.get("artist") or "Unknown",
            "duration": 0,
            "url": og_payload.get("url") or url,
            "description": og_payload.get("description"),
            "cover_url": og_payload.get("cover_url"),
            "site_name": og_payload.get("site_name"),
            "entity_type": "track",
            "platform": "open_graph",
            "platform_id": _url_hash(og_payload.get("url") or url),
        }
        return ProviderEntityBundle(
            provider_id="open_graph",
            provider_entity_id=str(payload["platform_id"]),
            provider_url=url,
            entity_type="track",
            normalized_payload=payload,
            raw_payload=og_payload,
            confidence=0.42,
        )

    def _capability_map_for_entity(
        self, entity_type: str, provider_ids: Iterable[str]
    ) -> dict[str, Any]:
        map_keys = {
            "resolvable": Capability.RESOLVE,
            "matchable": Capability.MATCH,
            "downloadable": Capability.DOWNLOAD,
            "lyrics": Capability.LYRICS,
            "enrichable": Capability.ENRICH,
        }
        providers = list(dict.fromkeys(provider_ids))
        payload: dict[str, Any] = {}
        for key, cap in map_keys.items():
            capable: list[str] = []
            for provider_id in providers:
                plugin = self._registry.get(provider_id)
                if plugin and cap in plugin.capabilities:
                    capable.append(provider_id)
            if key in {"matchable", "downloadable", "lyrics"} and entity_type != "track":
                capable = []
            payload[key] = {
                "enabled": len(capable) > 0,
                "providers": capable,
            }
        return payload

    async def _get_entity(self, entity_id: uuid.UUID) -> Entity:
        query = select(Entity).where(Entity.id == entity_id)
        result = await self._db.execute(query)
        entity = result.scalar_one_or_none()
        if entity is None:
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
        return entity

    async def _get_entity_canonical(self, entity_id: uuid.UUID) -> EntityCanonical | None:
        query = select(EntityCanonical).where(EntityCanonical.entity_id == entity_id)
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def _get_snapshots(self, entity_id: uuid.UUID) -> list[EntitySnapshot]:
        query = (
            select(EntitySnapshot)
            .where(EntitySnapshot.entity_id == entity_id)
            .order_by(desc(EntitySnapshot.fetched_at))
        )
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def _refresh_entity_map(
        self,
        entities_by_key: dict[tuple[str, str], Entity],
        bundles: dict[tuple[str, str], ProviderEntityBundle],
    ) -> None:
        """Re-resolve entity references after ISRC merges may have deleted entities.

        During upsert, ISRC merge can delete duplicate entities and move their
        snapshots to a survivor. This re-queries each snapshot to get the
        current owning entity, ensuring relations point to live entities.
        """
        for key in list(entities_by_key.keys()):
            bundle = bundles.get(key)
            if bundle is None:
                continue
            snap_result = await self._db.execute(
                select(EntitySnapshot).where(
                    EntitySnapshot.provider_id == bundle.provider_id,
                    EntitySnapshot.provider_entity_id == bundle.provider_entity_id,
                )
            )
            snap = snap_result.scalar_one_or_none()
            if snap is None:
                entities_by_key.pop(key, None)
                continue
            current_entity_id = snap.entity_id
            old_entity = entities_by_key[key]
            if old_entity.id != current_entity_id:
                entities_by_key[key] = await self._get_entity(current_entity_id)

    async def _find_or_create_entity(self, bundle: ProviderEntityBundle) -> tuple[Entity, bool]:
        """Find existing entity by (provider_id, provider_entity_id) or create new one.

        Returns (entity, created) tuple.
        """
        # 1. Look up existing snapshot by global dedup key
        snapshot_query = select(EntitySnapshot).where(
            and_(
                EntitySnapshot.provider_id == bundle.provider_id,
                EntitySnapshot.provider_entity_id == bundle.provider_entity_id,
            )
        )
        snapshot_result = await self._db.execute(snapshot_query)
        existing_snapshot = snapshot_result.scalar_one_or_none()

        if existing_snapshot is not None:
            # Entity exists — update snapshot if data changed
            entity = await self._get_entity(existing_snapshot.entity_id)
            self._update_snapshot_if_changed(existing_snapshot, bundle)
            return entity, False

        # 2. No existing snapshot — create new Entity + Snapshot
        try:
            async with self._db.begin_nested():
                entity = Entity(entity_type=bundle.entity_type)
                self._db.add(entity)
                await self._db.flush()

                snapshot = self._create_snapshot(entity.id, bundle)
                self._db.add(snapshot)
                await self._db.flush()
        except IntegrityError:
            # Concurrent insert — re-query
            snapshot_result = await self._db.execute(snapshot_query)
            existing_snapshot = snapshot_result.scalar_one_or_none()
            if existing_snapshot is None:
                raise UnifiedEntityError(
                    f"Failed to create or load entity for ({bundle.provider_id}, {bundle.provider_entity_id})."
                )
            entity = await self._get_entity(existing_snapshot.entity_id)
            return entity, False

        # 3. For tracks, try ISRC cross-provider merge
        if bundle.entity_type == "track":
            entity = await self._try_isrc_merge(entity, bundle)

        # 4. Recompute EntityCanonical
        ec = await self._merge.merge(self._db, entity)
        ec.capabilities = self._capability_map_for_entity(
            entity.entity_type,
            [s.provider_id for s in await self._get_snapshots(entity.id)],
        )
        await self._db.flush()
        return entity, True

    def _create_snapshot(
        self, entity_id: uuid.UUID, bundle: ProviderEntityBundle
    ) -> EntitySnapshot:
        plugin = self._registry.get(bundle.provider_id)
        capability_ids = plugin.capability_ids() if plugin else []
        return EntitySnapshot(
            entity_id=entity_id,
            provider_id=bundle.provider_id,
            provider_entity_id=bundle.provider_entity_id,
            provider_url=bundle.provider_url,
            normalized_payload=bundle.normalized_payload,
            raw_payload=bundle.raw_payload,
            confidence=float(max(bundle.confidence, 0.01)),
            fetched_at=_now_utc(),
            capabilities={"provider_capabilities": capability_ids},
        )

    def _update_snapshot_if_changed(
        self, snapshot: EntitySnapshot, bundle: ProviderEntityBundle
    ) -> bool:
        plugin = self._registry.get(bundle.provider_id)
        capability_ids = plugin.capability_ids() if plugin else []
        normalized_confidence = float(max(bundle.confidence, 0.01))
        snapshot_capabilities = {"provider_capabilities": capability_ids}

        if (
            snapshot.provider_url != bundle.provider_url
            or snapshot.normalized_payload != bundle.normalized_payload
            or snapshot.raw_payload != bundle.raw_payload
            or not math.isclose(float(snapshot.confidence), normalized_confidence, rel_tol=1e-9)
            or snapshot.capabilities != snapshot_capabilities
        ):
            snapshot.provider_url = bundle.provider_url
            snapshot.normalized_payload = bundle.normalized_payload
            snapshot.raw_payload = bundle.raw_payload
            snapshot.confidence = normalized_confidence
            snapshot.fetched_at = _now_utc()
            snapshot.capabilities = snapshot_capabilities
            return True
        return False

    async def _try_isrc_merge(self, entity: Entity, bundle: ProviderEntityBundle) -> Entity:
        """Check for cross-provider merge via ISRC. Returns survivor entity."""
        isrc = bundle.normalized_payload.get("isrc")
        if not isrc or not isinstance(isrc, str) or not isrc.strip():
            return entity

        # Find other snapshots with same ISRC from different entities
        other_query = select(EntitySnapshot).where(
            EntitySnapshot.entity_id != entity.id,
            EntitySnapshot.normalized_payload["isrc"].as_string() == isrc,
        )
        other_result = await self._db.execute(other_query)
        other_snapshots = list(other_result.scalars().all())

        if not other_snapshots:
            return entity

        # Merge all duplicate entities into the oldest one (survivor)
        all_entity_ids = {entity.id} | {s.entity_id for s in other_snapshots}
        sorted_ids = sorted(all_entity_ids)
        survivor_id = sorted_ids[0]

        if survivor_id != entity.id:
            survivor = await self._get_entity(survivor_id)
        else:
            survivor = entity

        for eid in sorted_ids[1:]:
            if eid == survivor.id:
                continue
            duplicate = await self._get_entity(eid)
            await self._merge_entities(survivor, duplicate)

        return survivor

    async def _merge_entities(self, survivor: Entity, duplicate: Entity) -> None:
        """Move all data from duplicate to survivor and delete duplicate."""
        # Move snapshots
        await self._db.execute(
            update(EntitySnapshot)
            .where(EntitySnapshot.entity_id == duplicate.id)
            .values(entity_id=survivor.id)
        )

        # Move outgoing relations (handle unique constraint conflicts by skipping duplicates)
        outgoing_query = select(EntityRelation).where(EntityRelation.from_entity_id == duplicate.id)
        outgoing_result = await self._db.execute(outgoing_query)
        for rel in outgoing_result.scalars().all():
            existing = await self._db.execute(
                select(EntityRelation).where(
                    EntityRelation.from_entity_id == survivor.id,
                    EntityRelation.to_entity_id == rel.to_entity_id,
                    EntityRelation.relation_type == rel.relation_type,
                )
            )
            if existing.scalar_one_or_none() is None:
                rel.from_entity_id = survivor.id
            else:
                await self._db.delete(rel)

        # Move incoming relations
        incoming_query = select(EntityRelation).where(EntityRelation.to_entity_id == duplicate.id)
        incoming_result = await self._db.execute(incoming_query)
        for rel in incoming_result.scalars().all():
            existing = await self._db.execute(
                select(EntityRelation).where(
                    EntityRelation.from_entity_id == rel.from_entity_id,
                    EntityRelation.to_entity_id == survivor.id,
                    EntityRelation.relation_type == rel.relation_type,
                )
            )
            if existing.scalar_one_or_none() is None:
                rel.to_entity_id = survivor.id
            else:
                await self._db.delete(rel)

        # Move provenance
        await self._db.execute(
            update(EntityFieldProvenance)
            .where(EntityFieldProvenance.entity_id == duplicate.id)
            .values(entity_id=survivor.id)
        )

        # Delete duplicate's EntityCanonical (will be recomputed)
        await self._db.execute(
            delete(EntityCanonical).where(EntityCanonical.entity_id == duplicate.id)
        )

        # Delete duplicate entity
        await self._db.delete(duplicate)
        await self._db.flush()

    async def _upsert_entity_snapshot(self, bundle: ProviderEntityBundle) -> Entity:
        """Upsert via snapshot-based lookup. Wrapper around _find_or_create_entity
        that also handles re-merging for existing entities when data changes."""
        # Look up existing snapshot
        snapshot_query = select(EntitySnapshot).where(
            and_(
                EntitySnapshot.provider_id == bundle.provider_id,
                EntitySnapshot.provider_entity_id == bundle.provider_entity_id,
            )
        )
        snapshot_result = await self._db.execute(snapshot_query)
        existing_snapshot = snapshot_result.scalar_one_or_none()

        if existing_snapshot is not None:
            entity = await self._get_entity(existing_snapshot.entity_id)
            changed = self._update_snapshot_if_changed(existing_snapshot, bundle)

            # Get current canonical
            ec = await self._get_entity_canonical(entity.id)

            if not changed and ec is not None and ec.canonical:
                return entity

            # Recompute canonical
            await self._db.flush()
            ec = await self._merge.merge(self._db, entity)
            ec.capabilities = self._capability_map_for_entity(
                entity.entity_type,
                [s.provider_id for s in await self._get_snapshots(entity.id)],
            )
            await self._db.flush()
            return entity

        # Create new
        entity, _created = await self._find_or_create_entity(bundle)
        return entity

    async def _create_or_update_relation(
        self,
        from_entity_id: uuid.UUID,
        to_entity_id: uuid.UUID,
        relation_type: str,
        match_score: float | None,
        discovered_by: str,
        relation_data: dict[str, Any] | None = None,
    ) -> EntityRelation | None:
        # Skip self-referencing relations (can happen after ISRC merge)
        if from_entity_id == to_entity_id:
            return None

        query = select(EntityRelation).where(
            and_(
                EntityRelation.from_entity_id == from_entity_id,
                EntityRelation.to_entity_id == to_entity_id,
                EntityRelation.relation_type == relation_type,
            )
        )
        result = await self._db.execute(query)
        relation = result.scalar_one_or_none()
        if relation is None:
            try:
                async with self._db.begin_nested():
                    relation = EntityRelation(
                        from_entity_id=from_entity_id,
                        to_entity_id=to_entity_id,
                        relation_type=relation_type,
                        match_score=match_score,
                        status="suggested",
                        discovered_by=discovered_by,
                        relation_data=relation_data or {},
                    )
                    self._db.add(relation)
                    await self._db.flush()
            except IntegrityError:
                relation = None
                result = await self._db.execute(query)
                relation = result.scalar_one_or_none()

            if relation is None:
                # FK violation (entity deleted by concurrent merge) — skip gracefully
                logger.warning(
                    "Skipping relation %s -> %s (%s): entity no longer exists.",
                    from_entity_id,
                    to_entity_id,
                    relation_type,
                )
                return None

        relation.match_score = match_score
        relation.discovered_by = discovered_by
        if relation_data is not None:
            relation.relation_data = relation_data

        await self._db.flush()
        return relation

    async def _resolve_target_url(self, url: str, platform_id: str) -> ProviderEntityBundle | None:
        try:
            if platform_id == "youtube_music":
                provider = self._target_providers["youtube_music"]
                video_id = YouTubeMusicProvider.extract_video_id(url)
                if not video_id:
                    return None
                info = await provider.get_song_info(video_id)  # type: ignore[attr-defined]
                if not info:
                    return None
                return self._bundle_from_result(info)
            if platform_id == "youtube":
                provider = self._target_providers["youtube"]
                video_id = YouTubeProvider.extract_video_id(url)
                if not video_id:
                    return None
                info = await provider.get_video_info(video_id)  # type: ignore[attr-defined]
                if not info:
                    return None
                return self._bundle_from_result(info)
        except Exception:
            return None
        return None

    async def discover(
        self,
        *,
        value: str,
        entity_types: list[str] | None = None,
        provider_ids: list[str] | None = None,
        limit: int = 20,
    ) -> DiscoverResult:
        text = value.strip()
        if not text:
            return DiscoverResult(entities=[], relations={})
        if text.startswith("http://") or text.startswith("https://"):
            return await self.discover_from_url(
                url=text,
                entity_types=entity_types,
                provider_ids=provider_ids,
                limit=limit,
            )
        return await self.discover_from_query(
            query=text,
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
        del entity_types, provider_ids, limit
        created_entities = 0
        entities: list[Entity] = []
        relations: dict[str, list[EntityRelation]] = {}

        # Key: (provider_id, provider_entity_id) — the global dedup key
        bundles_to_upsert: dict[tuple[str, str], ProviderEntityBundle] = {}
        # Relations: (from_bundle_key, to_bundle_key, relation_type, discovered_by, relation_data)
        relations_to_create: list[
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None]
        ] = []

        source_platform = detect_platform(url)
        if source_platform is not None:
            url_info = extract_url_info(url)
            url_type = (url_info.get("type") or "track").lower()
            try:
                discovered_by = SOURCE_PLATFORM_TO_ID.get(source_platform, "system")
                if url_type == "album":
                    album = await self._song_service.get_album(url)
                    root_bundle = self._bundle_from_songlist(album, "album")
                    root_key = (root_bundle.provider_id, root_bundle.provider_entity_id)
                    bundles_to_upsert[root_key] = root_bundle
                    for track in album.songs:
                        track_bundle = self._bundle_from_song(track)
                        track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                        bundles_to_upsert[track_key] = track_bundle
                        relations_to_create.append(
                            (
                                root_key,
                                track_key,
                                "contains",
                                discovered_by,
                                {"position": track.track_number},
                            )
                        )
                        artist_bundle = self._bundle_from_song_artist(track)
                        if artist_bundle:
                            artist_key = (
                                artist_bundle.provider_id,
                                artist_bundle.provider_entity_id,
                            )
                            bundles_to_upsert[artist_key] = artist_bundle
                            relations_to_create.append(
                                (artist_key, root_key, "performed", discovered_by, None)
                            )
                            relations_to_create.append(
                                (artist_key, track_key, "performed", discovered_by, None)
                            )
                elif url_type == "artist":
                    artist = await self._song_service.get_artist(url)
                    root_bundle = self._bundle_from_songlist(artist, "artist")
                    root_key = (root_bundle.provider_id, root_bundle.provider_entity_id)
                    bundles_to_upsert[root_key] = root_bundle
                    for track in artist.songs:
                        track_bundle = self._bundle_from_song(track)
                        track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                        bundles_to_upsert[track_key] = track_bundle
                        relations_to_create.append(
                            (root_key, track_key, "performed", discovered_by, None)
                        )
                        album_bundle = self._bundle_from_song_album(track)
                        if album_bundle:
                            album_key = (album_bundle.provider_id, album_bundle.provider_entity_id)
                            bundles_to_upsert[album_key] = album_bundle
                            relations_to_create.append(
                                (
                                    album_key,
                                    track_key,
                                    "contains",
                                    discovered_by,
                                    {"track_number": track.track_number},
                                )
                            )
                            relations_to_create.append(
                                (root_key, album_key, "performed", discovered_by, None)
                            )
                elif url_type == "playlist":
                    playlist = await self._song_service.get_playlist(url)
                    root_bundle = self._bundle_from_songlist(playlist, "playlist")
                    root_key = (root_bundle.provider_id, root_bundle.provider_entity_id)
                    bundles_to_upsert[root_key] = root_bundle
                    for idx, track in enumerate(playlist.songs):
                        track_bundle = self._bundle_from_song(track)
                        track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                        bundles_to_upsert[track_key] = track_bundle
                        relations_to_create.append(
                            (root_key, track_key, "contains", discovered_by, {"position": idx + 1})
                        )
                        artist_bundle = self._bundle_from_song_artist(track)
                        if artist_bundle:
                            artist_key = (
                                artist_bundle.provider_id,
                                artist_bundle.provider_entity_id,
                            )
                            bundles_to_upsert[artist_key] = artist_bundle
                            relations_to_create.append(
                                (artist_key, track_key, "performed", discovered_by, None)
                            )
                        album_bundle = self._bundle_from_song_album(track)
                        if album_bundle:
                            album_key = (album_bundle.provider_id, album_bundle.provider_entity_id)
                            bundles_to_upsert[album_key] = album_bundle
                            relations_to_create.append(
                                (
                                    album_key,
                                    track_key,
                                    "contains",
                                    discovered_by,
                                    {"track_number": track.track_number},
                                )
                            )
                else:
                    track = await self._song_service.get_track(url, enrich=True)
                    track_bundle = self._bundle_from_song(track)
                    track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                    bundles_to_upsert[track_key] = track_bundle
                    artist_bundle = self._bundle_from_song_artist(track)
                    if artist_bundle:
                        artist_key = (artist_bundle.provider_id, artist_bundle.provider_entity_id)
                        bundles_to_upsert[artist_key] = artist_bundle
                        relations_to_create.append(
                            (artist_key, track_key, "performed", discovered_by, None)
                        )
                    album_bundle = self._bundle_from_song_album(track)
                    if album_bundle:
                        album_key = (album_bundle.provider_id, album_bundle.provider_entity_id)
                        bundles_to_upsert[album_key] = album_bundle
                        relations_to_create.append(
                            (
                                album_key,
                                track_key,
                                "contains",
                                discovered_by,
                                {"track_number": track.track_number},
                            )
                        )
            except (SongServiceError, UnsupportedURLError) as exc:
                logger.warning("Failed source discovery for %s: %s", url, exc)
                raise UnifiedEntityError(f"Failed to discover source URL: {exc}") from exc
        else:
            target_platform = _detect_target_platform(url)
            if target_platform:
                bundle = await self._resolve_target_url(url, target_platform)
                if bundle:
                    bundle_key = (bundle.provider_id, bundle.provider_entity_id)
                    bundles_to_upsert[bundle_key] = bundle
            if not bundles_to_upsert:
                og_payload = await _fetch_open_graph(url)
                if og_payload:
                    bundle = self._bundle_from_open_graph(url, og_payload)
                    bundle_key = (bundle.provider_id, bundle.provider_entity_id)
                    bundles_to_upsert[bundle_key] = bundle
                else:
                    raise UnifiedEntityError(f"Unsupported URL and no metadata available: {url}")

        entities_by_key: dict[tuple[str, str], Entity] = {}
        for key in sorted(bundles_to_upsert.keys()):
            entity = await self._upsert_entity_snapshot(bundles_to_upsert[key])
            entities_by_key[key] = entity
            entities.append(entity)
            created_entities += 1

        # Refresh entity references: ISRC merge may have replaced entities
        await self._refresh_entity_map(entities_by_key, bundles_to_upsert)

        # Deduplicate by (from_key, to_key, relation_type)
        unique_rel_map: dict[
            tuple[tuple[str, str], tuple[str, str], str],
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None],
        ] = {}
        for r in relations_to_create:
            unique_rel_map[(r[0], r[1], r[2])] = r

        for r_tuple in sorted(unique_rel_map.values(), key=lambda x: (x[0], x[1], x[2])):
            from_key, to_key, rel_type, provider_id, rel_data = r_tuple
            from_entity = entities_by_key.get(from_key)
            to_entity = entities_by_key.get(to_key)
            if from_entity is None or to_entity is None:
                continue
            relation = await self._create_or_update_relation(
                from_entity.id,
                to_entity.id,
                rel_type,
                None,
                provider_id,
                relation_data=rel_data,
            )
            if relation is not None:
                relations.setdefault(str(from_entity.id), []).append(relation)

        deduped: dict[str, Entity] = {}
        for entity in entities:
            deduped[str(entity.id)] = entity
        return DiscoverResult(
            entities=list(deduped.values()), relations=relations, created_entities=created_entities
        )

    async def discover_from_query(
        self,
        *,
        query: str,
        entity_types: list[str] | None = None,
        provider_ids: list[str] | None = None,
        limit: int = 20,
    ) -> DiscoverResult:
        requested_types = set(entity_types or ["track", "album", "artist", "playlist"])

        provider_filter = set(provider_ids or [])
        source_platforms = [
            platform
            for platform in self._song_service.supported_platforms
            if not provider_filter or SOURCE_PLATFORM_TO_ID.get(platform, "") in provider_filter
        ]

        async def search_source(platform: Platform) -> list[Song]:
            try:
                return await self._song_service.search(query, platform=platform, limit=limit)
            except Exception:
                return []

        source_tasks = [search_source(platform) for platform in source_platforms]
        source_results = await asyncio.gather(*source_tasks, return_exceptions=False)

        # Key: (provider_id, provider_entity_id)
        bundles_to_upsert: dict[tuple[str, str], ProviderEntityBundle] = {}
        relations_to_create: list[
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None]
        ] = []

        for songs in source_results:
            for song in songs:
                track_bundle = self._bundle_from_song(song)
                track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                bundles_to_upsert[track_key] = track_bundle

                artist_bundle = self._bundle_from_song_artist(song)
                if artist_bundle:
                    artist_key = (artist_bundle.provider_id, artist_bundle.provider_entity_id)
                    bundles_to_upsert[artist_key] = artist_bundle
                    relations_to_create.append(
                        (artist_key, track_key, "performed", artist_bundle.provider_id, None)
                    )

                album_bundle = self._bundle_from_song_album(song)
                if album_bundle:
                    album_key = (album_bundle.provider_id, album_bundle.provider_entity_id)
                    bundles_to_upsert[album_key] = album_bundle
                    relations_to_create.append(
                        (
                            album_key,
                            track_key,
                            "contains",
                            album_bundle.provider_id,
                            {"track_number": song.track_number},
                        )
                    )
                    if artist_bundle:
                        relations_to_create.append(
                            (artist_key, album_key, "performed", album_bundle.provider_id, None)
                        )

        entities: list[Entity] = []
        entities_by_key: dict[tuple[str, str], Entity] = {}
        for key in sorted(bundles_to_upsert.keys()):
            entity = await self._upsert_entity_snapshot(bundles_to_upsert[key])
            entities_by_key[key] = entity
            entities.append(entity)

        # Refresh entity references: ISRC merge may have replaced entities
        await self._refresh_entity_map(entities_by_key, bundles_to_upsert)

        # Deduplicate relations
        unique_relations: dict[
            tuple[tuple[str, str], tuple[str, str], str],
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None],
        ] = {}
        for r in relations_to_create:
            unique_relations[(r[0], r[1], r[2])] = r

        for r_tuple in sorted(unique_relations.values(), key=lambda x: (x[0], x[1], x[2])):
            from_key, to_key, rel_type, provider_id, rel_data = r_tuple
            from_entity = entities_by_key.get(from_key)
            to_entity = entities_by_key.get(to_key)
            if from_entity is None or to_entity is None:
                continue
            await self._create_or_update_relation(
                from_entity.id,
                to_entity.id,
                rel_type,
                None,
                provider_id,
                relation_data=rel_data,
            )

        # Query target providers
        pseudo_song = Song(
            name=query,
            artists=[query],
            artist=query,
            duration=180,
            platform=Platform.SPOTIFY,
            platform_id=_safe_lower(query) or "query",
            url=f"query:{query}",
        )

        target_ids = [
            provider_id
            for provider_id in self._target_providers
            if (not provider_filter or provider_id in provider_filter)
        ]
        if target_ids:
            match_service = get_match_service()
            target_platforms = [
                TARGET_ID_TO_PLATFORM[provider_id]
                for provider_id in target_ids
                if provider_id in TARGET_ID_TO_PLATFORM
            ]
            try:
                matches = await match_service.find_matches(
                    pseudo_song,
                    target_platforms=target_platforms or None,
                    limit=max(1, min(limit, 10)),
                )
            except Exception:
                matches = []
            for match in matches:
                entity = await self._upsert_entity_snapshot(
                    self._bundle_from_result(match.target_result)
                )
                entities.append(entity)

        filtered_entities = [entity for entity in entities if entity.entity_type in requested_types]

        deduped: dict[str, Entity] = {}
        for entity in filtered_entities:
            deduped[str(entity.id)] = entity

        return DiscoverResult(
            entities=list(deduped.values())[:limit],
            relations={},
            created_entities=len(deduped),
        )

    async def get_entity(self, entity_id: uuid.UUID) -> Entity:
        return await self._get_entity(entity_id)

    async def get_entity_snapshots(
        self,
        entity_id: uuid.UUID,
    ) -> tuple[list[EntitySnapshot], list[EntityFieldProvenance]]:
        snapshots = await self._get_snapshots(entity_id)
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
        canonical = (ec.canonical if ec else None) or {}
        preferred_provider = snapshots[0].provider_id if snapshots else "spotify"
        source_platform = SOURCE_ID_TO_PLATFORM.get(preferred_provider, Platform.SPOTIFY)
        platform_id = str(
            canonical.get("platform_id")
            or (snapshots[0].provider_entity_id if snapshots else str(entity.id))
        )
        url = str(canonical.get("url") or (snapshots[0].provider_url if snapshots else ""))
        artists = canonical.get("artists")
        if not isinstance(artists, list) or not artists:
            artists = [str(canonical.get("artist") or "Unknown")]
        return Song(
            name=str(canonical.get("name") or (ec.name if ec else "Unknown")),
            artists=[str(artist) for artist in artists],
            artist=str(canonical.get("artist") or artists[0]),
            duration=int(canonical.get("duration") or 180),
            platform=source_platform,
            platform_id=platform_id,
            url=url,
            album_name=str(canonical.get("album_name") or ""),
            album_artist=str(canonical.get("album_artist") or ""),
            album_id=canonical.get("album_id"),
            track_number=int(canonical.get("track_number") or 1),
            disc_number=int(canonical.get("disc_number") or 1),
            year=int(canonical.get("year") or 0),
            date=str(canonical.get("date") or ""),
            genres=list(canonical.get("genres") or []),
            isrc=canonical.get("isrc"),
            explicit=bool(canonical.get("explicit") or False),
            cover_url=canonical.get("cover_url"),
        )

    async def discover_relations(
        self,
        entity_id: uuid.UUID,
        *,
        target_provider_ids: list[str] | None = None,
        limit: int = 6,
    ) -> list[EntityRelation]:
        entity = await self._get_entity(entity_id)
        if entity.entity_type != "track":
            return []

        snapshots = await self._get_snapshots(entity.id)
        ec = await self._get_entity_canonical(entity.id)
        song = self._song_from_entity(entity, snapshots, ec)

        target_provider_ids = target_provider_ids or [
            "youtube_music",
            "youtube",
            "soundcloud",
            "bandcamp",
        ]
        target_platforms = [
            TARGET_ID_TO_PLATFORM[provider_id]
            for provider_id in target_provider_ids
            if provider_id in TARGET_ID_TO_PLATFORM
        ]

        match_service = get_match_service()
        matches = await match_service.find_matches(
            song,
            target_platforms=target_platforms or None,
            limit=limit,
        )

        relations: list[EntityRelation] = []
        for match in matches:
            bundle = self._bundle_from_result(match.target_result)
            target_entity = await self._upsert_entity_snapshot(bundle)
            relation = await self._create_or_update_relation(
                entity.id,
                target_entity.id,
                "audio_match",
                float(match.score),
                bundle.provider_id,
                relation_data={
                    "confidence": match.confidence,
                    "provider_id": bundle.provider_id,
                    "target_url": bundle.provider_url,
                },
            )
            if relation is not None:
                relations.append(relation)

        await self._db.flush()
        return relations

    async def list_relations(
        self,
        entity_id: uuid.UUID,
        relation_type: str = "audio_match",
    ) -> list[EntityRelation]:
        query = (
            select(EntityRelation)
            .where(
                and_(
                    EntityRelation.from_entity_id == entity_id,
                    EntityRelation.relation_type == relation_type,
                )
            )
            .order_by(
                desc(EntityRelation.match_score),
                desc(EntityRelation.upvotes - EntityRelation.downvotes),
                desc(EntityRelation.updated_at),
            )
        )
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_relation(self, relation_id: uuid.UUID) -> EntityRelation:
        query = select(EntityRelation).where(EntityRelation.id == relation_id)
        result = await self._db.execute(query)
        relation = result.scalar_one_or_none()
        if relation is None:
            raise EntityNotFoundError(f"Relation not found: {relation_id}")
        return relation

    async def get_user_relation_vote(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> str | None:
        if user_id is None:
            return None
        query = select(RelationVote).where(
            and_(
                RelationVote.relation_id == relation_id,
                RelationVote.user_id == user_id,
            )
        )
        result = await self._db.execute(query)
        vote = result.scalar_one_or_none()
        return vote.vote_type if vote is not None else None

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
        from_entity = await self._get_entity(from_entity_id)
        if from_entity.entity_type != "track":
            raise CapabilityUnsupportedError(
                "Manual relation creation is supported only for track entities."
            )

        resolved_target_id = to_entity_id
        if resolved_target_id is None and to_url:
            discovered = await self.discover_from_url(url=to_url)
            track_entities = [
                entity for entity in discovered.entities if entity.entity_type == "track"
            ]
            if not track_entities:
                raise UnifiedEntityError("Unable to resolve target URL into a track entity.")
            resolved_target_id = track_entities[0].id

        if resolved_target_id is None:
            raise UnifiedEntityError("Provide either to_entity_id or to_url.")

        _ = await self._get_entity(resolved_target_id)
        relation = await self._create_or_update_relation(
            from_entity_id=from_entity_id,
            to_entity_id=resolved_target_id,
            relation_type=relation_type,
            match_score=match_score,
            discovered_by=discovered_by,
            relation_data={"manual": True},
        )
        if relation is None:
            raise UnifiedEntityError("Cannot create a relation between the same entity.")
        return relation

    async def vote_relation(
        self,
        relation_id: uuid.UUID,
        user_id: uuid.UUID,
        vote_type: str | None,
    ) -> EntityRelation:
        relation_query = select(EntityRelation).where(EntityRelation.id == relation_id)
        relation_result = await self._db.execute(relation_query)
        relation = relation_result.scalar_one_or_none()
        if relation is None:
            raise EntityNotFoundError(f"Relation not found: {relation_id}")

        vote_query = select(RelationVote).where(
            and_(
                RelationVote.relation_id == relation_id,
                RelationVote.user_id == user_id,
            )
        )
        vote_result = await self._db.execute(vote_query)
        vote = vote_result.scalar_one_or_none()

        normalized_vote = (vote_type or "").strip().lower() or None
        if normalized_vote not in {"up", "down", None}:
            raise UnifiedEntityError("Invalid vote type. Expected 'up', 'down', or null/remove.")

        if normalized_vote is None:
            if vote is not None:
                await self._db.delete(vote)
        else:
            if vote is None:
                try:
                    async with self._db.begin_nested():
                        vote = RelationVote(
                            relation_id=relation_id,
                            user_id=user_id,
                            vote_type=normalized_vote,
                        )
                        self._db.add(vote)
                        await self._db.flush()
                except IntegrityError:
                    vote_result = await self._db.execute(vote_query)
                    vote = vote_result.scalar_one_or_none()
                    if vote is None:
                        raise UnifiedEntityError(
                            "Failed to create or load relation vote after concurrent insert."
                        ) from None
                    vote.vote_type = normalized_vote
            else:
                vote.vote_type = normalized_vote

        await self._db.flush()

        summary_query = select(
            func.count().filter(RelationVote.vote_type == "up"),
            func.count().filter(RelationVote.vote_type == "down"),
        ).where(RelationVote.relation_id == relation_id)
        summary = await self._db.execute(summary_query)
        upvotes, downvotes = summary.one()
        relation.upvotes = int(upvotes or 0)
        relation.downvotes = int(downvotes or 0)
        await self._db.flush()
        return relation

    async def refresh_entity(
        self,
        entity_id: uuid.UUID,
        provider_ids: list[str] | None = None,
    ) -> RefreshResult:
        entity = await self._get_entity(entity_id)
        snapshots = await self._get_snapshots(entity_id)
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
                        bundle = self._bundle_from_song(track)
                    elif source_type == "album":
                        album = await self._song_service.get_album(provider_url)
                        bundle = self._bundle_from_songlist(album, "album")
                    elif source_type == "artist":
                        artist = await self._song_service.get_artist(provider_url)
                        bundle = self._bundle_from_songlist(artist, "artist")
                    elif source_type == "playlist":
                        playlist = await self._song_service.get_playlist(provider_url)
                        bundle = self._bundle_from_songlist(playlist, "playlist")
                elif snapshot.provider_id in self._target_providers and provider_url:
                    bundle = await self._resolve_target_url(provider_url, snapshot.provider_id)
                elif snapshot.provider_id == "open_graph" and provider_url:
                    og_payload = await _fetch_open_graph(provider_url)
                    if og_payload:
                        bundle = self._bundle_from_open_graph(provider_url, og_payload)

                if bundle is None:
                    failed.append(
                        {
                            "provider_id": snapshot.provider_id,
                            "error": "Refresh capability not available for provider/url",
                        }
                    )
                    continue

                bundle.provider_entity_id = snapshot.provider_entity_id or bundle.provider_entity_id
                await self._upsert_entity_snapshot(bundle)
                refreshed += 1
            except Exception as exc:
                failed.append(
                    {
                        "provider_id": snapshot.provider_id,
                        "error": str(exc),
                    }
                )

        ec = await self._merge.merge(self._db, entity)
        ec.capabilities = self._capability_map_for_entity(
            entity.entity_type,
            [snapshot.provider_id for snapshot in await self._get_snapshots(entity.id)],
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
        entity = await self._get_entity(entity_id)
        snapshots = await self._get_snapshots(entity_id)
        ec = await self._get_entity_canonical(entity_id)
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
            relation_entity = await self._get_entity(relation.to_entity_id)
            relation_ec = await self._get_entity_canonical(relation.to_entity_id)
        else:
            relations = await self.list_relations(entity_id)
            relation = relations[0] if relations else None
            if relation:
                relation_entity = await self._get_entity(relation.to_entity_id)
                relation_ec = await self._get_entity_canonical(relation.to_entity_id)

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


def relation_confidence(relation: EntityRelation) -> float:
    """
    Wilson-score lower bound mapped to [0, 1], blended with match score.
    """
    upvotes = relation.upvotes or 0
    downvotes = relation.downvotes or 0
    n = upvotes + downvotes
    wilson = 0.0
    if n > 0:
        p = upvotes / n
        z = 1.96
        denominator = 1 + z * z / n
        centre = p + z * z / (2 * n)
        deviation = math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
        wilson = max(0.0, min(1.0, (centre - z * deviation) / denominator))
    score_component = max(0.0, min(1.0, float((relation.match_score or 0.0) / 100.0)))
    if n == 0:
        return score_component
    return (0.65 * wilson) + (0.35 * score_component)
