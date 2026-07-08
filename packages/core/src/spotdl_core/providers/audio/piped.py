"""Piped provider: audio candidates via a rotating list of public instances.

Piped is a privacy-friendly YouTube frontend with a JSON API. Public instances
are frequently rate-limited or down, so this provider is configured with a
**list** of instances (:attr:`ProviderContext.piped_instances`, defaulting to
:data:`~spotdl_core.providers.registry.DEFAULT_PIPED_INSTANCES`) and fails over
between them: for each instance it health-checks ``GET {inst}/healthcheck`` and,
if healthy, searches ``GET {inst}/search?q=...&filter=videos``. The first
instance that answers wins.

Two behaviours are **contract**: Piped ``duration`` is in **seconds** and stored
as milliseconds (``*1000``); when **all** configured instances fail their
health/search, the provider raises :class:`ProviderUnavailable` (it never
crashes the registry). This provider is **public-instance dependent** and
expected to be flaky in the wild.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import parse_qs, urlsplit

import httpx

from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_core.providers.base import HttpProvider
from spotdl_core.providers.errors import ProviderUnavailable
from spotdl_core.providers.http import create_client

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext

__all__ = [
    "PipedProvider",
    "build_piped_provider",
]

_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"

#: Short timeout for the per-instance healthcheck so a dead instance is skipped
#: quickly rather than blocking the whole failover chain.
_HEALTH_TIMEOUT = 5.0


# --- pure mapper ----------------------------------------------------------


def _video_id(url: str) -> str | None:
    """Extract the ``v=`` video id from a Piped ``/watch?v=<id>`` url."""
    query = parse_qs(urlsplit(url).query)
    values = query.get("v")
    return values[0] if values else None


def _map_piped_search(items: list[dict[str, Any]]) -> list[AudioCandidate]:
    """Map Piped ``/search`` items to audio candidates (best-first).

    Only ``type == "stream"`` items become candidates; items without a video id
    or title are skipped. ``duration`` (seconds) becomes ``duration_ms``,
    ``uploaderVerified`` becomes ``verified`` and ``views`` becomes
    ``popularity``. The candidate url is the canonical YouTube watch url so the
    download engine (Plan 4) can consume it directly.
    """
    candidates: list[AudioCandidate] = []
    for item in items:
        if item.get("type") != "stream":
            continue
        video_id = _video_id(item.get("url") or "")
        title = item.get("title")
        if not video_id or not title:
            continue
        uploader = item.get("uploaderName") or item.get("uploader")
        duration = item.get("duration")
        candidates.append(
            AudioCandidate(
                provider=ProviderId.PIPED,
                provider_id=video_id,
                url=_WATCH_URL.format(video_id=video_id),
                name=title,
                artists=(uploader,) if uploader else (),
                duration_ms=(
                    int(duration) * 1000
                    if isinstance(duration, int | float) and duration >= 0
                    else None
                ),
                verified=bool(item.get("uploaderVerified")),
                popularity=item.get("views"),
            )
        )
    return candidates


# --- provider -------------------------------------------------------------


class PipedProvider(HttpProvider):
    """Piped audio-candidate provider with cross-instance failover.

    Implements :class:`~spotdl_core.providers.base.ProvidesAudio`.
    """

    id: ClassVar[ProviderId] = ProviderId.PIPED

    def __init__(self, client: httpx.AsyncClient, *, instances: tuple[str, ...]) -> None:
        super().__init__(client)
        self._instances = instances

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        query = f"{track.main_artist} - {track.name}"
        items = await self._search(query)
        return _map_piped_search(items)[:limit]

    async def _search(self, query: str) -> list[dict[str, Any]]:
        """Search the first healthy instance; fail over on any error.

        Raises :class:`ProviderUnavailable` when every configured instance fails
        its healthcheck or search.
        """
        for instance in self._instances:
            base = instance.rstrip("/")
            try:
                health = await self._client.get(f"{base}/healthcheck", timeout=_HEALTH_TIMEOUT)
                if health.status_code != 200:
                    continue
                response = await self._client.get(
                    f"{base}/search", params={"q": query, "filter": "videos"}
                )
                if response.status_code != 200:
                    continue
                body = response.json()
            except (httpx.HTTPError, ValueError):
                continue
            items = body.get("items") if isinstance(body, dict) else None
            return list(items) if isinstance(items, list) else []
        raise ProviderUnavailable(
            "all Piped instances failed health/search", provider=ProviderId.PIPED
        )


# --- factory --------------------------------------------------------------


def build_piped_provider(ctx: ProviderContext) -> PipedProvider:
    """Construct a :class:`PipedProvider` from a :class:`ProviderContext`."""
    client = create_client(user_agent=ctx.user_agent, timeout=15.0)
    return PipedProvider(client, instances=ctx.piped_instances)
