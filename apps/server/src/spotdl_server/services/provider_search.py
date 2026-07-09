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

from spotdl_core.model import ProviderId, Track
from spotdl_core.providers import ProviderError, ProviderRegistry, Searches


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
