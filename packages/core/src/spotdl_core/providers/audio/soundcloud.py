"""SoundCloud provider: audio candidates plus track resolve, via scraping.

SoundCloud exposes no stable public API without a ``client_id``, so the default
path **scrapes** the public web pages: the search page embeds a
``window.__sc_hydration`` JSON blob and every track page embeds a ``sound``
hydratable carrying the full track object. ``beautifulsoup4`` is imported
**lazily** inside the extraction helper so a broken install degrades only this
provider (the isolation constraint); network/parse failures raise
:class:`ProviderUnavailable` and never crash the registry.

If :attr:`ProviderContext.soundcloud_client_id` is supplied, the faster
``api-v2`` search path is used instead of scraping. When it is not, the provider
**lazily discovers** a public ``client_id`` on the first search by scraping
soundcloud.com's asset bundles (the keyless hydration scrape returns nothing —
the results are JS-rendered). Discovery is best-effort and cached for the
provider's lifetime: on failure the provider falls back to the hydration scrape,
and an api-v2 ``401``/``403`` (a rotated id) triggers a single re-discovery. Both
search paths feed the same :func:`_map_soundcloud_hydration` mapper.

This is a **fragile scraper**: the selectors/regex below track SoundCloud's
current markup and are expected to need maintenance. One mapping rule is
**contract**: SoundCloud ``duration`` is already in **milliseconds** and is
stored as-is (never ``*1000``).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import quote

import httpx

from spotdl_core.model import AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.base import HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, ProviderUnavailable, UnsupportedURL
from spotdl_core.providers.http import create_client

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "SoundCloudProvider",
    "build_soundcloud_provider",
]

_SEARCH_URL = "https://soundcloud.com/search/sounds"
_TRACK_BASE = "https://soundcloud.com"
_API_SEARCH_URL = "https://api-v2.soundcloud.com/search/tracks"

#: A browser-like User-Agent; SoundCloud rejects unfamiliar agents.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

#: The search/track pages embed their state as ``window.__sc_hydration = [...]``.
_HYDRATION_RE = re.compile(r"window\.__sc_hydration\s*=\s*(\[.*?\]);", re.DOTALL)

#: The homepage references the api-v2 asset bundles that carry a public client_id.
_HOME_URL = "https://soundcloud.com/"

#: ``<script crossorigin src="https://a-v2.sndcdn.com/assets/*.js">`` bundle URLs.
_ASSET_RE = re.compile(r'<script[^>]+src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"')

#: A public ``client_id`` appears as a 32-char alphanumeric literal in a bundle.
_CLIENT_ID_RE = re.compile(r'client_id\s*[:=]\s*"([a-zA-Z0-9]{32})"')


# --- pure mappers ---------------------------------------------------------


def _track_to_candidate(track: dict[str, Any]) -> AudioCandidate | None:
    """Map one SoundCloud track object to an :class:`AudioCandidate`.

    Returns ``None`` for non-track collection entries (e.g. users) or tracks
    missing an id/title.
    """
    if track.get("kind") != "track":
        return None
    track_id = track.get("id")
    title = track.get("title")
    if not track_id or not title:
        return None
    user = track.get("user") or {}
    username = user.get("username")
    return AudioCandidate(
        provider=ProviderId.SOUNDCLOUD,
        provider_id=str(track_id),
        url=track.get("permalink_url") or "",
        name=title,
        artists=(username,) if username else (),
        # CONTRACT: SoundCloud ``duration`` is already milliseconds; store as-is.
        duration_ms=track.get("duration") if isinstance(track.get("duration"), int) else None,
        verified=False,
        popularity=track.get("playback_count"),
    )


def _map_soundcloud_hydration(hydration: list[dict[str, Any]]) -> list[AudioCandidate]:
    """Map a ``__sc_hydration`` blob to audio candidates (best-first).

    Walks every hydratable's ``data.collection`` (the search page nests its
    results there) and keeps entries whose ``kind`` is ``"track"``.
    """
    candidates: list[AudioCandidate] = []
    for item in hydration:
        data = item.get("data")
        if not isinstance(data, dict):
            continue
        collection = data.get("collection")
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if isinstance(entry, dict):
                candidate = _track_to_candidate(entry)
                if candidate is not None:
                    candidates.append(candidate)
    return candidates


def _sound_from_hydration(hydration: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the ``sound`` hydratable's track object from a track page blob."""
    for item in hydration:
        if item.get("hydratable") == "sound":
            data = item.get("data")
            if isinstance(data, dict):
                return data
    return None


def _sound_to_track(sound: dict[str, Any], provider_id: str) -> Track | None:
    """Map a ``sound`` track object to a :class:`Track` (``None`` if incomplete)."""
    title = sound.get("title")
    user = sound.get("user") or {}
    username = user.get("username")
    duration = sound.get("duration")
    if not title or not username or not isinstance(duration, int):
        return None
    return Track(
        name=title,
        artists=(username,),
        duration_ms=duration,  # ms as-is (contract)
        provider=ProviderId.SOUNDCLOUD,
        provider_id=provider_id,
    )


