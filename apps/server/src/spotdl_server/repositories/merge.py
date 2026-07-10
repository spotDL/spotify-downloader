"""Deterministic snapshot → canonical merge (source-priority per field class).

Given the set of :class:`ProviderSnapshot` rows that describe one real-world
entity, :class:`CanonicalMerger` folds them into a single canonical row
(``tracks``/``albums``/``artists``/``playlists``) plus the ``entity_links`` that
record which snapshots contributed. The fold is:

* **Deterministic** — the winning value for every field is chosen by a fixed
  source priority (:data:`SOURCE_PRIORITY`) and a fixed per-field-class rule, so
  the result is independent of the order snapshots are passed in.
* **Re-runnable** — merging the same set twice yields one canonical row with
  identical field values and no duplicate ``entity_links`` (idempotent on the
  unique ``(entity_type, entity_id, snapshot_id)`` triple).

**Snapshot metadata convention.** A snapshot carries the provider-agnostic
*normalized* metadata for its entity. The repository's normalized key columns
(``name``/``isrc``/``duration_ms``/``artist_names``/``album_name``/``art_url``)
are the fast-query projection; the full structured metadata (track/disc numbers,
explicit flag, year, genres, popularity, the album sub-object, per-entity extras
like an artist ``image_url`` or a playlist ``owner``) lives in ``raw_payload`` as
a ``Track``/``AlbumRef``-shaped dict. The merger reads a column first and falls
back to the matching ``raw_payload`` key, so a producer may populate either. This
is the one place that convention is interpreted — every field accessor here is
the single implementation.

The merger lives in the repositories layer and upserts ``EntityLink`` ORM rows
directly (it does **not** depend on the Task 6 ``EntityLinkRepository`` read/status
API, keeping this module green standalone). It never commits — the caller's unit
of work does.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from spotdl_core.model import EntityType, ProviderId
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.enums import LinkStatus
from spotdl_server.db.models import (
    Album,
    Artist,
    EntityLink,
    Playlist,
    ProviderSnapshot,
    Track,
)
from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
    TrackRepository,
    normalize_artist_name,
)

# Metadata source priority (spec §6.1): SPOTIFY > DEEZER > ITUNES > MUSICBRAINZ.
# Any provider not listed (e.g. YTMusic, which also carries metadata) ranks after
# MUSICBRAINZ. This is CONTRACT.
SOURCE_PRIORITY: tuple[ProviderId, ...] = (
    ProviderId.SPOTIFY,
    ProviderId.DEEZER,
    ProviderId.ITUNES,
    ProviderId.MUSICBRAINZ,
)


def _priority_rank(provider: ProviderId) -> int:
    try:
        return SOURCE_PRIORITY.index(provider)
    except ValueError:
        return len(SOURCE_PRIORITY)


def _sort_key(snapshot: ProviderSnapshot) -> tuple[int, str, str]:
    # Rank first, then a total order on (provider, provider_entity_id) so the sort
    # is fully deterministic even for two snapshots that share a priority rank —
    # the merge result never depends on input order.
    return (_priority_rank(snapshot.provider), snapshot.provider.value, snapshot.provider_entity_id)


def _sorted(snapshots: Sequence[ProviderSnapshot]) -> list[ProviderSnapshot]:
    return sorted(snapshots, key=_sort_key)


# --------------------------------------------------------------------------- #
# per-snapshot field accessors — read normalized column first, then raw_payload
# --------------------------------------------------------------------------- #
def _payload(snapshot: ProviderSnapshot) -> dict[str, Any]:
    payload = snapshot.raw_payload
    return payload if isinstance(payload, dict) else {}


def _name(snapshot: ProviderSnapshot) -> str | None:
    return snapshot.name or _payload(snapshot).get("name")


def _duration_ms(snapshot: ProviderSnapshot) -> int | None:
    if snapshot.duration_ms is not None:
        return snapshot.duration_ms
    value = _payload(snapshot).get("duration_ms")
    return value if isinstance(value, int) else None


def _isrc(snapshot: ProviderSnapshot) -> str | None:
    return snapshot.isrc or _payload(snapshot).get("isrc")


def _artist_names(snapshot: ProviderSnapshot) -> list[str]:
    if snapshot.artist_names:
        return list(snapshot.artist_names)
    value = _payload(snapshot).get("artists")
    return list(value) if value else []


def _cover_url(snapshot: ProviderSnapshot) -> str | None:
    return snapshot.art_url or _payload(snapshot).get("cover_url")


def _image_url(snapshot: ProviderSnapshot) -> str | None:
    return snapshot.art_url or _payload(snapshot).get("image_url")


def _genres(snapshot: ProviderSnapshot) -> list[str]:
    value = _payload(snapshot).get("genres")
    return list(value) if value else []


def _album_dict(snapshot: ProviderSnapshot) -> dict[str, Any] | None:
    album = _payload(snapshot).get("album")
    return album if isinstance(album, dict) else None


def _payload_key(key: str) -> Callable[[ProviderSnapshot], Any]:
    return lambda snapshot: _payload(snapshot).get(key)


# --------------------------------------------------------------------------- #
# priority selection primitives (input already priority-sorted)
# --------------------------------------------------------------------------- #
def _first_not_none(
    snapshots: Sequence[ProviderSnapshot], accessor: Callable[[ProviderSnapshot], Any]
) -> Any:
    """First value that ``is not None`` following source priority.

    ``is not None`` (not truthiness) so a legitimate ``False``/``0`` from a
    higher-priority source is not skipped in favour of a lower one.
    """
    for snapshot in snapshots:
        value = accessor(snapshot)
        if value is not None:
            return value
    return None


def _first_non_empty(
    snapshots: Sequence[ProviderSnapshot], accessor: Callable[[ProviderSnapshot], list[str]]
) -> list[str]:
    """First non-empty list following source priority (single-source pick)."""
    for snapshot in snapshots:
        value = accessor(snapshot)
        if value:
            return value
    return []


def _spotify_popularity(snapshots: Sequence[ProviderSnapshot]) -> int | None:
    for snapshot in snapshots:
        if snapshot.provider == ProviderId.SPOTIFY:
            value = _payload(snapshot).get("popularity")
            return value if isinstance(value, int) else None
    return None


class CanonicalMerger:
    """Folds provider snapshots into canonical entities (deterministic + re-runnable)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._tracks = TrackRepository(session)
        self._albums = AlbumRepository(session)
        self._artists = ArtistRepository(session)
        self._playlists = PlaylistRepository(session)

    # ----------------------------------------------------------------- track
    async def merge_track(
        self, snapshots: Sequence[ProviderSnapshot], *, merge_embedded_album: bool = True
    ) -> Track:
        snaps = _sorted(snapshots)
        merged_isrc = _first_not_none(snaps, _isrc)
        track = await self._resolve_track(snaps, merged_isrc)

        # ``merge_embedded_album=False`` when the caller (``merge_album``) will
        # assign ``album_id`` itself: the per-track embedded ``album`` sub-object
        # must not create an orphan Album row (first run) nor overwrite the
        # already-merged album's fields (re-run). Preserve the current binding.
        album_id = (
            await self._merge_track_album(track, snaps) if merge_embedded_album else track.album_id
        )
        await self._tracks.update(
            track,
            name=_first_not_none(snaps, _name) or "",
            duration_ms=_first_not_none(snaps, _duration_ms) or 0,
            isrc=merged_isrc,
            explicit=_first_not_none(snaps, _payload_key("explicit")),
            track_number=_first_not_none(snaps, _payload_key("track_number")),
            disc_number=_first_not_none(snaps, _payload_key("disc_number")),
            year=_first_not_none(snaps, _payload_key("year")),
            genres=_first_non_empty(snaps, _genres),
            popularity=_spotify_popularity(snaps),
            date=_first_not_none(snaps, _payload_key("date")),
            publisher=_first_not_none(snaps, _payload_key("publisher")),
            copyright_text=_first_not_none(snaps, _payload_key("copyright_text")),
            album_id=album_id,
        )

        artist_ids = await self._resolve_artist_ids(_first_non_empty(snaps, _artist_names))
        await self._tracks.set_artists(track, artist_ids)  # refreshes ``artists``

        await self._link_all(EntityType.TRACK, track.id, snaps)
        await self.session.flush()
        # Return the track with ``artists`` + ``album`` force-loaded in the
        # greenlet: a plain ``refresh([...])`` only expires a selectin relationship,
        # so a warm-cache re-resolve would lazy-load ``album`` on access outside the
        # await context (MissingGreenlet). ``get_for_matching`` reloads both.
        reloaded = await self._tracks.get_for_matching(track.id)
        assert reloaded is not None
        return reloaded

    async def _resolve_track(
        self, snapshots: Sequence[ProviderSnapshot], merged_isrc: str | None
    ) -> Track:
        # Convergence order: an existing canonical row linked to any input snapshot
        # wins first (so re-resolving a track that had no ISRC, then gained one from
        # a higher-priority source, reuses the same row instead of forking a new one
        # by ISRC), then ISRC, then create.
        linked_id = await self._entity_id_via_links(EntityType.TRACK, [s.id for s in snapshots])
        if linked_id is not None:
            existing = await self._tracks.get(linked_id)
            if existing is not None:
                return existing
        if merged_isrc:
            track, _ = await self._tracks.get_or_create_by_isrc(merged_isrc)
            return track
        return await self._tracks.create(name="")

    async def _merge_track_album(
        self, track: Track, snapshots: Sequence[ProviderSnapshot]
    ) -> uuid.UUID | None:
        source = next((s for s in snapshots if _album_dict(s) is not None or s.album_name), None)
        if source is None:
            return track.album_id
        album = _album_dict(source) or {}
        fields = {
            "name": album.get("name") or source.album_name or "",
            "album_artist": album.get("album_artist"),
            "year": album.get("year"),
            "track_count": album.get("track_count"),
            "cover_url": self._album_cover(snapshots),
        }
        # Update the track's existing album row in place (re-runnable — no dup rows).
        if track.album_id is not None:
            existing = await self._albums.get(track.album_id)
            if existing is not None:
                await self._albums.update(existing, **fields)
                return existing.id
        created = await self._albums.create(**fields)
        return created.id

    @staticmethod
    def _album_cover(snapshots: Sequence[ProviderSnapshot]) -> str | None:
        for snapshot in snapshots:
            album = _album_dict(snapshot)
            if album and album.get("cover_url"):
                cover = album["cover_url"]
                return cover if isinstance(cover, str) else None
        fallback = _first_not_none(snapshots, _cover_url)
        return fallback if isinstance(fallback, str) else None

    # ----------------------------------------------------------------- album
    async def merge_album(
        self,
        snapshots: Sequence[ProviderSnapshot],
        track_snapshots_by_pos: Mapping[int, Sequence[ProviderSnapshot]],
    ) -> Album:
        snaps = _sorted(snapshots)
        album = await self._resolve_album(snaps)
        await self._albums.update(
            album,
            name=_first_not_none(snaps, _name) or "",
            album_artist=_first_not_none(snaps, _payload_key("album_artist")),
            year=_first_not_none(snaps, _payload_key("year")),
            track_count=_first_not_none(snaps, _payload_key("track_count")),
            cover_url=_first_not_none(snaps, _cover_url),
            label=_first_not_none(snaps, _payload_key("label")),
            copyright_text=_first_not_none(snaps, _payload_key("copyright_text")),
            popularity=_first_not_none(snaps, _payload_key("popularity")),
            genres=_first_non_empty(snaps, _genres),
            album_type=_first_not_none(snaps, _payload_key("album_type")),
            # Primary source ref = the highest-priority snapshot (input is
            # priority-sorted), so a metadata-only discography album can be
            # resolve-refreshed via ``{provider}:album:{provider_id}``.
            provider=snaps[0].provider,
            provider_id=snaps[0].provider_entity_id,
        )
        for position in sorted(track_snapshots_by_pos):
            track = await self.merge_track(
                list(track_snapshots_by_pos[position]), merge_embedded_album=False
            )
            await self._tracks.update(track, album_id=album.id)

        await self._link_all(EntityType.ALBUM, album.id, snaps)
        await self.session.flush()
        # Reload via the repository so ``tracks`` + each track's ``artists``/``album``
        # are force-loaded in the greenlet: a bare ``refresh([...])`` keeps the stale
        # ``track.album`` (loaded as ``None`` before ``album_id`` was assigned), so the
        # nested cover thumbnail would be missing. ``AlbumRepository.get`` states the
        # full chain (mirrors ``merge_artist``).
        reloaded = await self._albums.get(album.id)
        assert reloaded is not None
        return reloaded

    async def _resolve_album(self, snapshots: Sequence[ProviderSnapshot]) -> Album:
        linked_id = await self._entity_id_via_links(EntityType.ALBUM, [s.id for s in snapshots])
        if linked_id is not None:
            existing = await self._albums.get(linked_id)
            if existing is not None:
                return existing
        return await self._albums.create(name="")

    # ---------------------------------------------------------------- artist
    async def merge_artist(
        self,
        snapshots: Sequence[ProviderSnapshot],
        track_snapshots_by_pos: Mapping[int, Sequence[ProviderSnapshot]] | None = None,
        album_snapshots_by_pos: Mapping[int, Sequence[ProviderSnapshot]] | None = None,
    ) -> Artist:
        snaps = _sorted(snapshots)
        name = _first_not_none(snaps, _name) or ""
        # Canonical identity is the normalized name (name-only provenance).
        artist, _ = await self._artists.get_or_create_by_normalized_name(name)
        await self._artists.update(
            artist,
            name=name,
            normalized_name=normalize_artist_name(name),
            genres=_first_non_empty(snaps, _genres),
            image_url=_first_not_none(snaps, _image_url),
            popularity=_first_not_none(snaps, _payload_key("popularity")),
            followers=_first_not_none(snaps, _payload_key("followers")),
            bio=_first_not_none(snaps, _payload_key("bio")),
            country=_first_not_none(snaps, _payload_key("country")),
            header_url=_first_not_none(snaps, _payload_key("header_url")),
        )
        # Merge the artist's top-track listing so ``artist.tracks`` is populated:
        # each merged track credits this artist via ``track_artists`` (set_artists),
        # so it joins the artist's M2M listing. Mirrors ``merge_album`` per-position.
        by_pos = track_snapshots_by_pos or {}
        for position in sorted(by_pos):
            await self.merge_track(list(by_pos[position]))
        # Persist the discography: each album is merged (metadata-only — no track
        # listing here) and linked to the artist via ``artist_albums`` (set_albums),
        # in provider listing order. A discography album with no tracks is fine — a
        # later ``{provider}:album:{id}`` resolve reuses the same canonical row.
        by_album_pos = album_snapshots_by_pos or {}
        album_ids: list[uuid.UUID] = []
        for position in sorted(by_album_pos):
            album = await self.merge_album(list(by_album_pos[position]), {})
            album_ids.append(album.id)
        if by_album_pos:
            await self._artists.set_albums(artist, album_ids)
        await self._link_all(EntityType.ARTIST, artist.id, snaps)
        await self.session.flush()
        # Reload with ``tracks`` + nested ``artists`` + ``albums`` force-loaded in the
        # greenlet: ``artist_view`` iterates ``artist.tracks`` (and each track's
        # ``artists``) and ``artist.albums``, so returning the bare row would lazy-load
        # them on attribute access outside the await context (MissingGreenlet).
        # ``ArtistRepository.get`` states the chain.
        reloaded = await self._artists.get(artist.id)
        assert reloaded is not None
        return reloaded

    # -------------------------------------------------------------- playlist
    async def merge_playlist(
        self,
        snapshots: Sequence[ProviderSnapshot],
        track_snapshots_ordered: Sequence[Sequence[ProviderSnapshot]],
    ) -> Playlist:
        snaps = _sorted(snapshots)
        playlist = await self._resolve_playlist(snaps)
        await self._playlists.update(
            playlist,
            name=_first_not_none(snaps, _name) or "",
            description=_first_not_none(snaps, _payload_key("description")),
            owner=_first_not_none(snaps, _payload_key("owner")),
            cover_url=_first_not_none(snaps, _cover_url),
        )
        track_ids: list[uuid.UUID] = []
        for group in track_snapshots_ordered:
            track = await self.merge_track(list(group))
            track_ids.append(track.id)
        await self._playlists.set_tracks(playlist, track_ids)

        await self._link_all(EntityType.PLAYLIST, playlist.id, snaps)
        await self.session.flush()
        # Reload via the repository so ``tracks`` + each track's ``artists``/``album``
        # are force-loaded in the greenlet (nested cover thumbnails); mirrors
        # ``merge_album``/``merge_artist``.
        reloaded = await self._playlists.get(playlist.id)
        assert reloaded is not None
        return reloaded

    async def _resolve_playlist(self, snapshots: Sequence[ProviderSnapshot]) -> Playlist:
        linked_id = await self._entity_id_via_links(EntityType.PLAYLIST, [s.id for s in snapshots])
        if linked_id is not None:
            existing = await self._playlists.get(linked_id)
            if existing is not None:
                return existing
        return await self._playlists.create(name="")

    # ----------------------------------------------------------------- utils
    async def _resolve_artist_ids(self, names: Sequence[str]) -> list[uuid.UUID]:
        """Resolve an ordered name tuple to canonical artist ids.

        Names normalizing to the same key resolve to the same row; the caller's
        ``set_artists`` dedupes those while preserving first-occurrence order.
        """
        ids: list[uuid.UUID] = []
        for name in names:
            artist, _ = await self._artists.get_or_create_by_normalized_name(name)
            ids.append(artist.id)
        return ids

    async def _entity_id_via_links(
        self, entity_type: EntityType, snapshot_ids: Sequence[uuid.UUID]
    ) -> uuid.UUID | None:
        if not snapshot_ids:
            return None
        result = await self.session.execute(
            select(EntityLink.entity_id)
            .where(
                EntityLink.entity_type == entity_type,
                EntityLink.snapshot_id.in_(snapshot_ids),
            )
            .limit(1)
        )
        return result.scalars().first()

    async def _link_all(
        self,
        entity_type: EntityType,
        entity_id: uuid.UUID,
        snapshots: Sequence[ProviderSnapshot],
    ) -> None:
        for snapshot in snapshots:
            await self._upsert_link(entity_type, entity_id, snapshot.id)

    async def _upsert_link(
        self, entity_type: EntityType, entity_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> None:
        result = await self.session.execute(
            select(EntityLink).where(
                EntityLink.entity_type == entity_type,
                EntityLink.entity_id == entity_id,
                EntityLink.snapshot_id == snapshot_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return
        self.session.add(
            EntityLink(
                entity_type=entity_type,
                entity_id=entity_id,
                snapshot_id=snapshot_id,
                status=LinkStatus.AUTO,
            )
        )
        await self.session.flush()
