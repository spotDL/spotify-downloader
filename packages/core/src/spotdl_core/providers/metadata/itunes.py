"""iTunes / Apple Music metadata provider (open Search + Lookup APIs, no auth).

Resolution uses Apple's **Lookup API** (``/lookup?id=...``) keyed by the numeric
id that :func:`spotdl_core.providers.urls.parse` extracts from a
``music.apple.com`` URL. This is a deliberate improvement over scraping
``music.apple.com`` HTML/JSON-LD: no ``bs4``, no fragile markup, one JSON path.

Three quirks drive the mapping and are enforced here as **contract**:

* **Duration is already milliseconds.** ``trackTimeMillis`` maps straight to
  ``duration_ms`` -- never multiplied.
* **No ISRC.** The iTunes APIs never return an ISRC, so ``isrc`` is always
  ``None``.
* **"Not found" is an empty 200 body.** A miss is ``{"resultCount": 0,
  "results": []}`` -> :class:`EntityNotFound` on ``resolve`` and ``[]`` on
  ``search``.

Album tracks are expanded with ``?id={collectionId}&entity=song`` (the first
result is the ``collection`` record, the rest are its ``track`` records).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from spotdl_core.model import AlbumRef, ArtistRef, EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers.base import ALL_SEARCH_ENTITY_TYPES, HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, UnsupportedURL
from spotdl_core.providers.http import create_client, request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "ITunesProvider",
    "build_itunes_provider",
    "map_album",
    "map_album_hits",
    "map_artist_hits",
    "map_search",
    "map_song_hits",
    "map_track",
]

#: Discography cap — raw ``lookup?entity=album`` collections fetched for an artist
#: before the name dedupe (also the ``limit`` sent to the Lookup API).
_ARTIST_ALBUMS_LIMIT = 200

_API_BASE = "https://itunes.apple.com"


# --- pure mappers ---------------------------------------------------------


def _year(release_date: str | None) -> int | None:
    if not release_date:
        return None
    head = release_date[:4]
    return int(head) if head.isdigit() else None


def _upgrade_artwork(url: str | None) -> str | None:
    """Upgrade a ``100x100`` artwork URL to ``600x600``."""
    if not url:
        return None
    return url.replace("100x100", "600x600")


def _album_type(collection_type: str | None) -> str | None:
    """Lower-case an iTunes ``collectionType`` (``Album`` -> ``album``)."""
    return collection_type.lower() if isinstance(collection_type, str) and collection_type else None


def _album_ref(result: dict[str, Any]) -> AlbumRef | None:
    name = result.get("collectionName")
    if not name:
        return None
    return AlbumRef(
        name=name,
        album_artist=result.get("artistName"),
        year=_year(result.get("releaseDate")),
        track_count=result.get("trackCount"),
        cover_url=_upgrade_artwork(result.get("artworkUrl100")),
    )


def map_track(result: dict[str, Any]) -> Track:
    """Map an iTunes ``song`` result object to a :class:`Track` (no ISRC)."""
    album = _album_ref(result)
    genre = result.get("primaryGenreName")
    return Track(
        name=result["trackName"],
        artists=(result["artistName"],),
        duration_ms=int(result.get("trackTimeMillis") or 0),
        album=album,
        isrc=None,
        explicit=result.get("trackExplicitness") == "explicit",
        track_number=result.get("trackNumber"),
        disc_number=result.get("discNumber"),
        genres=(genre,) if genre else (),
        year=_year(result.get("releaseDate")),
        provider=ProviderId.ITUNES,
        provider_id=str(result["trackId"]),
    )


def _song_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in results if r.get("wrapperType") == "track" and r.get("trackName")]


def map_album(results: list[dict[str, Any]]) -> ResolvedEntity:
    """Map an ``entity=song`` lookup (collection record + track records)."""
    collection = next((r for r in results if r.get("wrapperType") == "collection"), None)
    if collection is None:
        raise EntityNotFound(provider=ProviderId.ITUNES)
    album = AlbumRef(
        name=collection["collectionName"],
        album_artist=collection.get("artistName"),
        year=_year(collection.get("releaseDate")),
        track_count=collection.get("trackCount"),
        cover_url=_upgrade_artwork(collection.get("artworkUrl100")),
        copyright_text=collection.get("copyright"),
        album_type=_album_type(collection.get("collectionType")),
    )
    tracks = tuple(
        map_track(result).model_copy(update={"album": album, "year": album.year})
        for result in _song_results(results)
    )
    return ResolvedEntity(
        provider=ProviderId.ITUNES,
        provider_id=str(collection["collectionId"]),
        entity_type=EntityType.ALBUM,
        album=album,
        name=collection.get("collectionName"),
        tracks=tracks,
    )


def map_search(payload: dict[str, Any]) -> list[Track]:
    """Map a ``/search`` payload (``entity=song``) to a list of :class:`Track`."""
    results = payload.get("results") or []
    return [map_track(r) for r in results if r.get("trackName") and r.get("trackId") is not None]


def _split_collection_name(raw: str) -> tuple[str, str | None]:
    """Strip iTunes' ``" - Single"``/``" - EP"`` collection-name suffix.

    The suffix IS the release-type signal (iTunes has no ``collectionType`` on
    most collections) — and left in place it breaks the cross-source name dedupe
    ("I Love It - Single" would sit next to Spotify's "I Love It").
    """
    for suffix, kind in ((" - Single", "single"), (" - EP", "ep")):
        if raw.endswith(suffix):
            return raw[: -len(suffix)], kind
    return raw, None


def _artist_album_ref(item: dict[str, Any], *, artist_id: str) -> AlbumRef | None:
    """Map one ``lookup?entity=album`` collection to a source-tagged ``AlbumRef``.

    Collections not OWNED by the looked-up artist are dropped: iTunes' lookup
    also returns releases the artist merely appears on ("… (feat. X)" albums by
    other artists), which polluted the discography with features.
    """
    name = item.get("collectionName")
    collection_id = item.get("collectionId")
    if not name or collection_id is None:
        return None
    if str(item.get("artistId")) != artist_id:
        return None  # someone else's release featuring the artist — not discography
    clean_name, suffix_type = _split_collection_name(name)
    return AlbumRef(
        name=clean_name,
        album_artist=item.get("artistName"),
        year=_year(item.get("releaseDate")),
        track_count=item.get("trackCount"),
        cover_url=_upgrade_artwork(item.get("artworkUrl100")),
        album_type=_album_type(item.get("collectionType")) or suffix_type,
        provider=ProviderId.ITUNES,
        provider_id=str(collection_id),
    )


def _dedupe_artist_albums(refs: list[AlbumRef], *, cap: int) -> tuple[AlbumRef, ...]:
    """De-duplicate a discography by (case-folded) name, preserving order, capped."""
    seen: set[str] = set()
    out: list[AlbumRef] = []
    for ref in refs:
        key = ref.name.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
        if len(out) >= cap:
            break
    return tuple(out)


def map_song_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``search?entity=song`` payload to track :class:`SearchHit`\\ s."""
    return [SearchHit.from_track(track) for track in map_search(payload)]


def map_album_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``search?entity=album`` payload to album :class:`SearchHit`\\ s."""
    hits: list[SearchHit] = []
    for item in payload.get("results") or []:
        collection_id = item.get("collectionId")
        name = item.get("collectionName")
        if collection_id is None or not name:
            continue
        hits.append(
            SearchHit(
                entity_type=EntityType.ALBUM,
                provider=ProviderId.ITUNES,
                provider_id=str(collection_id),
                name=name,
                subtitle=item.get("artistName"),
                cover_url=_upgrade_artwork(item.get("artworkUrl100")),
                year=_year(item.get("releaseDate")),
            )
        )
    return hits


def map_artist_hits(payload: dict[str, Any]) -> list[SearchHit]:
    """Map a ``search?entity=musicArtist`` payload to artist :class:`SearchHit`\\ s.

    iTunes exposes no artist image or follower count, so the primary genre (when
    present) becomes the subtitle and ``cover_url``/``followers`` stay ``None``.
    """
    hits: list[SearchHit] = []
    for item in payload.get("results") or []:
        artist_id = item.get("artistId")
        name = item.get("artistName")
        if artist_id is None or not name:
            continue
        hits.append(
            SearchHit(
                entity_type=EntityType.ARTIST,
                provider=ProviderId.ITUNES,
                provider_id=str(artist_id),
                name=name,
                subtitle=item.get("primaryGenreName"),
            )
        )
    return hits


# --- provider -------------------------------------------------------------


class ITunesProvider(HttpProvider):
    """Resolve/search/enrich against the open iTunes APIs.

    Implements :class:`~spotdl_core.providers.base.Searches`,
    :class:`~spotdl_core.providers.base.SearchesEntities`,
    :class:`~spotdl_core.providers.base.Resolves` and
    :class:`~spotdl_core.providers.base.Enriches`.
    """

    id: ClassVar[ProviderId] = ProviderId.ITUNES

    #: Per-entity ``search`` ``entity`` value + item→hit mapper, in stable order.
    #: iTunes exposes no playlist search, so playlists are absent (skipped).
    _SEARCH_ENTITIES: ClassVar[
        tuple[tuple[EntityType, str, Callable[[dict[str, Any]], list[SearchHit]]], ...]
    ] = (
        (EntityType.TRACK, "song", map_song_hits),
        (EntityType.ALBUM, "album", map_album_hits),
        (EntityType.ARTIST, "musicArtist", map_artist_hits),
    )

    async def _get(self, path: str, **params: Any) -> Any:
        clean = {key: value for key, value in params.items() if value is not None}
        return await request_json(
            self._client,
            "GET",
            path,
            provider=ProviderId.ITUNES,
            params=clean or None,
        )

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is EntityType.TRACK:
            return await self._resolve_track(ref.entity_id)
        if ref.entity_type is EntityType.ALBUM:
            return await self._resolve_album(ref.entity_id)
        if ref.entity_type is EntityType.ARTIST:
            return await self._resolve_artist(ref.entity_id)
        # The Lookup API cannot fetch Apple Music editorial playlists (pl.* ids).
        raise UnsupportedURL(f"itunes cannot resolve entity type {ref.entity_type}")

    async def _resolve_track(self, entity_id: str) -> ResolvedEntity:
        results = await self._lookup(entity_id)
        result = results[0]
        return ResolvedEntity(
            provider=ProviderId.ITUNES,
            provider_id=str(result.get("trackId") or entity_id),
            entity_type=EntityType.TRACK,
            track=map_track(result),
        )

    async def _resolve_album(self, entity_id: str) -> ResolvedEntity:
        results = await self._lookup(entity_id, entity="song")
        return map_album(results)

    async def _resolve_artist(self, entity_id: str) -> ResolvedEntity:
        """Resolve an artist to metadata + a full discography (one Lookup request).

        ``lookup?entity=album`` returns the artist record first, then its
        collections → source-tagged discography ``AlbumRef``\\ s (deduped by name).
        iTunes exposes no artist image/followers and no per-artist top tracks, so
        ``tracks=()`` — the enrichment overlap gate then compares via albums.
        """
        results = await self._lookup(entity_id, entity="album", limit=_ARTIST_ALBUMS_LIMIT)
        artist = next((r for r in results if r.get("wrapperType") == "artist"), None)
        name = artist.get("artistName") if artist else None
        genre = artist.get("primaryGenreName") if artist else None
        refs = [
            ref
            for r in results
            if r.get("wrapperType") == "collection"
            and (ref := _artist_album_ref(r, artist_id=entity_id)) is not None
        ]
        albums = _dedupe_artist_albums(refs, cap=_ARTIST_ALBUMS_LIMIT)
        return ResolvedEntity(
            provider=ProviderId.ITUNES,
            provider_id=entity_id,
            entity_type=EntityType.ARTIST,
            artist=(
                ArtistRef(
                    name=name,
                    provider=ProviderId.ITUNES,
                    provider_id=entity_id,
                    genres=(genre,) if genre else (),
                )
                if name
                else None
            ),
            name=name,
            albums=albums,
        )

    async def _lookup(
        self, entity_id: str, *, entity: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Run the Lookup API, raising :class:`EntityNotFound` on an empty body."""
        payload = await self._get("/lookup", id=entity_id, entity=entity, limit=limit)
        results = payload.get("results") or []
        if not results:
            raise EntityNotFound(provider=ProviderId.ITUNES)
        return list(results)

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        payload = await self._get("/search", term=query, media="music", entity="song", limit=limit)
        return map_search(payload)

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Universal search: one ``/search`` request per requested type, concurrently.

        iTunes has no playlist search, so a requested ``PLAYLIST`` type is skipped;
        each supported type maps its own ``entity`` (``song``/``album``/``musicArtist``).
        """
        requested = [
            (entity_type, entity, mapper)
            for entity_type, entity, mapper in self._SEARCH_ENTITIES
            if entity_type in types
        ]
        if not requested:
            return []
        payloads = await asyncio.gather(
            *(
                self._get("/search", term=query, media="music", entity=entity, limit=limit)
                for _, entity, _ in requested
            )
        )
        hits: list[SearchHit] = []
        for (_, _, mapper), payload in zip(requested, payloads, strict=True):
            hits.extend(mapper(payload)[:limit])
        return hits

    async def enrich(self, track: Track) -> Track:
        fresh = await self._fresh_track(track)
        if fresh is None:
            return track
        updates: dict[str, Any] = {}
        if not track.genres and fresh.genres:
            updates["genres"] = fresh.genres
        if track.year is None and fresh.year is not None:
            updates["year"] = fresh.year
        if track.explicit is None and fresh.explicit is not None:
            updates["explicit"] = fresh.explicit
        if track.album is None and fresh.album is not None:
            updates["album"] = fresh.album
        elif (
            track.album is not None
            and fresh.album is not None
            and track.album.cover_url is None
            and fresh.album.cover_url is not None
        ):
            updates["album"] = track.album.model_copy(update={"cover_url": fresh.album.cover_url})
        return track.model_copy(update=updates) if updates else track

    async def _fresh_track(self, track: Track) -> Track | None:
        """Fetch the best iTunes track for ``track`` (by id, else by search)."""
        if track.provider is ProviderId.ITUNES and track.provider_id:
            results = await self._lookup(track.provider_id)
            song = next((r for r in results if r.get("trackName")), None)
            return map_track(song) if song else None
        matches = await self.search(f"{track.main_artist} {track.name}", limit=1)
        return matches[0] if matches else None


# --- factory --------------------------------------------------------------


def build_itunes_provider(ctx: ProviderContext) -> ITunesProvider:
    """Construct an :class:`ITunesProvider` from a :class:`ProviderContext`."""
    client = create_client(user_agent=ctx.user_agent, base_url=_API_BASE)
    return ITunesProvider(client)
