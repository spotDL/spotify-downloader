"""Spotify metadata provider: anonymous TOTP token + client-credentials fallback.

Both authentication strategies yield an ordinary **bearer token used against the
standard Web API** (``https://api.spotify.com/v1``). Unifying them behind one
:class:`SpotifyAuth` interface means the field mapping is identical regardless
of token origin and, crucially, that ``external_ids.isrc`` is present on
``/v1/tracks/{id}`` for both paths. This deliberately avoids the ``spotapi``
GraphQL pathfinder approach (no ISRC; requires scraping web-player query hashes).

Two auth implementations:

* :class:`AnonymousSpotifyAuth` -- fetches a token from
  ``open.spotify.com/api/token`` using a TOTP code (``pyotp``). No credentials
  required. The TOTP shared secret is pinned as a default but is **rotatable
  without a code release** via ``SPOTDL_SPOTIFY_TOTP_SECRET`` (spec §1: no
  hardcoded-shared-secret failure mode).
* :class:`ClientCredentialsSpotifyAuth` -- the classic
  ``POST accounts.spotify.com/api/token`` client-credentials grant, requiring an
  operator-supplied ``client_id`` / ``client_secret``.

:class:`LayeredSpotifyAuth` tries them in the order dictated by
``SpotifyConfig.prefer_anonymous`` and falls back to the secondary on *any*
breakage of the primary (auth rejection, transport failure, or a malformed token
payload), recording the live path in :attr:`LayeredSpotifyAuth.live_path`.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import httpx
import pyotp

from spotdl_core.model import AlbumRef, ArtistRef, EntityType, ProviderId, SearchHit, Track
from spotdl_core.providers.base import ALL_SEARCH_ENTITY_TYPES, HttpProvider, ResolvedEntity
from spotdl_core.providers.errors import (
    ProviderAuthError,
    ProviderError,
    UnsupportedURL,
)
from spotdl_core.providers.http import create_client, request_json

if TYPE_CHECKING:
    from spotdl_core.providers.registry import ProviderContext, SpotifyConfig
    from spotdl_core.providers.urls import PlatformRef

__all__ = [
    "AnonymousSpotifyAuth",
    "ClientCredentialsSpotifyAuth",
    "LayeredSpotifyAuth",
    "SpotifyAuth",
    "SpotifyProvider",
    "build_spotify_provider",
    "map_album",
    "map_search",
    "map_search_hits",
    "map_track",
]

#: Spotify's ``/v1/search`` ``type`` vocabulary, keyed by the domain entity type.
_SEARCH_TYPE_PARAM: dict[EntityType, str] = {
    EntityType.TRACK: "track",
    EntityType.ALBUM: "album",
    EntityType.ARTIST: "artist",
    EntityType.PLAYLIST: "playlist",
}
#: The response section key ``/v1/search`` returns for each ``type`` (pluralised).
_SEARCH_SECTION: dict[EntityType, str] = {
    EntityType.TRACK: "tracks",
    EntityType.ALBUM: "albums",
    EntityType.ARTIST: "artists",
    EntityType.PLAYLIST: "playlists",
}

_API_BASE = "https://api.spotify.com"
_ANON_TOKEN_URL = "https://open.spotify.com/api/token"
_CC_TOKEN_URL = "https://accounts.spotify.com/api/token"

#: Refresh a cached token this many milliseconds before it actually expires.
_REFRESH_SKEW_MS = 30_000.0

#: Album-tracks page size (Spotify caps ``limit`` at 50).
_PAGE_LIMIT = 50

#: Pinned default TOTP cipher for the anonymous-token flow. This mirrors the
#: ``spotapi``/web-player scheme: each byte is XOR-transformed, the decimal
#: digits are concatenated and base32-encoded to form the ``pyotp`` secret. The
#: value rotates whenever Spotify rotates its web-player secret; it is only a
#: *default* -- operators override it via ``SPOTDL_SPOTIFY_TOTP_SECRET``
#: (``SpotifyConfig.totp_secret_override``) with a fresh base32 secret, so a
#: rotation never requires a spotDL release. Source of current secrets:
#: https://github.com/xyloflake/spot-secrets-go (secrets/secretDict.json).
_PINNED_TOTP_CIPHER: tuple[int, ...] = (
    44,
    55,
    47,
    42,
    70,
    40,
    34,
    114,
    76,
    74,
    50,
    111,
    120,
    97,
    75,
    76,
    94,
    102,
    43,
    69,
    49,
    120,
    118,
    80,
    64,
    78,
)
#: Version tag sent as ``totpVer``. Spotify accepts any value as long as the
#: TOTP code validates against the *current* server secret, so this is purely
#: informational, but we send the version matching the pinned cipher.
_PINNED_TOTP_VERSION = 61


def _derive_totp_secret(cipher: tuple[int, ...]) -> str:
    """Derive the base32 ``pyotp`` secret from a web-player cipher byte array."""
    transformed = [byte ^ ((index % 33) + 9) for index, byte in enumerate(cipher)]
    joined = "".join(str(value) for value in transformed)
    return base64.b32encode(joined.encode()).decode().rstrip("=")


# --- auth interface -------------------------------------------------------


class SpotifyAuth(Protocol):
    """Yields a Web API bearer token, refreshing/caching as needed."""

    async def bearer_token(self) -> str: ...


def _now_ms() -> float:
    return time.time() * 1000.0


class AnonymousSpotifyAuth:
    """Anonymous web-player token via TOTP against ``open.spotify.com``.

    ``totp_secret`` overrides the pinned default; it is the base32 secret used
    directly by :class:`pyotp.TOTP`. The shared ``client`` is reused (the token
    endpoint is a different host, addressed by absolute URL).
    """

    live_path: ClassVar[str] = "anonymous"

    def __init__(self, client: httpx.AsyncClient, *, totp_secret: str | None = None) -> None:
        self._client = client
        self._secret = totp_secret or _derive_totp_secret(_PINNED_TOTP_CIPHER)
        self._token: str | None = None
        self._expires_at_ms = 0.0

    async def bearer_token(self) -> str:
        now = _now_ms()
        if self._token is not None and now < self._expires_at_ms - _REFRESH_SKEW_MS:
            return self._token
        code = pyotp.TOTP(self._secret, digits=6, interval=30).now()
        payload = await request_json(
            self._client,
            "GET",
            _ANON_TOKEN_URL,
            provider=ProviderId.SPOTIFY,
            params={
                "reason": "transport",
                "productType": "web-player",
                "totp": code,
                "totpServer": code,
                "totpVer": _PINNED_TOTP_VERSION,
            },
        )
        token = _validate_token(
            payload,
            token_key="accessToken",
            expiry=_anon_expiry,
        )
        self._token = token
        self._expires_at_ms = float(payload["accessTokenExpirationTimestampMs"])
        return token


class ClientCredentialsSpotifyAuth:
    """Classic client-credentials grant against ``accounts.spotify.com``."""

    live_path: ClassVar[str] = "client_credentials"

    def __init__(self, client: httpx.AsyncClient, *, client_id: str, client_secret: str) -> None:
        self._client = client
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._expires_at_ms = 0.0

    async def bearer_token(self) -> str:
        now = _now_ms()
        if self._token is not None and now < self._expires_at_ms - _REFRESH_SKEW_MS:
            return self._token
        basic = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
        payload = await request_json(
            self._client,
            "POST",
            _CC_TOKEN_URL,
            provider=ProviderId.SPOTIFY,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        token = _validate_token(payload, token_key="access_token", expiry=_cc_expiry)
        self._token = token
        self._expires_at_ms = now + float(payload["expires_in"]) * 1000.0
        return token


def _anon_expiry(payload: dict[str, Any]) -> bool:
    """A plausible anonymous expiry is a future epoch-ms timestamp."""
    exp = payload.get("accessTokenExpirationTimestampMs")
    return isinstance(exp, int | float) and not isinstance(exp, bool) and exp > _now_ms()


def _cc_expiry(payload: dict[str, Any]) -> bool:
    """A plausible client-credentials expiry is a positive ``expires_in``."""
    exp = payload.get("expires_in")
    return isinstance(exp, int | float) and not isinstance(exp, bool) and exp > 0


def _validate_token(
    payload: Any,
    *,
    token_key: str,
    expiry: Callable[[dict[str, Any]], bool],
) -> str:
    """Validate a 2xx token body's shape; never trust an arbitrary 2xx.

    Raises :class:`ProviderAuthError` unless ``payload`` is a mapping carrying a
    non-empty ``str`` access token under ``token_key`` and a plausible expiry.
    """
    if not isinstance(payload, dict):
        raise ProviderAuthError(
            "spotify token payload is not an object", provider=ProviderId.SPOTIFY
        )
    token = payload.get(token_key)
    if not isinstance(token, str) or not token:
        raise ProviderAuthError(
            "spotify token payload has no access token", provider=ProviderId.SPOTIFY
        )
    if not expiry(payload):
        raise ProviderAuthError(
            "spotify token payload has an implausible expiry", provider=ProviderId.SPOTIFY
        )
    return token


class LayeredSpotifyAuth:
    """Tries anonymous/client-credentials in ``prefer_anonymous`` order.

    Falls back to the secondary strategy on *any* breakage of the primary --
    :class:`ProviderAuthError` (401/403 or malformed payload) or
    :class:`ProviderUnavailable` (transport failure / repeated 5xx). Falls back
    only when a secondary is configured; otherwise the primary's error
    propagates. :attr:`live_path` records the strategy that last produced a
    token, for ``degraded_sources`` reporting.
    """

    def __init__(
        self,
        *,
        anonymous: SpotifyAuth | None,
        client_credentials: SpotifyAuth | None,
        prefer_anonymous: bool = True,
    ) -> None:
        ordered: list[tuple[str, SpotifyAuth | None]] = [
            ("anonymous", anonymous),
            ("client_credentials", client_credentials),
        ]
        if not prefer_anonymous:
            ordered.reverse()
        self._chain: list[tuple[str, SpotifyAuth]] = [
            (name, auth) for name, auth in ordered if auth is not None
        ]
        self.live_path: str | None = None

    async def bearer_token(self) -> str:
        if not self._chain:
            raise ProviderAuthError(
                "no spotify auth strategy configured", provider=ProviderId.SPOTIFY
            )
        last_error: ProviderError | None = None
        for name, auth in self._chain:
            try:
                token = await auth.bearer_token()
            except ProviderError as exc:
                # Any breakage of this path (auth rejection, transport failure /
                # repeated 5xx via ProviderUnavailable, or a malformed token
                # payload raised as ProviderAuthError) triggers fallback.
                last_error = exc
                continue
            self.live_path = name
            return token
        assert last_error is not None  # a non-empty chain always yields an error here
        raise last_error


# --- pure mappers ---------------------------------------------------------


def _year(release_date: str | None) -> int | None:
    if not release_date:
        return None
    head = release_date[:4]
    return int(head) if head.isdigit() else None


def _largest_image(images: list[dict[str, Any]] | None) -> str | None:
    """Return the URL of the largest cover image (by pixel area)."""
    if not images:
        return None
    best = max(images, key=lambda img: (img.get("width") or 0) * (img.get("height") or 0))
    url = best.get("url")
    return url if isinstance(url, str) else None


def _artist_names(payload: dict[str, Any]) -> tuple[str, ...]:
    return tuple(a["name"] for a in payload.get("artists", []) if a.get("name"))


def _album_ref(album_payload: dict[str, Any]) -> AlbumRef:
    artists = album_payload.get("artists") or []
    album_artist = artists[0]["name"] if artists and artists[0].get("name") else None
    return AlbumRef(
        name=album_payload["name"],
        album_artist=album_artist,
        year=_year(album_payload.get("release_date")),
        track_count=album_payload.get("total_tracks"),
        cover_url=_largest_image(album_payload.get("images")),
    )


def map_track(payload: dict[str, Any]) -> Track:
    """Map a full ``/v1/tracks/{id}`` (or search) track object to a ``Track``."""
    album_payload = payload.get("album")
    album = _album_ref(album_payload) if album_payload else None
    return Track(
        name=payload["name"],
        artists=_artist_names(payload),
        duration_ms=payload["duration_ms"],
        album=album,
        isrc=(payload.get("external_ids") or {}).get("isrc"),
        explicit=payload.get("explicit"),
        track_number=payload.get("track_number"),
        disc_number=payload.get("disc_number"),
        year=album.year if album else None,
        provider=ProviderId.SPOTIFY,
        provider_id=payload["id"],
    )


def _map_album_track(payload: dict[str, Any], album: AlbumRef) -> Track:
    """Map a simplified album-track object, injecting the album context."""
    return Track(
        name=payload["name"],
        artists=_artist_names(payload),
        duration_ms=payload["duration_ms"],
        album=album,
        isrc=(payload.get("external_ids") or {}).get("isrc"),
        explicit=payload.get("explicit"),
        track_number=payload.get("track_number"),
        disc_number=payload.get("disc_number"),
        year=album.year,
        provider=ProviderId.SPOTIFY,
        provider_id=payload["id"],
    )


def map_album(payload: dict[str, Any], tracks: list[dict[str, Any]]) -> ResolvedEntity:
    """Map an album payload plus its (paginated) simplified track objects."""
    album = _album_ref(payload)
    mapped = tuple(_map_album_track(track, album) for track in tracks)
    return ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id=payload["id"],
        entity_type=EntityType.ALBUM,
        album=album,
        name=payload.get("name"),
        tracks=mapped,
    )


def map_search(payload: dict[str, Any]) -> list[Track]:
    """Map a ``/v1/search?type=track`` payload to a list of ``Track``."""
    items = (payload.get("tracks") or {}).get("items") or []
    return [map_track(item) for item in items if item]


def _track_hit(item: dict[str, Any]) -> SearchHit:
    return SearchHit.from_track(map_track(item))


def _album_hit(item: dict[str, Any]) -> SearchHit:
    artists = item.get("artists") or []
    subtitle = artists[0]["name"] if artists and artists[0].get("name") else None
    return SearchHit(
        entity_type=EntityType.ALBUM,
        provider=ProviderId.SPOTIFY,
        provider_id=item["id"],
        name=item["name"],
        subtitle=subtitle,
        cover_url=_largest_image(item.get("images")),
        year=_year(item.get("release_date")),
    )


def _artist_hit(item: dict[str, Any]) -> SearchHit:
    return SearchHit(
        entity_type=EntityType.ARTIST,
        provider=ProviderId.SPOTIFY,
        provider_id=item["id"],
        name=item["name"],
        subtitle=None,
        cover_url=_largest_image(item.get("images")),
    )


def _playlist_hit(item: dict[str, Any]) -> SearchHit:
    owner = (item.get("owner") or {}).get("display_name")
    return SearchHit(
        entity_type=EntityType.PLAYLIST,
        provider=ProviderId.SPOTIFY,
        provider_id=item["id"],
        name=item["name"],
        subtitle=owner,
        cover_url=_largest_image(item.get("images")),
    )


#: Per-entity ``search`` item → :class:`SearchHit` mappers.
_HIT_MAPPERS: dict[EntityType, Callable[[dict[str, Any]], SearchHit]] = {
    EntityType.TRACK: _track_hit,
    EntityType.ALBUM: _album_hit,
    EntityType.ARTIST: _artist_hit,
    EntityType.PLAYLIST: _playlist_hit,
}


def map_search_hits(
    payload: dict[str, Any], types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES
) -> list[SearchHit]:
    """Map a multi-type ``/v1/search`` payload to a flat :class:`SearchHit` list.

    Each requested section (``tracks``/``albums``/``artists``/``playlists``) is
    mapped in a stable type order; Spotify occasionally returns ``null`` array
    entries, which are skipped. An item that lacks the ``id``/``name`` a hit needs
    is dropped rather than raising.
    """
    hits: list[SearchHit] = []
    for entity_type in _SEARCH_TYPE_PARAM:
        if entity_type not in types:
            continue
        section = payload.get(_SEARCH_SECTION[entity_type]) or {}
        mapper = _HIT_MAPPERS[entity_type]
        for item in section.get("items") or []:
            if item and item.get("id") and item.get("name"):
                hits.append(mapper(item))
    return hits


# --- provider -------------------------------------------------------------


class SpotifyProvider(HttpProvider):
    """Resolve/search/enrich against the Spotify Web API using an injected auth.

    Implements :class:`~spotdl_core.providers.base.Resolves`,
    :class:`~spotdl_core.providers.base.Searches`,
    :class:`~spotdl_core.providers.base.SearchesEntities` and
    :class:`~spotdl_core.providers.base.Enriches`.
    """

    id: ClassVar[ProviderId] = ProviderId.SPOTIFY

    def __init__(self, client: httpx.AsyncClient, auth: SpotifyAuth) -> None:
        super().__init__(client)
        self._auth = auth

    async def _get(self, path: str, **params: Any) -> Any:
        headers = {"Authorization": f"Bearer {await self._auth.bearer_token()}"}
        return await request_json(
            self._client,
            "GET",
            path,
            provider=ProviderId.SPOTIFY,
            headers=headers,
            params=params or None,
        )

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        if ref.entity_type is EntityType.TRACK:
            return await self._resolve_track(ref.entity_id)
        if ref.entity_type is EntityType.ALBUM:
            return await self._resolve_album(ref.entity_id)
        if ref.entity_type is EntityType.ARTIST:
            return await self._resolve_artist(ref.entity_id)
        if ref.entity_type is EntityType.PLAYLIST:
            return await self._resolve_playlist(ref.entity_id)
        raise UnsupportedURL(f"spotify cannot resolve entity type {ref.entity_type}")

    async def _resolve_track(self, entity_id: str) -> ResolvedEntity:
        payload = await self._get(f"/v1/tracks/{entity_id}")
        return ResolvedEntity(
            provider=ProviderId.SPOTIFY,
            provider_id=entity_id,
            entity_type=EntityType.TRACK,
            track=map_track(payload),
        )

    async def _resolve_album(self, entity_id: str) -> ResolvedEntity:
        album = await self._get(f"/v1/albums/{entity_id}")
        page = album.get("tracks") or {}
        tracks: list[dict[str, Any]] = list(page.get("items") or [])
        offset = len(tracks)
        total = page.get("total")
        while page.get("next"):
            page = await self._get(
                f"/v1/albums/{entity_id}/tracks", offset=offset, limit=_PAGE_LIMIT
            )
            items = page.get("items") or []
            if not items:
                break
            tracks.extend(items)
            offset += len(items)
            if isinstance(total, int) and offset >= total:
                break
        return map_album(album, tracks)

    async def _resolve_artist(self, entity_id: str) -> ResolvedEntity:
        artist = await self._get(f"/v1/artists/{entity_id}")
        top = await self._get(f"/v1/artists/{entity_id}/top-tracks", market="US")
        tracks = tuple(map_track(item) for item in (top.get("tracks") or []) if item)
        return ResolvedEntity(
            provider=ProviderId.SPOTIFY,
            provider_id=entity_id,
            entity_type=EntityType.ARTIST,
            artist=ArtistRef(
                name=artist["name"], provider=ProviderId.SPOTIFY, provider_id=entity_id
            ),
            name=artist.get("name"),
            tracks=tracks,
        )

    async def _resolve_playlist(self, entity_id: str) -> ResolvedEntity:
        playlist = await self._get(f"/v1/playlists/{entity_id}")
        page = playlist.get("tracks") or {}
        tracks: list[Track] = _playlist_page_tracks(page)
        next_url = page.get("next")
        while next_url:
            page = await self._get(next_url)
            tracks.extend(_playlist_page_tracks(page))
            next_url = page.get("next")
        return ResolvedEntity(
            provider=ProviderId.SPOTIFY,
            provider_id=entity_id,
            entity_type=EntityType.PLAYLIST,
            name=playlist.get("name"),
            tracks=tuple(tracks),
        )

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        payload = await self._get("/v1/search", q=query, type="track", limit=limit)
        return map_search(payload)

    async def search_entities(
        self,
        query: str,
        *,
        types: frozenset[EntityType] = ALL_SEARCH_ENTITY_TYPES,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Universal search: one ``/v1/search`` call across the requested types."""
        requested = [t for t in _SEARCH_TYPE_PARAM if t in types]
        if not requested:
            return []
        type_param = ",".join(_SEARCH_TYPE_PARAM[t] for t in requested)
        payload = await self._get("/v1/search", q=query, type=type_param, limit=limit)
        return map_search_hits(payload, frozenset(requested))

    async def enrich(self, track: Track) -> Track:
        entity_id = _spotify_track_id(track)
        if entity_id is None:
            return track
        payload = await self._get(f"/v1/tracks/{entity_id}")
        fresh = map_track(payload)
        updates: dict[str, Any] = {}
        if track.isrc is None and fresh.isrc is not None:
            updates["isrc"] = fresh.isrc
        if track.year is None and fresh.year is not None:
            updates["year"] = fresh.year
        if track.album is None and fresh.album is not None:
            updates["album"] = fresh.album
        elif (
            track.album is not None
            and fresh.album is not None
            and track.album.cover_url is None
            and fresh.album.cover_url is not None
        ):
            updates["album"] = track.album.model_copy(update={"cover_url": fresh.album.cover_url})
        if not track.genres:
            genres = await self._artist_genres(payload)
            if genres:
                updates["genres"] = genres
        return track.model_copy(update=updates) if updates else track

    async def _artist_genres(self, track_payload: dict[str, Any]) -> tuple[str, ...]:
        artists = track_payload.get("artists") or []
        if not artists or not artists[0].get("id"):
            return ()
        artist = await self._get(f"/v1/artists/{artists[0]['id']}")
        return tuple(g for g in (artist.get("genres") or ()) if g)


