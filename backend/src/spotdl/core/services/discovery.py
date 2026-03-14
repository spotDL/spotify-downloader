"""Discovery logic for resolving URLs and queries into unified entities."""

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
from urllib.parse import urlparse

from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl.core.capabilities import (
    Capability,
    ProviderEntityBundle,
)
from spotdl.core.provider_registry import get_provider_registry
from spotdl.core.services.merge_engine import MergeEngine
from spotdl.core.services.song import SongServiceError, UnsupportedURLError, get_song_service
from spotdl.core.types.result import Result, TargetPlatform
from spotdl.core.types.song import Platform, Song, SongList
from spotdl.core.utils.opengraph import _fetch_open_graph
from spotdl.db.models.entity_unified import (
    Entity,
    EntityCanonical,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
)
from spotdl.providers.sources import detect_platform, extract_url_info
from spotdl.providers.targets import (
    YouTubeMusicProvider,
    YouTubeProvider,
)

logger = logging.getLogger(__name__)

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


@dataclass(slots=True)
class DiscoverResult:
    entities: list[Entity]
    relations: dict[str, list[EntityRelation]]
    created_entities: int = 0


def _now_utc() -> datetime:
    return datetime.now(UTC)


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


class DiscoveryService:
    """Handles entity discovery from URLs and search queries."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        song_service: Any = None,
        registry: Any = None,
        merge_engine: MergeEngine | None = None,
        target_providers: dict[str, Any] | None = None,
        fetch_open_graph_fn: Any = None,
    ) -> None:
        self._db = session
        self._song_service = song_service or get_song_service()
        self._registry = registry or get_provider_registry()
        self._merge = merge_engine or MergeEngine()
        self._target_providers = target_providers or {}
        self._fetch_open_graph = fetch_open_graph_fn or _fetch_open_graph

    # ── Bundle builders ──────────────────────────────────────────────

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
            "isrc": self._normalize_isrc(song.isrc),
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

        # Construct album URL from platform + album_id instead of using song.list_url
        album_url = self._construct_album_url(song.platform, song.album_id)

        payload = {
            "name": album_name,
            "artists": list(song.artists),
            "artist": song.album_artist or song.artist,
            "platform": provider_id,
            "platform_id": song.album_id,
            "url": album_url,
            "cover_url": song.cover_url,
            "year": song.year or None,
            "track_count": song.tracks_count or None,
            "entity_type": "album",
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=song.album_id,
            provider_url=album_url,
            entity_type="album",
            normalized_payload=payload,
            raw_payload=payload,
            confidence=0.74,
        )

    @staticmethod
    def _construct_album_url(platform: Platform, album_id: str) -> str | None:
        """Construct canonical album URL from platform and album ID."""
        url_templates = {
            Platform.SPOTIFY: f"https://open.spotify.com/album/{album_id}",
            Platform.DEEZER: f"https://www.deezer.com/album/{album_id}",
            Platform.TIDAL: f"https://tidal.com/browse/album/{album_id}",
            Platform.APPLE_MUSIC: f"https://music.apple.com/album/{album_id}",
        }
        return url_templates.get(platform)

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
            "disc_number": None,
            "date": None,
            "isrc": None,
            "album_artist": None,
            "genres": [],
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

        # Try to get container-level metadata from the raw JSON
        raw = songlist.json if hasattr(songlist, 'json') else {}

        # For albums, use album_artist from songs if available
        if entity_type == "album" and songlist.songs:
            album_artist = next(
                (s.album_artist for s in songlist.songs if s.album_artist),
                songlist.songs[0].artist if songlist.songs else None,
            )
            artists = [album_artist] if album_artist else []
            cover_url = songlist.songs[0].cover_url if songlist.songs else None
            year = next(
                (s.year for s in songlist.songs if s.year),
                None,
            )
        elif entity_type == "artist" and songlist.songs:
            # For artist entities, the name IS the artist
            artists = [songlist.name]
            album_artist = songlist.name
            # Don't use album art for artists - use None and let enrichment provide it
            cover_url = None
            year = None
        else:
            # Playlists and others
            first_song = songlist.songs[0] if songlist.songs else None
            artists = []
            album_artist = None
            cover_url = first_song.cover_url if first_song else None
            year = None

        payload = {
            "name": songlist.name,
            "url": songlist.url,
            "platform": provider_id,
            "platform_id": provider_entity_id,
            "entity_type": entity_type,
            "track_count": len(songlist.songs),
            "cover_url": cover_url,
            "artists": artists,
            "artist": artists[0] if artists else None,
            "year": year,
        }
        return ProviderEntityBundle(
            provider_id=provider_id,
            provider_entity_id=str(provider_entity_id),
            provider_url=songlist.url,
            entity_type=entity_type,
            normalized_payload=payload,
            raw_payload=raw if raw else payload,
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

    # ── Entity conversion ──────────────────────────────────────────────

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

    # ── Capability map ───────────────────────────────────────────────

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

    # ── Entity CRUD helpers ──────────────────────────────────────────

    async def _get_entity(self, entity_id: uuid.UUID) -> Entity:
        from spotdl.core.services.entity_unified import EntityNotFoundError

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
        # Collect (provider_id, provider_entity_id) pairs for batch query
        composite_keys: list[tuple[str, str]] = []  # (provider_id, provider_entity_id)
        key_to_composite: dict[tuple[str, str], tuple[str, str]] = {}  # composite -> bundle key
        for key in list(entities_by_key.keys()):
            bundle = bundles.get(key)
            if bundle is None:
                continue
            composite = (bundle.provider_id, bundle.provider_entity_id)
            composite_keys.append(composite)
            key_to_composite[composite] = key

        if not composite_keys:
            return

        # Batch fetch snapshots with BOTH provider_id and provider_entity_id filters
        conditions = [
            and_(
                EntitySnapshot.provider_id == pid,
                EntitySnapshot.provider_entity_id == peid,
            )
            for pid, peid in composite_keys
        ]
        snap_result = await self._db.execute(
            select(EntitySnapshot).where(or_(*conditions))
        )
        # Key by (provider_id, provider_entity_id) to avoid collisions
        snap_map: dict[tuple[str, str], EntitySnapshot] = {}
        for snap in snap_result.scalars().all():
            snap_map[(snap.provider_id, snap.provider_entity_id)] = snap

        # Re-resolve entity references
        for composite, key in key_to_composite.items():
            snap = snap_map.get(composite)
            if snap is None:
                entities_by_key.pop(key, None)
                continue
            old_entity = entities_by_key.get(key)
            if old_entity is not None and old_entity.id != snap.entity_id:
                entities_by_key[key] = await self._get_entity(snap.entity_id)

    # ── Snapshot upsert & entity creation ────────────────────────────

    async def _find_or_create_entity(self, bundle: ProviderEntityBundle) -> tuple[Entity, bool]:
        """Find existing entity by (provider_id, provider_entity_id) or create new one.

        Returns (entity, created) tuple.
        """
        from spotdl.core.services.entity_unified import UnifiedEntityError

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
            # Entity exists -- update snapshot if data changed
            entity = await self._get_entity(existing_snapshot.entity_id)
            self._update_snapshot_if_changed(existing_snapshot, bundle)
            return entity, False

        # 2. No existing snapshot -- create new Entity + Snapshot
        try:
            async with self._db.begin_nested():
                entity = Entity(entity_type=bundle.entity_type)
                self._db.add(entity)
                await self._db.flush()

                snapshot = self._create_snapshot(entity.id, bundle)
                self._db.add(snapshot)
                await self._db.flush()
        except IntegrityError:
            # Concurrent insert -- re-query
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

    @staticmethod
    def _normalize_isrc(isrc: str | None) -> str | None:
        """Normalize ISRC to uppercase with hyphens stripped."""
        if not isrc or not isinstance(isrc, str):
            return None
        normalized = isrc.strip().upper().replace("-", "")
        return normalized if normalized else None

    async def _try_isrc_merge(self, entity: Entity, bundle: ProviderEntityBundle) -> Entity:
        """Check for cross-provider merge via ISRC. Returns survivor entity."""
        isrc = self._normalize_isrc(bundle.normalized_payload.get("isrc"))
        if not isrc:
            return entity

        # Find other snapshots with same ISRC from different entities
        try:
            other_query = select(EntitySnapshot).where(
                EntitySnapshot.entity_id != entity.id,
                func.upper(func.replace(EntitySnapshot.normalized_payload["isrc"].as_string(), "-", "")) == isrc,
            )
            other_result = await self._db.execute(other_query)
            other_snapshots = list(other_result.scalars().all())
        except SQLAlchemyError as exc:
            logger.warning(
                "ISRC merge query failed for entity %s (ISRC=%s): %s — skipping merge",
                entity.id,
                isrc,
                exc,
            )
            return entity

        if not other_snapshots:
            return entity

        # Choose survivor by creation time (oldest entity survives)
        all_entity_ids = {entity.id} | {s.entity_id for s in other_snapshots}
        all_entity_ids_list = list(all_entity_ids)
        entities_result = await self._db.execute(
            select(Entity)
            .where(Entity.id.in_(all_entity_ids_list))
            .order_by(Entity.created_at.asc())
        )
        ordered_entities = list(entities_result.scalars().all())
        if not ordered_entities:
            return entity
        survivor = ordered_entities[0]

        for dup_entity in ordered_entities[1:]:
            await self._merge_entities(survivor, dup_entity)

        return survivor

    async def _merge_entities(self, survivor: Entity, duplicate: Entity) -> None:
        """Move all data from duplicate to survivor and delete duplicate."""
        # Move snapshots
        await self._db.execute(
            update(EntitySnapshot)
            .where(EntitySnapshot.entity_id == duplicate.id)
            .values(entity_id=survivor.id)
        )

        # Pre-load survivor's existing relations for conflict check (batch)
        survivor_rels_result = await self._db.execute(
            select(
                EntityRelation.from_entity_id,
                EntityRelation.to_entity_id,
                EntityRelation.relation_type,
            ).where(
                (EntityRelation.from_entity_id == survivor.id)
                | (EntityRelation.to_entity_id == survivor.id)
            )
        )
        survivor_rel_keys = {
            (row.from_entity_id, row.to_entity_id, row.relation_type)
            for row in survivor_rels_result.all()
        }

        # Move outgoing relations (handle unique constraint conflicts by skipping duplicates)
        outgoing_query = select(EntityRelation).where(EntityRelation.from_entity_id == duplicate.id)
        outgoing_result = await self._db.execute(outgoing_query)
        for rel in outgoing_result.scalars().all():
            if (survivor.id, rel.to_entity_id, rel.relation_type) not in survivor_rel_keys:
                rel.from_entity_id = survivor.id
                survivor_rel_keys.add((survivor.id, rel.to_entity_id, rel.relation_type))
            else:
                await self._db.delete(rel)

        # Move incoming relations
        incoming_query = select(EntityRelation).where(EntityRelation.to_entity_id == duplicate.id)
        incoming_result = await self._db.execute(incoming_query)
        for rel in incoming_result.scalars().all():
            if (rel.from_entity_id, survivor.id, rel.relation_type) not in survivor_rel_keys:
                rel.to_entity_id = survivor.id
                survivor_rel_keys.add((rel.from_entity_id, survivor.id, rel.relation_type))
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

        # Delete duplicate entity using raw SQL to avoid ORM cascade
        # (ORM cascade="all, delete-orphan" would re-delete snapshots/relations
        # that were already moved to the survivor via UPDATE statements above)
        await self._db.execute(
            delete(Entity).where(Entity.id == duplicate.id)
        )
        # Expunge the now-deleted object from the session to avoid stale state
        await self._db.flush()
        try:
            self._db.expunge(duplicate)
        except Exception:
            pass

    async def _upsert_entity_snapshot(self, bundle: ProviderEntityBundle) -> tuple[Entity, bool]:
        """Upsert via snapshot-based lookup. Wrapper around _find_or_create_entity
        that also handles re-merging for existing entities when data changes.

        Returns (entity, created) tuple.
        """
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
            old_isrc = self._normalize_isrc(
                (existing_snapshot.normalized_payload or {}).get("isrc")
            )
            changed = self._update_snapshot_if_changed(existing_snapshot, bundle)

            # Get current canonical
            ec = await self._get_entity_canonical(entity.id)

            if not changed and ec is not None and ec.canonical:
                return entity, False

            # Recompute canonical
            await self._db.flush()

            # If ISRC was added or changed, try cross-provider merge
            new_isrc = self._normalize_isrc(bundle.normalized_payload.get("isrc"))
            if (
                bundle.entity_type == "track"
                and new_isrc
                and new_isrc != old_isrc
            ):
                entity = await self._try_isrc_merge(entity, bundle)

            ec = await self._merge.merge(self._db, entity)
            ec.capabilities = self._capability_map_for_entity(
                entity.entity_type,
                [s.provider_id for s in await self._get_snapshots(entity.id)],
            )
            await self._db.flush()
            return entity, False

        # Create new
        entity, created = await self._find_or_create_entity(bundle)
        return entity, created

    # ── Target URL resolution ────────────────────────────────────────

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
        except Exception as exc:
            logger.debug("Failed to resolve target URL %s: %s", url, exc)
            return None
        return None

    # ── Relation helper (used during discovery) ──────────────────────

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
                # FK violation (entity deleted by concurrent merge) -- skip gracefully
                logger.warning(
                    "Skipping relation %s -> %s (%s): entity no longer exists.",
                    from_entity_id,
                    to_entity_id,
                    relation_type,
                )
                return None

        if match_score is not None:
            relation.match_score = match_score
        relation.discovered_by = discovered_by
        if relation_data is not None:
            relation.relation_data = relation_data

        await self._db.flush()
        return relation

    # ── Main discovery methods ───────────────────────────────────────

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
        from spotdl.core.services.entity_unified import UnifiedEntityError

        requested_types = set(entity_types) if entity_types else None
        created_entities = 0
        entities: list[Entity] = []
        relations: dict[str, list[EntityRelation]] = {}

        # Key: (provider_id, provider_entity_id) -- the global dedup key
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
                og_payload = await self._fetch_open_graph(url)
                if og_payload:
                    bundle = self._bundle_from_open_graph(url, og_payload)
                    bundle_key = (bundle.provider_id, bundle.provider_entity_id)
                    bundles_to_upsert[bundle_key] = bundle
                else:
                    raise UnifiedEntityError(f"Unsupported URL and no metadata available: {url}")

        entities_by_key: dict[tuple[str, str], Entity] = {}
        for key in sorted(bundles_to_upsert.keys()):
            entity, was_created = await self._upsert_entity_snapshot(bundles_to_upsert[key])
            entities_by_key[key] = entity
            entities.append(entity)
            if was_created:
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

        # Filter by entity_types if specified
        filtered = list(deduped.values())
        if requested_types:
            filtered = [e for e in filtered if e.entity_type in requested_types]

        return DiscoverResult(
            entities=filtered[:limit], relations=relations, created_entities=created_entities
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
        if provider_filter:
            source_platforms = [
                platform
                for platform in self._song_service.supported_platforms
                if SOURCE_PLATFORM_TO_ID.get(platform, "") in provider_filter
            ]
        else:
            source_platforms = [Platform.SPOTIFY]

        async def search_source(platform: Platform) -> list[Song]:
            try:
                return await self._song_service.search(query, platform=platform, limit=limit)
            except Exception as exc:
                logger.warning("Search failed for platform %s: %s", platform, exc)
                return []

        source_tasks = [search_source(platform) for platform in source_platforms]
        source_results = await asyncio.gather(*source_tasks, return_exceptions=False)

        # Key: (provider_id, provider_entity_id)
        bundles_to_upsert: dict[tuple[str, str], ProviderEntityBundle] = {}
        relations_to_create: list[
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None]
        ] = []

        # Task 1.2: Track total entities across platforms, stop when limit reached
        total_track_count = 0
        for songs in source_results:
            for song in songs:
                track_bundle = self._bundle_from_song(song)
                track_key = (track_bundle.provider_id, track_bundle.provider_entity_id)
                bundles_to_upsert[track_key] = track_bundle
                total_track_count += 1

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

            # Stop searching more platforms if we already have enough results
            if total_track_count >= limit:
                break

        entities: list[Entity] = []
        created_entities = 0
        entities_by_key: dict[tuple[str, str], Entity] = {}
        for key in sorted(bundles_to_upsert.keys()):
            entity, was_created = await self._upsert_entity_snapshot(bundles_to_upsert[key])
            entities_by_key[key] = entity
            entities.append(entity)
            if was_created:
                created_entities += 1

        # Refresh entity references: ISRC merge may have replaced entities
        await self._refresh_entity_map(entities_by_key, bundles_to_upsert)

        # Deduplicate relations
        unique_relations: dict[
            tuple[tuple[str, str], tuple[str, str], str],
            tuple[tuple[str, str], tuple[str, str], str, str, dict[str, Any] | None],
        ] = {}
        for r in relations_to_create:
            unique_relations[(r[0], r[1], r[2])] = r

        # Task 1.1: Collect relations the same way URL discovery does
        relations: dict[str, list[EntityRelation]] = {}
        for r_tuple in sorted(unique_relations.values(), key=lambda x: (x[0], x[1], x[2])):
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

        # Task 1.6: Deduplicate then filter (same order as URL discovery)
        deduped: dict[str, Entity] = {}
        for entity in entities:
            deduped[str(entity.id)] = entity

        filtered = list(deduped.values())
        if requested_types:
            filtered = [e for e in filtered if e.entity_type in requested_types]

        return DiscoverResult(
            entities=filtered[:limit],
            relations=relations,
            created_entities=created_entities,
        )
