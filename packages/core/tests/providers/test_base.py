from typing import ClassVar

import httpx
import pytest
from spotdl_core.model import (
    AudioCandidate,
    EntityType,
    Lyrics,
    LyricsKind,
    ProviderId,
    Track,
)
from spotdl_core.providers.base import (
    Enriches,
    HttpProvider,
    Provider,
    ProvidesAudio,
    ProvidesLyrics,
    ResolvedEntity,
    Resolves,
    Searches,
)
from spotdl_core.providers.urls import PlatformRef


class FakeResolver:
    id: ClassVar[ProviderId] = ProviderId.DEEZER

    async def resolve(self, ref: PlatformRef) -> ResolvedEntity:
        return ResolvedEntity(
            provider=self.id,
            provider_id=ref.entity_id,
            entity_type=EntityType.TRACK,
            track=Track(name="x", artists=("a",), duration_ms=1000),
        )


class FakeSearcher:
    id: ClassVar[ProviderId] = ProviderId.SPOTIFY

    async def search(self, query: str, *, limit: int = 10) -> list[Track]:
        return [Track(name=query, artists=("a",), duration_ms=1000)]


class FakeEnricher:
    id: ClassVar[ProviderId] = ProviderId.MUSICBRAINZ

    async def enrich(self, track: Track) -> Track:
        return track


class FakeAudio:
    id: ClassVar[ProviderId] = ProviderId.YOUTUBE

    async def audio_candidates(self, track: Track, *, limit: int = 10) -> list[AudioCandidate]:
        return [
            AudioCandidate(
                provider=self.id,
                provider_id="v",
                url="https://example.com",
                name=track.name,
            )
        ]


class FakeLyrics:
    id: ClassVar[ProviderId] = ProviderId.LRCLIB

    async def lyrics(self, track: Track) -> Lyrics | None:
        return Lyrics(kind=LyricsKind.PLAIN, text="la la la", source=self.id)


def test_resolver_satisfies_resolves_and_provider() -> None:
    r = FakeResolver()
    assert isinstance(r, Resolves)
    assert isinstance(r, Provider)
    assert not isinstance(r, ProvidesAudio)


def test_searcher_satisfies_searches_only() -> None:
    s = FakeSearcher()
    assert isinstance(s, Searches)
    assert isinstance(s, Provider)
    assert not isinstance(s, Resolves)


def test_enricher_satisfies_enriches_only() -> None:
    e = FakeEnricher()
    assert isinstance(e, Enriches)
    assert isinstance(e, Provider)
    assert not isinstance(e, ProvidesLyrics)


def test_audio_provider_satisfies_provides_audio() -> None:
    a = FakeAudio()
    assert isinstance(a, ProvidesAudio)
    assert isinstance(a, Provider)
    assert not isinstance(a, ProvidesLyrics)


def test_lyrics_provider_satisfies_provides_lyrics() -> None:
    lyr = FakeLyrics()
    assert isinstance(lyr, ProvidesLyrics)
    assert isinstance(lyr, Provider)
    assert not isinstance(lyr, ProvidesAudio)


def test_bare_object_is_no_capability() -> None:
    obj = object()
    assert not isinstance(obj, Provider)
    assert not isinstance(obj, Resolves)
    assert not isinstance(obj, Searches)
    assert not isinstance(obj, Enriches)
    assert not isinstance(obj, ProvidesAudio)
    assert not isinstance(obj, ProvidesLyrics)


def test_resolved_entity_is_frozen() -> None:
    e = ResolvedEntity(provider=ProviderId.DEEZER, provider_id="1", entity_type=EntityType.TRACK)
    with pytest.raises(Exception):  # noqa: B017, PT011 - pydantic frozen raises ValidationError
        e.name = "y"  # type: ignore[misc]


def test_resolved_entity_defaults() -> None:
    e = ResolvedEntity(provider=ProviderId.DEEZER, provider_id="1", entity_type=EntityType.TRACK)
    assert e.track is None
    assert e.album is None
    assert e.artist is None
    assert e.name is None
    assert e.tracks == ()


async def test_resolved_entity_track_roundtrip() -> None:
    r = FakeResolver()
    e = await r.resolve(PlatformRef(ProviderId.DEEZER, EntityType.TRACK, "1"))
    assert e.track is not None
    assert e.track.name == "x"


async def test_lyrics_roundtrip() -> None:
    lyr = FakeLyrics()
    result = await lyr.lyrics(Track(name="x", artists=("a",), duration_ms=1000))
    assert result is not None
    assert result.text == "la la la"


async def test_http_provider_aclose_closes_client() -> None:
    class _Fake(HttpProvider):
        id: ClassVar[ProviderId] = ProviderId.DEEZER

    async with httpx.AsyncClient() as raw:
        provider = _Fake(raw)
        assert provider._client is raw
        await provider.aclose()
        assert raw.is_closed