def _spotify_track_id(track: Track) -> str | None:
    if track.provider is ProviderId.SPOTIFY and track.provider_id:
        return track.provider_id
    return None


def _playlist_page_tracks(page: dict[str, Any]) -> list[Track]:
    tracks: list[Track] = []
    for item in page.get("items") or []:
        inner = item.get("track") if isinstance(item, dict) else None
        if isinstance(inner, dict) and inner.get("id") and inner.get("name"):
            tracks.append(map_track(inner))
    return tracks


# --- factory --------------------------------------------------------------


def _build_auth(client: httpx.AsyncClient, config: SpotifyConfig) -> LayeredSpotifyAuth:
    anonymous = AnonymousSpotifyAuth(client, totp_secret=config.totp_secret_override)
    client_credentials: ClientCredentialsSpotifyAuth | None = None
    if config.client_id and config.client_secret:
        client_credentials = ClientCredentialsSpotifyAuth(
            client, client_id=config.client_id, client_secret=config.client_secret
        )
    return LayeredSpotifyAuth(
        anonymous=anonymous,
        client_credentials=client_credentials,
        prefer_anonymous=config.prefer_anonymous,
    )


def build_spotify_provider(ctx: ProviderContext) -> SpotifyProvider:
    """Construct a :class:`SpotifyProvider` from a :class:`ProviderContext`."""
    client = create_client(user_agent=ctx.user_agent, base_url=_API_BASE)
    return SpotifyProvider(client, _build_auth(client, ctx.spotify))
