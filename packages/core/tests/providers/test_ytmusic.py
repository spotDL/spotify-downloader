"""Tests for the YTMusic audio + metadata provider (Task 9).

Every test is offline except the ``@pytest.mark.network`` live search:
pure-mapper tests run from checked-in JSON fixtures recorded from a real
``YTMusic.search(...)``/``get_song``/``get_album``, and the fetch methods are
tested with a fake ``YTMusic`` client injected in place of the real library.

The mapping contracts asserted here are: ``resultType == "song"`` sets
``verified=True`` (videos set ``verified=False``), and the ``"m:ss"`` duration
string is converted to milliseconds.
"""

from __future__ import annotations

from typing import Any

import pytest
from spotdl_core.model import AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers.audio.ytmusic import (
    YTMusicProvider,
    build_ytmusic_provider,
    map_results,
    map_search_tracks,
)
from spotdl_core.providers.base import ProvidesAudio, Resolves, Searches
from spotdl_core.providers.registry import ProviderContext
from spotdl_core.providers.urls import PlatformRef

_QUERY_TRACK = Track(
    name="Get Lucky",
    artists=("Daft Punk",),
    duration_ms=248_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


class _FakeYTMusic:
    """Stand-in for ``ytmusicapi.YTMusic`` returning recorded fixtures."""

    def __init__(
        self,
        *,
        songs: list[dict[str, Any]] | None = None,
        videos: list[dict[str, Any]] | None = None,
        song: dict[str, Any] | None = None,
        album: dict[str, Any] | None = None,
    ) -> None:
        self._songs = songs or []
        self._videos = videos or []
        self._song = song
        self._album = album
        self.search_calls: list[tuple[str, str, int]] = []

    def search(self, query: str, *, filter: str, limit: int) -> list[dict[str, Any]]:  # noqa: A002
        self.search_calls.append((query, filter, limit))
        return self._videos if filter == "videos" else self._songs

    def get_song(self, video_id: str) -> dict[str, Any]:
        assert self._song is not None
        return self._song

    def get_album(self, browse_id: str) -> dict[str, Any]:
        assert self._album is not None
        return self._album


def _provider(client: _FakeYTMusic) -> YTMusicProvider:
    return YTMusicProvider(client_factory=lambda _language: client)


# --- pure mappers ---------------------------------------------------------


def test_ytmusic_map_songs_sets_verified_true(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    candidates = map_results(songs)
    assert candidates
    assert all(isinstance(c, AudioCandidate) for c in candidates)
    assert all(c.provider is ProviderId.YTMUSIC for c in candidates)
    # CONTRACT: song results are treated as verified.
    assert all(c.verified for c in candidates)
    first = candidates[0]
    assert first.provider_id == songs[0]["videoId"]
    assert first.url == f"https://music.youtube.com/watch?v={songs[0]['videoId']}"
    assert first.name == songs[0]["title"]
    assert first.artists == tuple(a["name"] for a in songs[0]["artists"])
    assert first.album == songs[0]["album"]["name"]
    assert first.popularity is None


def test_ytmusic_map_videos_verified_false(load_fixture: Any) -> None:
    videos = load_fixture("ytmusic", "search_videos")
    candidates = map_results(videos)
    assert candidates
    # CONTRACT: video results are not verified.
    assert all(not c.verified for c in candidates)
    assert all(c.provider is ProviderId.YTMUSIC for c in candidates)
    # videos carry no album context
    assert all(c.album is None for c in candidates)


def test_ytmusic_duration_mmss_to_ms(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    candidates = map_results(songs)
    # CONTRACT: the "m:ss" duration string is parsed to milliseconds.
    first_seconds = songs[0]["duration_seconds"]
    assert candidates[0].duration_ms == first_seconds * 1000
    # "4:09" -> 249_000 ms specifically for the recorded first result.
    assert candidates[0].duration_ms == 249_000
    # a longer "10:33" entry in the fixture parses correctly too
    ten_plus = next(c for c, s in zip(candidates, songs, strict=True) if s["duration"] == "10:33")
    assert ten_plus.duration_ms == (10 * 60 + 33) * 1000


def test_ytmusic_map_skips_results_without_video_id() -> None:
    raw = [
        {"resultType": "song", "title": "No id", "artists": [{"name": "A"}], "duration": "3:00"},
        {
            "resultType": "song",
            "videoId": "abc",
            "title": "Ok",
            "artists": [{"name": "A"}],
            "duration": "3:00",
        },
    ]
    candidates = map_results(raw)
    assert [c.provider_id for c in candidates] == ["abc"]


def test_ytmusic_map_search_tracks_from_songs(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    tracks = map_search_tracks(songs)
    assert tracks
    assert all(isinstance(t, Track) for t in tracks)
    assert all(t.provider is ProviderId.YTMUSIC for t in tracks)
    assert tracks[0].name == songs[0]["title"]
    assert tracks[0].duration_ms == songs[0]["duration_seconds"] * 1000
    assert tracks[0].album is not None
    assert tracks[0].album.name == songs[0]["album"]["name"]


# --- fetch methods (fake client) ------------------------------------------


async def test_ytmusic_audio_candidates_monkeypatched(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    videos = load_fixture("ytmusic", "search_videos")
    client = _FakeYTMusic(songs=songs, videos=videos)
    candidates = await _provider(client).audio_candidates(_QUERY_TRACK, limit=10)
    assert candidates
    # query is "<main artist> - <name>"
    assert client.search_calls[0][0] == "Daft Punk - Get Lucky"
    assert client.search_calls[0][1] == "songs"
    # song candidates come first and are verified
    assert candidates[0].verified is True
    assert all(c.provider is ProviderId.YTMUSIC for c in candidates)


async def test_ytmusic_audio_candidates_respects_limit(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    videos = load_fixture("ytmusic", "search_videos")
    client = _FakeYTMusic(songs=songs, videos=videos)
    candidates = await _provider(client).audio_candidates(_QUERY_TRACK, limit=3)
    assert len(candidates) == 3


async def test_ytmusic_search_returns_tracks(load_fixture: Any) -> None:
    songs = load_fixture("ytmusic", "search_songs")
    client = _FakeYTMusic(songs=songs)
    tracks = await _provider(client).search("get lucky", limit=5)
    assert tracks
    assert all(t.provider is ProviderId.YTMUSIC for t in tracks)
    assert client.search_calls[0][1] == "songs"


async def test_ytmusic_resolve_track_from_get_song(load_fixture: Any) -> None:
    song = load_fixture("ytmusic", "get_song")
    client = _FakeYTMusic(song=song)
    ref = PlatformRef(ProviderId.YTMUSIC, EntityType.TRACK, "Rgrt_8mXrK8")
    resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.TRACK
    assert resolved.track is not None
    vd = song["videoDetails"]
    assert resolved.track.name == vd["title"]
    assert resolved.track.duration_ms == int(vd["lengthSeconds"]) * 1000
    assert resolved.track.provider is ProviderId.YTMUSIC
    assert resolved.track.provider_id == vd["videoId"]


async def test_ytmusic_resolve_album_from_get_album(load_fixture: Any) -> None:
    album = load_fixture("ytmusic", "get_album")
    client = _FakeYTMusic(album=album)
    ref = PlatformRef(ProviderId.YTMUSIC, EntityType.ALBUM, "OLAK5uy_x")
    resolved = await _provider(client).resolve(ref)
    assert resolved.entity_type is EntityType.ALBUM
    assert resolved.provider_id == "OLAK5uy_x"
    assert resolved.album is not None
    assert resolved.album.name == album["title"]
    assert resolved.album.track_count == album["trackCount"]
    assert len(resolved.tracks) == len(album["tracks"])
    assert resolved.tracks[0].album == resolved.album


# --- wiring / capabilities ------------------------------------------------


def test_ytmusic_advertises_capabilities() -> None:
    provider = build_ytmusic_provider(ProviderContext())
    assert provider.id is ProviderId.YTMUSIC
    assert isinstance(provider, ProvidesAudio)
    assert isinstance(provider, Resolves)
    assert isinstance(provider, Searches)


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_ytmusic_audio_candidates() -> None:
    provider = build_ytmusic_provider(ProviderContext())
    candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert candidates
    assert any(c.verified for c in candidates)
    assert all(c.provider is ProviderId.YTMUSIC for c in candidates)
    assert all(c.url.startswith("https://music.youtube.com/watch?v=") for c in candidates)
