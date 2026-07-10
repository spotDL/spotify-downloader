"""Shared multi-provider search helper (CONTRACT).

Pure orchestration over the provider registry: it runs every ``Searches``
provider, merges their results in PROVIDER_ORDER, de-duplicates, and truncates.
It holds **no** DB session and persists nothing — callers (``ResolveService``'s
free-text fallback, Task 9's ``SearchService``) own any snapshotting. Created
here so Task 8 is self-contained and Task 9 reuses the exact same de-dup rule.

De-duplication is two-level and order-sensitive to PROVIDER_ORDER (so the
highest-priority provider's copy of a track wins):

* by **ISRC** — a later track whose ISRC was already seen is dropped;
* then by **(name, main_artist)** casefolded — a later track whose title/artist
  key was already seen is dropped (catching duplicates that lack an ISRC or
  carry a different one for the same recording).

A ``ProviderError`` from one searcher is caught: its id joins the returned failed
set and the remaining searchers still run (spec §10 "no silent fallbacks").
"""

from __future__ import annotations

from spotdl_core.model import EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers import (
    ProviderError,
    ProviderRegistry,
    Searches,
    SearchesEntities,
)


async def provider_search(
    registry: ProviderRegistry,
    query: str,
    *,
    limit: int = 20,
) -> tuple[list[Track], set[ProviderId]]:
    """Search every capable provider, merge + de-dup + truncate.

    Returns ``(tracks, failed_provider_ids)``. ``tracks`` is at most ``limit``
    entries in PROVIDER_ORDER precedence; ``failed_provider_ids`` are the
    searchers that raised a :class:`ProviderError`.
    """
    collected: list[Track] = []
    failed: set[ProviderId] = set()

    for searcher in registry.capable(Searches):  # type: ignore[type-abstract]
        try:
            results = await searcher.search(query, limit=limit)
        except ProviderError:
            failed.add(searcher.id)
            continue
        collected.extend(results)

    return _dedupe(collected)[:limit], failed


def _dedupe(tracks: list[Track]) -> list[Track]:
    """Drop later duplicates by ISRC, then by casefolded ``(name, main_artist)``."""
    seen_isrc: set[str] = set()
    seen_key: set[tuple[str, str]] = set()
    unique: list[Track] = []
    for track in tracks:
        if track.isrc is not None and track.isrc in seen_isrc:
            continue
        key = (track.name.casefold(), track.main_artist.casefold())
        if key in seen_key:
            continue
        if track.isrc is not None:
            seen_isrc.add(track.isrc)
        seen_key.add(key)
        unique.append(track)
    return unique


async def provider_search_entities(
    registry: ProviderRegistry,
    query: str,
    *,
    types: frozenset[EntityType],
    limit: int = 10,
) -> tuple[dict[EntityType, list[SearchHit]], set[ProviderId]]:
    """Universal search: fan out, merge per type in PROVIDER_ORDER, dedup, truncate.

    Every :class:`~spotdl_core.providers.SearchesEntities` provider is queried once
    for all requested ``types``. For the ``TRACK`` type, providers that only expose
    track-only :class:`~spotdl_core.providers.Searches` (and don't already do entity
    search) additionally contribute synthesised track hits, so a track-only source
    still appears in universal results. Results merge per type in ``capable`` order
    (PROVIDER_ORDER), so the highest-priority provider's copy wins de-duplication:

    * **tracks** — by ISRC, then casefolded ``(name, subtitle)`` (mirrors
      :func:`provider_search`'s two-level rule, keyed on the hit's fields);
    * **albums / artists / playlists** — by casefolded ``(name, subtitle)``.

    Each type is truncated to ``limit``. Returns ``(hits_by_type, failed)``; a
    provider raising :class:`~spotdl_core.providers.ProviderError` joins ``failed``
    and is skipped (spec §10 "no silent fallbacks"), never fatal. ``hits_by_type``
    always has an entry for every requested type (possibly empty).
    """
    collected: dict[EntityType, list[SearchHit]] = {entity_type: [] for entity_type in types}
    failed: set[ProviderId] = set()
    entity_capable: set[ProviderId] = set()

    for provider in registry.capable(SearchesEntities):  # type: ignore[type-abstract]
        entity_capable.add(provider.id)
        try:
            hits = await provider.search_entities(query, types=types, limit=limit)
        except ProviderError:
            failed.add(provider.id)
            continue
        for hit in hits:
            if hit.entity_type in collected:
                collected[hit.entity_type].append(hit)

    if EntityType.TRACK in types:
        for searcher in registry.capable(Searches):  # type: ignore[type-abstract]
            if searcher.id in entity_capable:
                continue  # already contributed richer entity search (incl. tracks)
            try:
                results = await searcher.search(query, limit=limit)
            except ProviderError:
                failed.add(searcher.id)
                continue
            for track in results:
                if track.provider is not None and track.provider_id is not None:
                    collected[EntityType.TRACK].append(SearchHit.from_track(track))

    merged = {
        entity_type: _dedupe_hits(entity_type, hits)[:limit]
        for entity_type, hits in collected.items()
    }
    return merged, failed


def _hit_key(hit: SearchHit) -> tuple[str, str]:
    return (hit.name.casefold(), (hit.subtitle or "").casefold())


def _dedupe_hits(entity_type: EntityType, hits: list[SearchHit]) -> list[SearchHit]:
    """Drop later duplicate hits per type (tracks also collapse by ISRC first)."""
    track_scope = entity_type is EntityType.TRACK
    seen_isrc: set[str] = set()
    seen_key: set[tuple[str, str]] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        if track_scope and hit.isrc is not None and hit.isrc in seen_isrc:
            continue
        key = _hit_key(hit)
        if key in seen_key:
            continue
        if track_scope and hit.isrc is not None:
            seen_isrc.add(hit.isrc)
        seen_key.add(key)
        unique.append(hit)
    return unique
