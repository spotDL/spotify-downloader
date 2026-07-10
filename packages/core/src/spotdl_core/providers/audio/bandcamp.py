"""Bandcamp provider: audio candidates plus track resolve, via scraping.

Bandcamp has no public API, so this provider **scrapes**: the search page lists
``li.searchresult`` items and every track page embeds a ``TralbumData`` (a.k.a.
``data-tralbum``) JSON object carrying the full track detail. ``beautifulsoup4``
is imported **lazily** inside the parsing helpers so a broken install degrades
only this provider (the isolation constraint); network/parse failures raise
:class:`ProviderUnavailable` and never crash the registry.

This is a **fragile scraper**: the selectors/regex below track Bandcamp's
current markup and are expected to need maintenance. One mapping rule is
**contract**: Bandcamp ``trackinfo[0].duration`` is in **seconds** and is
converted to milliseconds (``*1000``); cover art is
``https://f4.bcbits.com/img/a{art_id}_10.jpg``.
"""

from __future__ import annotations

import html as html_module
import json
import re
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from spotdl_core.model import AlbumRef, AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.base import HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import EntityNotFound, ProviderUnavailable, UnsupportedURL
from spotdl_core.providers.http import create_client

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "BandcampProvider",
    "build_bandcamp_provider",
]

_SEARCH_URL = "https://bandcamp.com/search"

#: A browser-like User-Agent; Bandcamp serves a stripped page to unknown agents.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

#: The track page embeds ``var TralbumData = {...};``.
_TRALBUM_RE = re.compile(r"TralbumData\s*=\s*(\{.*?\});", re.DOTALL)
_ART_URL = "https://f4.bcbits.com/img/a{art_id}_10.jpg"


# --- pure mappers ---------------------------------------------------------


def _clean(text: str) -> str:
    """Collapse whitespace runs (Bandcamp markup is heavily indented)."""
    return re.sub(r"\s+", " ", text).strip()


def _parse_subhead(text: str) -> tuple[str | None, str | None]:
    """Parse a Bandcamp subhead into ``(artist, album)``.

    Track subheads read ``from <Album> by <Artist>`` or just ``by <Artist>``.
    """
    cleaned = _clean(text)
    if cleaned.startswith("by "):
        return cleaned[len("by ") :].strip() or None, None
    if " by " not in cleaned:
        return None, None
    head, _, artist_part = cleaned.rpartition(" by ")
    artist = artist_part.strip() or None
    album = None
    head = head.strip()
    if head.lower().startswith("from "):
        album = head[len("from ") :].strip() or None
    return artist, album


def _strip_query(url: str) -> str:
    """Drop query/fragment (Bandcamp appends ``?from=search...`` tracking)."""
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, "", ""))


def _search_result_to_candidate(result: Any) -> AudioCandidate | None:
    """Map one ``li.searchresult`` element to an :class:`AudioCandidate`.

    Only ``TRACK`` results are returned; albums/artists are dropped. The numeric
    id is read from the element's ``data-search`` JSON blob when present.
    """
    itemtype = result.find("div", class_="itemtype")
    if itemtype is None or _clean(itemtype.get_text()).upper() != "TRACK":
        return None
    heading = result.find("div", class_="heading")
    if heading is None:
        return None
    link = heading.find("a")
    if link is None or not link.get("href"):
        return None
    url = _strip_query(str(link.get("href")))
    name = _clean(link.get_text())
    if not name:
        return None
    subhead = result.find("div", class_="subhead")
    artist, album = _parse_subhead(subhead.get_text()) if subhead is not None else (None, None)
    provider_id = _search_result_id(result) or url
    return AudioCandidate(
        provider=ProviderId.BANDCAMP,
        provider_id=provider_id,
        url=url,
        name=name,
        artists=(artist,) if artist else (),
        album=album,
        duration_ms=None,
        verified=False,
    )


def _search_result_id(result: Any) -> str | None:
    """Extract the numeric id from a ``data-search`` attribute, if present."""
    raw = result.get("data-search")
    if not raw:
        return None
    try:
        blob = json.loads(html_module.unescape(str(raw)))
    except json.JSONDecodeError:
        return None
    item_id = blob.get("id") if isinstance(blob, dict) else None
    return str(item_id) if item_id is not None else None