def _extract_hydration(html: str) -> list[dict[str, Any]]:
    """Extract and parse the ``__sc_hydration`` JSON blob from page HTML.

    ``beautifulsoup4`` is imported lazily here so a broken install degrades only
    this provider. Returns an empty list when no blob is present or it does not
    parse.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.SOUNDCLOUD
        ) from exc
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        if "__sc_hydration" not in text:
            continue
        match = _HYDRATION_RE.search(text)
        if match is None:
            continue
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            return parsed
    return []


# --- provider -------------------------------------------------------------


class _ClientIdRejected(Exception):
    """Internal signal: api-v2 rejected the ``client_id`` (401/403) — re-discover."""


class SoundCloudProvider(HttpProvider):
    """SoundCloud audio + track-resolve provider (scraper).

    Implements :class:`~spotdl_core.providers.base.ProvidesAudio` and
    :class:`~spotdl_core.providers.base.Resolves`.
    """

    id: ClassVar[ProviderId] = ProviderId.SOUNDCLOUD

    def __init__(self, client: httpx.AsyncClient, *, client_id: str | None = None) -> None:
        super().__init__(client)
        #: An operator-configured id (authoritative — never discovered/replaced).
        self._client_id = client_id
        #: A lazily discovered public id, cached for the provider's lifetime.
        self._discovered_id: str | None = None
        #: Whether keyless discovery has been attempted (so a miss is not retried
        #: on every search — only a 401/403 forces an explicit re-discovery).
        self._discovery_attempted = False

    async def _get_text(self, url: str, **kwargs: Any) -> str:
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"soundcloud request failed: {exc}", provider=ProviderId.SOUNDCLOUD
            ) from exc
        return response.text

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        query = f"{track.main_artist} - {track.name}"
        client_id = await self._search_client_id()
        if client_id is None:
            # Neither configured nor discoverable → scrape (may yield nothing).
            return await self._scrape_candidates(query, limit)
        try:
            return (await self._api_search(query, limit, client_id))[:limit]
        except _ClientIdRejected:
            pass
        # api-v2 rejected the id (401/403). An operator id is authoritative, so
        # give up gracefully; a discovered id may have rotated, so re-discover ONCE
        # and retry before giving up.
        if self._client_id:
            return []
        self._discovered_id = await self._discover_client_id()
        if self._discovered_id is None:
            return await self._scrape_candidates(query, limit)
        try:
            return (await self._api_search(query, limit, self._discovered_id))[:limit]
        except _ClientIdRejected:
            return []

    async def _search_client_id(self) -> str | None:
        """The ``client_id`` to search with: the operator's, else a discovered one.

        An operator-configured id is used verbatim (discovery is skipped). Otherwise
        a public id is discovered lazily on the first search and cached for the
        provider's lifetime; ``None`` means neither is available (the caller then
        falls back to the hydration scrape).
        """
        if self._client_id:
            return self._client_id
        if not self._discovery_attempted:
            self._discovery_attempted = True
            self._discovered_id = await self._discover_client_id()
        return self._discovered_id

    async def _discover_client_id(self) -> str | None:
        """Best-effort scrape of a public ``client_id`` from soundcloud.com.

        The homepage references a handful of ``a-v2.sndcdn.com`` asset bundles and
        the id lives in one of them (usually the last), so bundles are scanned
        last-first. Any transport/parse failure yields ``None`` — the caller falls
        back to the hydration scrape; discovery never raises.
        """
        try:
            home = await self._get_text(_HOME_URL)
        except ProviderUnavailable:
            return None
        for asset_url in reversed(_ASSET_RE.findall(home)):
            try:
                bundle = await self._get_text(asset_url)
            except ProviderUnavailable:
                continue
            match = _CLIENT_ID_RE.search(bundle)
            if match is not None:
                return match.group(1)
        return None

    async def _scrape_candidates(self, query: str, limit: int) -> list[AudioCandidate]:
        """Fall-back path: parse candidates from the search page's hydration JSON."""
        html = await self._get_text(f"{_SEARCH_URL}?q={quote(query)}")
        return _map_soundcloud_hydration(_extract_hydration(html))[:limit]

    async def _api_search(self, query: str, limit: int, client_id: str) -> list[AudioCandidate]:
        """Search via the ``api-v2`` endpoint with ``client_id``.

        A ``401``/``403`` (a stale/rotated id) raises :class:`_ClientIdRejected` so
        the caller can re-discover; any other transport/parse failure raises
        :class:`ProviderUnavailable`.
        """
        try:
            response = await self._client.get(
                _API_SEARCH_URL,
                params={"q": query, "client_id": client_id, "limit": limit},
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (401, 403):
                raise _ClientIdRejected from exc
            raise ProviderUnavailable(
                f"soundcloud api search failed: {exc}", provider=ProviderId.SOUNDCLOUD
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(
                f"soundcloud api search failed: {exc}", provider=ProviderId.SOUNDCLOUD
            ) from exc
        # Reuse the hydration mapper by wrapping the collection response.
        return _map_soundcloud_hydration([{"data": body}])

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is not EntityType.TRACK:
            raise UnsupportedURL(f"soundcloud cannot resolve entity type {ref.entity_type}")
        url = ref.url or f"{_TRACK_BASE}/{ref.entity_id}"
        html = await self._get_text(url)
        sound = _sound_from_hydration(_extract_hydration(html))
        track = _sound_to_track(sound, ref.entity_id) if sound is not None else None
        if track is None:
            raise EntityNotFound(provider=ProviderId.SOUNDCLOUD)
        return ResolvedEntity(
            provider=ProviderId.SOUNDCLOUD,
            provider_id=ref.entity_id,
            entity_type=EntityType.TRACK,
            track=track,
        )


# --- factory --------------------------------------------------------------


def build_soundcloud_provider(ctx: ProviderContext) -> SoundCloudProvider:
    """Construct a :class:`SoundCloudProvider` from a :class:`ProviderContext`.

    ``beautifulsoup4`` is imported lazily on first scrape, so building the
    provider (and therefore registry construction) never imports it.
    """
    client = create_client(user_agent=_USER_AGENT, timeout=30.0)
    return SoundCloudProvider(client, client_id=ctx.soundcloud_client_id)
