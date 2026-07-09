"""Auth wiring must NOT gate the Plan 5 anonymous read surface (spec §2/§6.4).

Adding the auth dependency + ``/auth`` router (Plan 6) is regression-prone: a
misplaced ``require_user`` could suddenly 401 the public read endpoints. The app
here is built in SELFHOST mode, so ``auth_active()`` is true and the ``/auth``
router IS mounted — yet every Plan 5 read must still answer with no
``Authorization`` header, returning its original Plan-5 status (never 401/403).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from spotdl_core.model import AudioCandidate, LyricsKind, ProviderId, Track

from apps.server.tests.api.support import api_client
from apps.server.tests.fakes import (
    FakeAudioProvider,
    FakeLyricsProvider,
    FakeResolver,
    FakeSearcher,
    build_fake_registry,
)

_SPOTIFY_URL = "https://open.spotify.com/track/track123"


def _track() -> Track:
    return Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567")


def _candidate() -> AudioCandidate:
    return AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )


def _registry() -> object:
    # Distinct provider ids: the registry keys specs by id, so two fakes must not
    # share one (the resolver is spotify because the read URL is a spotify track).
    return build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track()),
        FakeSearcher(id=ProviderId.DEEZER, tracks=[_track()]),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[_candidate()]),
        FakeLyricsProvider(id=ProviderId.GENIUS, text="la la la", kind=LyricsKind.PLAIN),
    )


async def test_plan5_reads_stay_anonymous_with_auth_mounted(tmp_path: Path) -> None:
    async with api_client(_registry(), data_dir=tmp_path) as client:
        # Sanity: the auth router really is mounted in this mode (proving the read
        # surface below coexists with, and is not gated by, the auth wiring).
        schema = (await client.get("/openapi.json")).json()
        assert "/api/v1/auth/register" in schema["paths"]

        # A canonical track to read back through the typed GETs.
        resolved = await client.post("/api/v1/resolve", json={"query": _SPOTIFY_URL})
        assert resolved.status_code == 200
        track_id = resolved.json()["entity"]["track"]["id"]

        cases = [
            ("GET", "/api/v1/health", None, 200),
            ("GET", "/api/v1/config", None, 200),
            ("GET", "/api/v1/search", {"q": "song"}, 200),
            ("GET", f"/api/v1/tracks/{track_id}", None, 200),
            ("GET", f"/api/v1/tracks/{track_id}/matches", None, 200),
            ("GET", f"/api/v1/tracks/{track_id}/lyrics", None, 200),
        ]
        for method, path, params, expected in cases:
            resp = await client.request(method, path, params=params)
            assert resp.status_code == expected, f"{path} -> {resp.status_code}: {resp.text}"
            assert resp.status_code not in (401, 403), f"{path} was gated by auth"

        # POST /resolve is a read-shaped write of a snapshot; still fully anonymous.
        again = await client.post("/api/v1/resolve", json={"query": _SPOTIFY_URL})
        assert again.status_code == 200

        # A well-formed but absent id returns the Plan-5 404, not an auth error.
        missing = await client.get(f"/api/v1/tracks/{uuid.uuid4()}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"