def _map_bandcamp_search(page_html: str, *, limit: int = 10) -> list[AudioCandidate]:
    """Parse a Bandcamp search page into track audio candidates (best-first)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover - exercised only on broken installs
        raise ProviderUnavailable(
            "beautifulsoup4 is not available", provider=ProviderId.BANDCAMP
        ) from exc
    soup = BeautifulSoup(page_html, "lxml")
    candidates: list[AudioCandidate] = []
    for result in soup.find_all("li", class_="searchresult"):
        candidate = _search_result_to_candidate(result)
        if candidate is not None:
            candidates.append(candidate)
            if len(candidates) >= limit:
                break
    return candidates


def _year(release_date: str | None) -> int | None:
    """Extract a four-digit year from a Bandcamp release-date string."""
    if not release_date:
        return None
    match = re.search(r"\b(\d{4})\b", release_date)
    return int(match.group(1)) if match else None


def _map_bandcamp_tralbum(data: dict[str, Any], url: str) -> Track:
    """Map a ``TralbumData`` object to a :class:`Track`.

    Raises :class:`EntityNotFound` if the required fields (title, artist,
    duration) are absent. ``trackinfo[0].duration`` is seconds -> milliseconds.
    """
    trackinfo = data.get("trackinfo") or []
    track = trackinfo[0] if trackinfo else {}
    current = data.get("current") or {}
    title = current.get("title") or track.get("title")
    artist = data.get("artist")
    duration = track.get("duration")
    if not title or not artist or not isinstance(duration, int | float):
        raise EntityNotFound(provider=ProviderId.BANDCAMP)
    art_id = data.get("art_id")
    album_title = data.get("album_title")
    year = _year(current.get("release_date") or data.get("release_date"))
    album = (
        AlbumRef(
            name=album_title,
            album_artist=artist,
            year=year,
            cover_url=_ART_URL.format(art_id=art_id) if art_id is not None else None,
        )
        if album_title
        else None
    )
    track_id = track.get("id")
    return Track(
        name=title,
        artists=(artist,),
        duration_ms=int(round(float(duration) * 1000)),
        album=album,
        year=year,
        provider=ProviderId.BANDCAMP,
        provider_id=str(track_id) if track_id is not None else _strip_query(url),
    )


def _extract_tralbum(page_html: str) -> dict[str, Any] | None:
    """Extract and parse the ``TralbumData`` JSON object from track-page HTML."""
    match = _TRALBUM_RE.search(page_html)
    if match is None:
        return None
    body = match.group(1)
    # Bandcamp occasionally injects ``// comments`` inside the object literal.
    body = re.sub(r"//[^\n]*", "", body)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


# --- provider -------------------------------------------------------------


class BandcampProvider(HttpProvider):
    """Bandcamp audio + track-resolve provider (scraper).

    Implements :class:`~spotdl_core.providers.base.ProvidesAudio` and
    :class:`~spotdl_core.providers.base.Resolves`.
    """

    id: ClassVar[ProviderId] = ProviderId.BANDCAMP

    async def _get_text(self, url: str, **kwargs: Any) -> str:
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"bandcamp request failed: {exc}", provider=ProviderId.BANDCAMP
            ) from exc
        # Bandcamp serves a JS anti-bot page ("Client Challenge") to non-browser
        # clients with HTTP 200 — parsing it yields zero results, which read as a
        # silent "no matches". Surface it as an honest degraded source instead.
        if "<title>Client Challenge</title>" in response.text:
            raise ProviderUnavailable(
                "bandcamp is serving an anti-bot client challenge",
                provider=ProviderId.BANDCAMP,
            )
        return response.text

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        query = f"{track.main_artist} - {track.name}"
        page_html = await self._get_text(f"{_SEARCH_URL}?q={quote(query)}&item_type=t")
        return _map_bandcamp_search(page_html, limit=limit)

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is not EntityType.TRACK:
            raise UnsupportedURL(f"bandcamp cannot resolve entity type {ref.entity_type}")
        url = ref.url or _track_url_from_id(ref.entity_id)
        page_html = await self._get_text(url)
        data = _extract_tralbum(page_html)
        if data is None:
            raise EntityNotFound(provider=ProviderId.BANDCAMP)
        return ResolvedEntity(
            provider=ProviderId.BANDCAMP,
            provider_id=ref.entity_id,
            entity_type=EntityType.TRACK,
            track=_map_bandcamp_tralbum(data, url),
        )


def _track_url_from_id(entity_id: str) -> str:
    """Rebuild a track URL from a ``artist/track/slug`` platform id."""
    parts = entity_id.split("/")
    if len(parts) == 3:
        artist, kind, slug = parts
        return f"https://{artist}.bandcamp.com/{kind}/{slug}"
    return entity_id


# --- factory --------------------------------------------------------------


def build_bandcamp_provider(ctx: ProviderContext) -> BandcampProvider:
    """Construct a :class:`BandcampProvider` from a :class:`ProviderContext`.

    ``beautifulsoup4`` is imported lazily on first scrape, so building the
    provider (and therefore registry construction) never imports it.
    """
    client = create_client(user_agent=_USER_AGENT, timeout=30.0)
    return BandcampProvider(client)
