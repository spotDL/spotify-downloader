"""``SearchViewModel`` — query → track rows, and paste-a-URL → router ref (CONTRACT A)."""

from __future__ import annotations

from spotdl_cli.viewmodels.base import ErrorDisplay, Loadable, guard
from spotdl_cli.viewmodels.mappers import entity_ref, track_row
from spotdl_cli.viewmodels.protocol import SpotdlClientProtocol
from spotdl_cli.viewmodels.types import ResolveOutcome, SearchResult


class SearchViewModel:
    def __init__(self, client: SpotdlClientProtocol) -> None:
        self._client = client

    async def search(self, query: str, *, limit: int = 20) -> Loadable[SearchResult]:
        async def _run() -> SearchResult:
            result = await self._client.search(query, limit=limit)
            rows = tuple(track_row(track) for track in result.tracks)
            sources = tuple(result.degraded_sources)
            return SearchResult(rows=rows, degraded=bool(sources), degraded_sources=sources)

        return await guard(_run())

    async def open(self, query: str) -> Loadable[ResolveOutcome]:
        """Resolve a pasted URL/query to a router ``EntityRef`` (CONTRACT C)."""
        resolved = await guard(self._client.resolve(query))
        if resolved.error is not None:
            return Loadable.failed(resolved.error)
        assert resolved.data is not None
        ref = entity_ref(resolved.data)
        if ref is None:
            return Loadable.failed(
                ErrorDisplay(
                    "couldn't resolve that link to a track, album, artist, or playlist",
                    code=None,
                    severity="error",
                )
            )
        return Loadable.ready(
            ResolveOutcome(ref=ref, degraded=bool(resolved.data.degraded_sources))
        )
