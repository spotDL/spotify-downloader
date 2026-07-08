"""Tests for the YouTube audio provider (yt-dlp, metadata only) (Task 9).

Every test is offline except the ``@pytest.mark.network`` live search. The pure
mapper runs from a checked-in ``yt-dlp`` ``extract_info(...)`` fixture, and the
fetch method is tested with a fake ``YoutubeDL`` injected in place of the real
library. No audio is downloaded here (that is Plan 4).

The mapping contract asserted here: yt-dlp reports ``duration`` in **seconds**;
the candidate stores it as milliseconds, ``popularity`` is the ``view_count``,
and candidates are never ``verified``.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

import pytest
from spotdl_core.model import AudioCandidate, ProviderId, Track
from spotdl_core.providers.audio.youtube import (
    YouTubeProvider,
    build_youtube_provider,
    map_results,
)
from spotdl_core.providers.base import ProvidesAudio
from spotdl_core.providers.registry import ProviderContext

_QUERY_TRACK = Track(
    name="Get Lucky",
    artists=("Daft Punk",),
    duration_ms=249_000,
    provider=ProviderId.SPOTIFY,
    provider_id="x",
)


class _FakeYoutubeDL:
    """Stand-in for ``yt_dlp.YoutubeDL`` (a context manager) returning a fixture."""

    def __init__(self, info: dict[str, Any]) -> None:
        self._info = info
        self.opts: dict[str, Any] | None = None
        self.extract_calls: list[tuple[str, bool]] = []

    def __call__(self, opts: dict[str, Any]) -> _FakeYoutubeDL:
        self.opts = opts
        return self

    def __enter__(self) -> _FakeYoutubeDL:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def extract_info(self, url: str, *, download: bool) -> dict[str, Any]:
        self.extract_calls.append((url, download))
        return self._info


def _provider(fake: _FakeYoutubeDL) -> YouTubeProvider:
    return YouTubeProvider(ytdl_factory=fake)


# --- pure mapper ----------------------------------------------------------


def test_youtube_map_from_ytdlp_fixture(load_fixture: Any) -> None:
    info = load_fixture("youtube", "ytdlp_search")
    entries = info["entries"]
    candidates = map_results(entries)
    assert candidates
    assert all(isinstance(c, AudioCandidate) for c in candidates)
    assert all(c.provider is ProviderId.YOUTUBE for c in candidates)
    # CONTRACT: yt-dlp metadata candidates are never treated as verified.
    assert all(not c.verified for c in candidates)
    first = candidates[0]
    assert first.provider_id == entries[0]["id"]
    assert first.name == entries[0]["title"]
    assert first.artists == (entries[0]["uploader"],)
    assert first.url == entries[0]["url"]
    # CONTRACT: popularity is the view_count.
    assert first.popularity == entries[0]["view_count"]


def test_youtube_duration_seconds_to_ms(load_fixture: Any) -> None:
    info = load_fixture("youtube", "ytdlp_search")
    entries = info["entries"]
    candidates = map_results(entries)
    # CONTRACT: yt-dlp duration is seconds; the candidate stores milliseconds.
    assert candidates[0].duration_ms == entries[0]["duration"] * 1000
    assert candidates[0].duration_ms == 249_000


def test_youtube_map_builds_watch_url_when_missing() -> None:
    entries = [{"id": "abc123", "title": "Song", "uploader": "Artist", "duration": 60}]
    candidates = map_results(entries)
    assert candidates[0].url == "https://www.youtube.com/watch?v=abc123"
    assert candidates[0].duration_ms == 60_000


def test_youtube_map_skips_entries_without_id() -> None:
    entries = [
        {"title": "no id", "duration": 10},
        {"id": "keep", "title": "keep", "uploader": "A", "duration": 10},
    ]
    assert [c.provider_id for c in map_results(entries)] == ["keep"]


def test_youtube_map_handles_missing_duration_and_uploader() -> None:
    entries = [{"id": "z", "title": "T", "view_count": 5}]
    candidate = map_results(entries)[0]
    assert candidate.duration_ms is None
    assert candidate.artists == ()
    assert candidate.popularity == 5


# --- fetch method (fake YoutubeDL) ----------------------------------------


async def test_youtube_audio_candidates_monkeypatched(load_fixture: Any) -> None:
    info = load_fixture("youtube", "ytdlp_search")
    fake = _FakeYoutubeDL(info)
    candidates = await _provider(fake).audio_candidates(_QUERY_TRACK, limit=5)
    assert candidates
    # search query is "ytsearch{N}:{artist} - {name}", download disabled
    assert fake.extract_calls[0] == ("ytsearch5:Daft Punk - Get Lucky", False)
    # extract_flat keeps the fetch cheap (metadata only)
    assert fake.opts is not None
    assert fake.opts.get("extract_flat")
    assert all(c.provider is ProviderId.YOUTUBE for c in candidates)


async def test_youtube_audio_candidates_respects_limit(load_fixture: Any) -> None:
    info = load_fixture("youtube", "ytdlp_search")
    fake = _FakeYoutubeDL(info)
    candidates = await _provider(fake).audio_candidates(_QUERY_TRACK, limit=2)
    assert len(candidates) == 2
    assert fake.extract_calls[0][0] == "ytsearch2:Daft Punk - Get Lucky"


# --- wiring / capabilities ------------------------------------------------


def test_youtube_advertises_capabilities() -> None:
    provider = build_youtube_provider(ProviderContext())
    assert provider.id is ProviderId.YOUTUBE
    assert isinstance(provider, ProvidesAudio)


# --- live (excluded from make check) --------------------------------------


@pytest.mark.network
async def test_live_youtube_audio_candidates() -> None:
    provider = build_youtube_provider(ProviderContext())
    candidates = await provider.audio_candidates(_QUERY_TRACK, limit=5)
    assert candidates
    assert all(c.provider is ProviderId.YOUTUBE for c in candidates)
    assert all(c.duration_ms and c.duration_ms > 0 for c in candidates)
    assert all(not c.verified for c in candidates)
