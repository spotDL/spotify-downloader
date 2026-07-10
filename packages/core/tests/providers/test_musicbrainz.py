"""Tests for the MusicBrainz metadata provider (Task 8).

Every test is offline except the single ``@pytest.mark.network`` live check:
pure-mapper tests run from checked-in JSON fixtures, and all HTTP behaviour is
mocked with ``respx``. The two mapping subtleties are asserted explicitly:
``length`` is **already milliseconds** (never multiplied), and an ISRC lookup's
recording carries no ``isrcs`` list -- the looked-up ISRC is threaded in
instead. The rate-limiter test injects a fake clock/sleep so it runs instantly
while still proving requests are spaced ``>= 1.0`` second (contract).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from spotdl_core.model import EntityType, ProviderId, Track
from spotdl_core.providers.base import Enriches, Resolves, Searches, SearchesEntities
from spotdl_core.providers.errors import EntityNotFound, UnsupportedURL
from spotdl_core.providers.http import create_client
from spotdl_core.providers.metadata.musicbrainz import (
    MusicBrainzProvider,
    _RateLimiter,
    build_musicbrainz_provider,
    cover_art_url,
    lucene_query,
    map_artist_hits,
    map_recording,
    map_release_group_hits,
    map_search,
)
from spotdl_core.providers.registry import ProviderContext, build_default_registry
from spotdl_core.providers.urls import PlatformRef

_API = "https://musicbrainz.org/ws/2"
_MBID = "f1a6a40f-78f5-4918-968d-f64363bae94c"
_ISRC = "GBDUW0000059"


def _provider(client: httpx.AsyncClient) -> MusicBrainzProvider:
    # Give a zero-interval limiter so respx tests are not slowed by real spacing.
    return MusicBrainzProvider(client, limiter=_RateLimiter(0.0))


# --- pure mappers ---------------------------------------------------------


def test_map_recording_from_fixture(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "recording")
    track = map_recording(payload)

    assert track.name == payload["title"]
    assert track.provider is ProviderId.MUSICBRAINZ
    assert track.provider_id == payload["id"]
    # artist-credit flattening
    assert track.artists == ("Daft Punk",)
    assert track.main_artist == "Daft Punk"
    # isrcs[0] picked up when present
    assert track.isrc == payload["isrcs"][0]
    # releases[0] -> AlbumRef with year from date[:4]
    assert track.album is not None
    assert track.album.name == payload["releases"][0]["title"]
    assert track.album.year == int(payload["releases"][0]["date"][:4])
    assert track.year == track.album.year


def test_map_recording_length_is_milliseconds(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "recording")
    track = map_recording(payload)
    # CONTRACT: MusicBrainz ``length`` is already milliseconds -- never *1000.
    assert track.duration_ms == payload["length"]
    assert track.duration_ms == 224293


def test_map_recording_isrc_argument_overrides(load_fixture: Any) -> None:
    # An ISRC-lookup recording omits ``isrcs``; the looked-up ISRC is threaded in.
    recording = load_fixture("musicbrainz", "isrc_lookup")["recordings"][0]
    assert "isrcs" not in recording
    track = map_recording(recording, isrc=_ISRC)
    assert track.isrc == _ISRC


def test_map_recording_multi_artist_flattening() -> None:
    recording = {
        "id": "x",
        "title": "Collab",
        "length": 200000,
        "artist-credit": [
            {"name": "Alpha", "joinphrase": " & "},
            {"artist": {"name": "Beta"}},
            {"name": "Alpha"},  # duplicate is dropped, order preserved
        ],
    }
    track = map_recording(recording)
    assert track.artists == ("Alpha", "Beta")


def test_map_recording_missing_length_defaults_zero() -> None:
    recording = {"id": "x", "title": "No Length", "artist-credit": [{"name": "A"}]}
    track = map_recording(recording)
    assert track.duration_ms == 0
    assert track.album is None


def test_map_recording_year_falls_back_to_first_release_date() -> None:
    recording = {
        "id": "x",
        "title": "T",
        "artist-credit": [{"name": "A"}],
        "first-release-date": "1998-07-01",
    }
    track = map_recording(recording)
    assert track.year == 1998


def test_map_search_returns_tracks(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "search")
    tracks = map_search(payload)
    assert tracks
    assert all(isinstance(t, Track) for t in tracks)
    assert all(t.provider is ProviderId.MUSICBRAINZ for t in tracks)
    assert tracks[0].name == payload["recordings"][0]["title"]


def test_map_search_score_threshold_filters() -> None:
    payload = {
        "recordings": [
            {"id": "1", "title": "Hi", "score": 100, "artist-credit": [{"name": "A"}]},
            {"id": "2", "title": "Lo", "score": 40, "artist-credit": [{"name": "A"}]},
        ]
    }
    kept = map_search(payload, min_score=80)
    assert [t.provider_id for t in kept] == ["1"]


def test_map_search_accepts_ext_score_alias() -> None:
    rec = {"id": "1", "title": "Hi", "ext:score": "95", "artist-credit": [{"name": "A"}]}
    assert map_search({"recordings": [rec]}, min_score=80)


def test_map_search_skips_unmappable() -> None:
    payload = {
        "recordings": [
            {"id": "1", "title": "", "artist-credit": [{"name": "A"}]},  # no title
            {"id": "2", "title": "T", "artist-credit": []},  # no artist
            {"id": "3", "title": "Good", "artist-credit": [{"name": "A"}]},
        ]
    }
    assert [t.provider_id for t in map_search(payload)] == ["3"]


def test_lucene_query_shape_and_escaping() -> None:
    q = lucene_query('Say "Hi"', "A\\B", album="Rel")
    assert q == 'recording:"Say \\"Hi\\"" AND artist:"A\\\\B" AND release:"Rel"'
    # album omitted when unknown
    assert lucene_query("T", "A") == 'recording:"T" AND artist:"A"'


# --- rate limiter (contract) ----------------------------------------------


async def test_rate_limiter_spaces_requests() -> None:
    # CONTRACT: >= 1.0s between outbound requests. Inject a fake clock + sleep so
    # the test is instant but still verifies the enforced gap.
    now = {"t": 0.0}
    slept: list[float] = []

    def clock() -> float:
        return now["t"]

    async def sleep(delay: float) -> None:
        slept.append(delay)
        now["t"] += delay

    limiter = _RateLimiter(1.0, clock=clock, sleep=sleep)

    start_first = clock()
    await limiter.acquire()  # first call: immediate
    start_second = clock()  # still 0.0 -- no time has really passed
    await limiter.acquire()  # must wait to honour the 1.0s spacing
    start_third = clock()
    await limiter.acquire()

    # The first request did not sleep; each subsequent one waited >= 1.0s.
    assert slept == [1.0, 1.0]
    assert start_second - start_first == 0.0
    assert start_third - start_second >= 1.0
    # clock advanced by exactly the enforced gaps
    assert now["t"] == pytest.approx(2.0)


async def test_rate_limiter_no_wait_when_interval_elapsed() -> None:
    now = {"t": 0.0}
    slept: list[float] = []

    def clock() -> float:
        return now["t"]

    async def sleep(delay: float) -> None:  # pragma: no cover - must not run
        slept.append(delay)
        now["t"] += delay

    limiter = _RateLimiter(1.0, clock=clock, sleep=sleep)
    await limiter.acquire()
    now["t"] = 5.0  # more than the interval has elapsed
    await limiter.acquire()
    assert slept == []  # no sleep needed


# --- provider (respx) -----------------------------------------------------


@respx.mock
async def test_resolve_track_returns_track(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "recording")
    route = respx.get(f"{_API}/recording/{_MBID}").mock(
        return_value=httpx.Response(200, json=payload)
    )
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.TRACK, _MBID)
    async with create_client(base_url=_API + "/") as client:
        resolved = await _provider(client).resolve(ref)

    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    assert resolved.track.duration_ms == payload["length"]
    assert resolved.track.isrc == payload["isrcs"][0]
    # request carried fmt=json + the include set
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["fmt"] == "json"
    assert params["inc"] == "artists+releases+isrcs"


@respx.mock
async def test_resolve_playlist_raises_unsupported() -> None:
    # Playlists have no MusicBrainz equivalent (tracks/albums/artists resolve).
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.PLAYLIST, "some-playlist")
    async with create_client(base_url=_API + "/") as client:
        with pytest.raises(UnsupportedURL):
            await _provider(client).resolve(ref)


@respx.mock
async def test_resolve_404_raises_entity_not_found() -> None:
    respx.get(f"{_API}/recording/{_MBID}").mock(return_value=httpx.Response(404))
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.TRACK, _MBID)
    async with create_client(base_url=_API + "/") as client:
        with pytest.raises(EntityNotFound):
            await _provider(client).resolve(ref)


@respx.mock
async def test_search_returns_tracks_and_sends_lucene(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "search")
    route = respx.get(f"{_API}/recording").mock(return_value=httpx.Response(200, json=payload))
    async with create_client(base_url=_API + "/") as client:
        tracks = await _provider(client).search("Daft Punk Harder", limit=3)
    assert tracks
    assert all(t.provider is ProviderId.MUSICBRAINZ for t in tracks)
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["query"] == "Daft Punk Harder"
    assert params["limit"] == "3"
    assert params["fmt"] == "json"


@respx.mock
async def test_search_empty_returns_empty_list() -> None:
    respx.get(f"{_API}/recording").mock(
        return_value=httpx.Response(200, json={"count": 0, "recordings": []})
    )
    async with create_client(base_url=_API + "/") as client:
        assert await _provider(client).search("nothing at all") == []


@respx.mock
async def test_enrich_fills_isrc_via_isrc_lookup(load_fixture: Any) -> None:
    payload = load_fixture("musicbrainz", "isrc_lookup")
    route = respx.get(f"{_API}/isrc/{_ISRC}").mock(return_value=httpx.Response(200, json=payload))
    bare = Track(
        name="Harder, Better, Faster, Stronger",
        artists=("Daft Punk",),
        duration_ms=224293,
        isrc=_ISRC,  # ISRC known but year/album missing
        provider=ProviderId.MUSICBRAINZ,
    )
    async with create_client(base_url=_API + "/") as client:
        enriched = await _provider(client).enrich(bare)
    # ISRC preserved; year filled from first-release-date (no releases on isrc lookup)
    assert enriched.isrc == _ISRC
    assert enriched.year == 2001
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["inc"] == "artists+releases"


@respx.mock
async def test_enrich_falls_back_to_name_search(load_fixture: Any) -> None:
    search_payload = load_fixture("musicbrainz", "search")
    respx.get(f"{_API}/isrc/{_ISRC}").mock(return_value=httpx.Response(404))
    search_route = respx.get(f"{_API}/recording").mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    bare = Track(
        name="Harder, Better, Faster, Stronger",
        artists=("Daft Punk",),
        duration_ms=1,
        isrc=_ISRC,  # ISRC set but the lookup 404s -> name search
        provider=ProviderId.MUSICBRAINZ,
    )
    async with create_client(base_url=_API + "/") as client:
        enriched = await _provider(client).enrich(bare)
    assert enriched.album is not None  # album filled from search result
    q = httpx.QueryParams(search_route.calls.last.request.url.query)["query"]
    assert 'recording:"Harder, Better, Faster, Stronger"' in q
    assert 'artist:"Daft Punk"' in q


@respx.mock
async def test_enrich_no_match_returns_original() -> None:
    respx.get(f"{_API}/recording").mock(return_value=httpx.Response(200, json={"recordings": []}))
    bare = Track(
        name="Totally Unknown",
        artists=("Nobody",),
        duration_ms=1000,
        provider=ProviderId.MUSICBRAINZ,
    )
    async with create_client(base_url=_API + "/") as client:
        assert await _provider(client).enrich(bare) is bare


# --- ISRC fielded search (bug fix) ----------------------------------------


@respx.mock
async def test_search_isrc_query_is_fielded() -> None:
    # CONTRACT: a bare ISRC matches nothing, so an ISRC-shaped query is issued as
    # the fielded ``isrc:`` Lucene query (this is the enrichment ISRC-search fix).
    route = respx.get(f"{_API}/recording").mock(
        return_value=httpx.Response(200, json={"recordings": []})
    )
    async with create_client(base_url=_API + "/") as client:
        await _provider(client).search("USUM71027402")
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["query"] == "isrc:USUM71027402"


@respx.mock
async def test_search_non_isrc_query_is_unchanged() -> None:
    route = respx.get(f"{_API}/recording").mock(
        return_value=httpx.Response(200, json={"recordings": []})
    )
    async with create_client(base_url=_API + "/") as client:
        await _provider(client).search("Kanye West Runaway")
    params = httpx.QueryParams(route.calls.last.request.url.query)
    assert params["query"] == "Kanye West Runaway"  # not ISRC-shaped -> verbatim


# --- entity search --------------------------------------------------------


def test_cover_art_url_is_constructed() -> None:
    # CONTRACT: the Cover Art Archive URL is built, never fetched.
    assert cover_art_url("mbid-1") == "https://coverartarchive.org/release-group/mbid-1/front-250"


def test_map_artist_hits() -> None:
    payload = {
        "artists": [
            {"id": "a1", "name": "Daft Punk", "country": "FR"},
            {"id": "", "name": "skip me"},  # no id -> dropped
        ]
    }
    hits = map_artist_hits(payload)
    assert len(hits) == 1
    assert hits[0].entity_type is EntityType.ARTIST
    assert hits[0].provider is ProviderId.MUSICBRAINZ
    assert hits[0].provider_id == "a1"
    assert hits[0].subtitle == "FR"  # country -> subtitle
    assert hits[0].cover_url is None  # MusicBrainz exposes no artist image


def test_map_release_group_hits() -> None:
    payload = {
        "release-groups": [
            {
                "id": "rg1",
                "title": "Discovery",
                "first-release-date": "2001-03-12",
                "primary-type": "Album",
                "artist-credit": [{"name": "Daft Punk"}],
            }
        ]
    }
    hits = map_release_group_hits(payload)
    assert len(hits) == 1
    assert hits[0].entity_type is EntityType.ALBUM
    assert hits[0].provider_id == "rg1"
    assert hits[0].name == "Discovery"
    assert hits[0].subtitle == "Daft Punk"  # artist credit -> subtitle
    assert hits[0].year == 2001
    assert hits[0].cover_url == cover_art_url("rg1")  # constructed, not fetched


@respx.mock
async def test_search_entities_artist_and_album() -> None:
    artist_route = respx.get(f"{_API}/artist").mock(
        return_value=httpx.Response(
            200, json={"artists": [{"id": "a1", "name": "Daft Punk", "country": "FR"}]}
        )
    )
    album_route = respx.get(f"{_API}/release-group").mock(
        return_value=httpx.Response(
            200,
            json={"release-groups": [{"id": "rg1", "title": "Discovery"}]},
        )
    )
    async with create_client(base_url=_API + "/") as client:
        hits = await _provider(client).search_entities("Daft Punk", limit=5)
    kinds = {hit.entity_type for hit in hits}
    assert kinds == {EntityType.ARTIST, EntityType.ALBUM}
    assert httpx.QueryParams(artist_route.calls.last.request.url.query)["query"] == "Daft Punk"
    assert httpx.QueryParams(album_route.calls.last.request.url.query)["query"] == "Daft Punk"


@respx.mock
async def test_search_entities_track_only_returns_nothing() -> None:
    # Tracks are served by ``search`` (not ``search_entities``); no request is made.
    async with create_client(base_url=_API + "/") as client:
        hits = await _provider(client).search_entities(
            "Daft Punk", types=frozenset({EntityType.TRACK})
        )
    assert hits == []


# --- artist resolve (tags + discography browse) ---------------------------


@respx.mock
async def test_resolve_artist_maps_tags_and_discography() -> None:
    mbid = "056e4f3e-d505-4dad-8ec1-d04f521cbb56"
    respx.get(f"{_API}/artist/{mbid}").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": mbid,
                "name": "Daft Punk",
                "country": "FR",
                "tags": [
                    {"name": "electronic", "count": 10},
                    {"name": "house", "count": 25},  # higher count sorts first
                ],
            },
        )
    )
    browse_route = respx.get(f"{_API}/release-group").mock(
        return_value=httpx.Response(
            200,
            json={
                "release-groups": [
                    {
                        "id": "rg1",
                        "title": "Discovery",
                        "primary-type": "Album",
                        "first-release-date": "2001-03-12",
                    },
                    {"id": "rg2", "title": "Discovery"},  # dup name -> deduped
                    {
                        "id": "rg3",
                        "title": "Homework",
                        "primary-type": "Album",
                        "first-release-date": "1997",
                    },
                ]
            },
        )
    )
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.ARTIST, mbid)
    async with create_client(base_url=_API + "/") as client:
        resolved = await _provider(client).resolve(ref)

    assert resolved.entity_type is EntityType.ARTIST
    assert resolved.artist is not None
    assert resolved.artist.genres == ("house", "electronic")  # ordered by count desc
    assert resolved.tracks == ()  # no top tracks; overlap gate uses albums
    names = [album.name for album in resolved.albums]
    assert names == ["Discovery", "Homework"]  # deduped by name
    disc = resolved.albums[0]
    assert disc.album_type == "album"  # primary-type lowercased
    assert disc.year == 2001
    assert disc.provider is ProviderId.MUSICBRAINZ and disc.provider_id == "rg1"
    assert disc.cover_url == cover_art_url("rg1")
    browse_params = httpx.QueryParams(browse_route.calls.last.request.url.query)
    assert browse_params["artist"] == mbid
    assert browse_params["type"] == "album|single|ep"


@respx.mock
async def test_resolve_artist_survives_discography_failure() -> None:
    mbid = "artist-mbid"
    respx.get(f"{_API}/artist/{mbid}").mock(
        return_value=httpx.Response(200, json={"id": mbid, "name": "Nobody", "tags": []})
    )
    respx.get(f"{_API}/release-group").mock(return_value=httpx.Response(503))
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.ARTIST, mbid)
    async with create_client(base_url=_API + "/") as client:
        resolved = await _provider(client).resolve(ref)
    assert resolved.artist is not None and resolved.artist.name == "Nobody"
    assert resolved.albums == ()  # a browse failure degrades to no discography


# --- album resolve (release-group -> release -> tracks) -------------------


@respx.mock
async def test_resolve_album_expands_release_tracks() -> None:
    rg_mbid = "rg-discovery"
    rel_mbid = "rel-official"
    respx.get(f"{_API}/release-group/{rg_mbid}").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": rg_mbid,
                "title": "Discovery",
                "primary-type": "Album",
                "first-release-date": "2001-03-12",
                "artist-credit": [{"name": "Daft Punk"}],
                "releases": [
                    {"id": "rel-promo", "status": "Promotion"},
                    {"id": rel_mbid, "status": "Official"},  # preferred
                ],
            },
        )
    )
    release_route = respx.get(f"{_API}/release/{rel_mbid}").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": rel_mbid,
                "title": "Discovery",
                "media": [
                    {
                        "position": 1,
                        "tracks": [
                            {
                                "position": 1,
                                "title": "One More Time",
                                "length": 320000,
                                "artist-credit": [{"name": "Daft Punk"}],
                                "recording": {"id": "rec1", "title": "One More Time"},
                            },
                            {
                                "position": 2,
                                "title": "Aerodynamic",
                                "recording": {
                                    "id": "rec2",
                                    "title": "Aerodynamic",
                                    "length": 205000,
                                    "artist-credit": [{"name": "Daft Punk"}],
                                },
                            },
                        ],
                    }
                ],
            },
        )
    )
    ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.ALBUM, rg_mbid)
    async with create_client(base_url=_API + "/") as client:
        resolved = await _provider(client).resolve(ref)

    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.album is not None
    assert resolved.album.name == "Discovery"
    assert resolved.album.album_artist == "Daft Punk"
    assert resolved.album.album_type == "album"
    assert resolved.album.year == 2001
    assert resolved.album.cover_url == cover_art_url(rg_mbid)
    assert [t.name for t in resolved.tracks] == ["One More Time", "Aerodynamic"]
    first, second = resolved.tracks
    assert first.duration_ms == 320000  # track-level length (already ms)
    assert first.track_number == 1 and first.disc_number == 1
    assert first.provider_id == "rec1"
    assert second.duration_ms == 205000  # falls back to recording length
    assert second.artists == ("Daft Punk",)  # falls back to recording artist-credit
    # the release was fetched with the recordings include set
    assert httpx.QueryParams(release_route.calls.last.request.url.query)["inc"] == (
        "recordings+artist-credits"
    )


# --- wiring / capabilities ------------------------------------------------


async def test_provider_advertises_capabilities() -> None:
    provider = build_musicbrainz_provider(ProviderContext())
    try:
        assert provider.id is ProviderId.MUSICBRAINZ
        assert isinstance(provider, Resolves)
        assert isinstance(provider, Searches)
        assert isinstance(provider, SearchesEntities)
        assert isinstance(provider, Enriches)
    finally:
        await provider.aclose()


def test_registered_in_default_registry() -> None:
    reg = build_default_registry(ProviderContext())
    assert ProviderId.MUSICBRAINZ in reg.registered
    provider = reg.get(ProviderId.MUSICBRAINZ)
    assert isinstance(provider, MusicBrainzProvider)


async def test_descriptive_user_agent_carries_contact() -> None:
    # MusicBrainz rejects generic UAs; the client must send a descriptive one.
    provider = build_musicbrainz_provider(ProviderContext())
    try:
        ua = provider._client.headers["User-Agent"]
        assert "http" in ua.lower()  # contains a contact URL
        assert ua.strip() != ""
    finally:
        await provider.aclose()


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_musicbrainz_resolve_known_recording() -> None:
    provider = build_musicbrainz_provider(ProviderContext())
    try:
        ref = PlatformRef(ProviderId.MUSICBRAINZ, EntityType.TRACK, _MBID)
        resolved = await provider.resolve(ref)
    finally:
        await provider.aclose()
    assert resolved.track is not None
    assert resolved.track.name == "Harder, Better, Faster, Stronger"
    assert resolved.track.duration_ms == 224293
    assert resolved.track.isrc
