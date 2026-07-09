"""Boot a seeded selfhost server for the Playwright e2e suite (Plan 10, Task 11).

Test-support only — this lives under ``apps/server/scripts`` (excluded from the
wheel) and imports the offline fake-registry seam from ``apps/server/tests``. It:

1. builds a real SELFHOST app (auth + downloads active) on a fresh migrated
   tmp-file SQLite DB, with every provider faked so nothing touches the network;
2. seeds — through the app's *real* code paths and repositories — two accounts
   (one admin), a canonical track with a community match, and one completed
   download batch/job (plus the audio file on disk); then
3. serves the bundled SPA (Task 12 embedded mount) + the API on a fixed port, so
   Playwright drives the true serving path, same-origin, fully offline.

Run: ``uv run python apps/server/scripts/serve_e2e.py`` (honours
``SPOTDL_E2E_PORT``, default 8811). The specs rely on the ``SEED_*`` constants.

The SPA must already be embedded (``make web-embed``) for ``/`` to serve it;
``make web-e2e`` builds + embeds before starting this server.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Run as a script → put the repo root on sys.path so the test-support fakes
# (apps.server.tests.*) import exactly as they do under pytest.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from spotdl_core.model import AudioCandidate, ProviderId, Track  # noqa: E402
from spotdl_server.app import create_app  # noqa: E402
from spotdl_server.bootstrap import upgrade_to_head  # noqa: E402
from spotdl_server.db.enums import BatchKind, DownloadStatus  # noqa: E402
from spotdl_server.db.models import DownloadBatch, DownloadJob  # noqa: E402
from spotdl_server.services.auth import normalize_email  # noqa: E402
from spotdl_server.settings import DeploymentMode, Settings  # noqa: E402

from apps.server.tests.conftest import FakeDownloadEngine  # noqa: E402
from apps.server.tests.fakes import (  # noqa: E402
    FakeAudioProvider,
    FakeLyricsProvider,
    FakeResolver,
    FakeSearcher,
    build_fake_registry,
)

# --- Seed constants the e2e specs depend on ----------------------------------
SEED_SECRET = "e2e-secret-key-0123456789-abcdefghijklmnop"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password-123"
USER_EMAIL = "listener@example.com"
USER_PASSWORD = "listener-password-123"
# FakeResolver returns TRACK for any ref, keyed by ISRC, so a re-resolve of this
# URL in the browser hits the same canonical track the match was seeded on.
SPOTIFY_TRACK_URL = "https://open.spotify.com/track/e2etrack01"
SUBMIT_MATCH_URL = "https://music.youtube.com/watch?v=e2eMatch01"  # a ytmusic audio target
TRACK_NAME = "E2E Anthem"
TRACK_ARTIST = "The Testers"

_TRACK = Track(
    name=TRACK_NAME,
    artists=(TRACK_ARTIST,),
    duration_ms=201_000,
    isrc="USE2E0000001",
)
# The search hit carries a provider ref so the search page renders a real result.
_SEARCH_HIT = Track(
    name=TRACK_NAME,
    artists=(TRACK_ARTIST,),
    duration_ms=201_000,
    isrc="USE2E0000001",
    provider=ProviderId.SPOTIFY,
    provider_id="e2etrack01",
)
_CANDIDATES = (
    AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="e2e-audio",
        url="https://audio/e2e",
        name=TRACK_NAME,
        artists=(TRACK_ARTIST,),
        duration_ms=201_000,
    ),
)


def _settings(data_dir: Path) -> Settings:
    return Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=data_dir,
        library_path=data_dir / "music",
        download_temp_dir=data_dir / "temp",
        auth_secret_key=SecretStr(SEED_SECRET),
    )


def _registry() -> object:
    return build_fake_registry(
        # Distinct provider ids: the registry keys specs by id, so a shared id
        # would clobber (e.g. a searcher overwriting the resolver). The search hit
        # still carries provider=spotify in its payload for snapshotting.
        FakeResolver(id=ProviderId.SPOTIFY, track=_TRACK),
        FakeSearcher(id=ProviderId.DEEZER, tracks=[_SEARCH_HIT]),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=list(_CANDIDATES)),
        FakeLyricsProvider(
            id=ProviderId.GENIUS,
            text="[00:00.00] first test line\n[00:03.00] second test line",
        ),
    )


async def _seed(app: object, settings: Settings) -> None:
    """Seed accounts, a track + match, and a completed download via real paths."""
    async with app.router.lifespan_context(app):  # type: ignore[attr-defined]
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://seed") as client:
            # Two accounts through the real register endpoint.
            listener = await client.post(
                "/api/v1/auth/register",
                json={"email": USER_EMAIL, "password": USER_PASSWORD},
            )
            listener.raise_for_status()
            listener_token = listener.json()["access_token"]

            admin = await client.post(
                "/api/v1/auth/register",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
            admin.raise_for_status()

            # Promote the admin (registration never grants is_admin). Fresh login
            # in the browser then mints a JWT carrying the is_admin claim.
            from spotdl_server.repositories.users import UserRepository

            async with app.state.sessionmaker() as session:  # type: ignore[attr-defined]
                admin_user = await UserRepository(session).get_by_email(
                    normalize_email(ADMIN_EMAIL)
                )
                assert admin_user is not None
                admin_user.is_admin = True
                await session.commit()

            # Resolve the track (creates the canonical entity) and submit a match
            # on it as the listener, so the track page has something to vote on.
            resolved = await client.post("/api/v1/resolve", json={"query": SPOTIFY_TRACK_URL})
            resolved.raise_for_status()
            track_id = resolved.json()["entity"]["track"]["id"]

            submitted = await client.post(
                f"/api/v1/tracks/{track_id}/matches",
                json={"url": SUBMIT_MATCH_URL},
                headers={"Authorization": f"Bearer {listener_token}"},
            )
            submitted.raise_for_status()

            # One completed download + its audio file, so the queue/library show a
            # finished job with a working file link. Terminal state → the worker
            # pool never touches it.
            library = settings.effective_library_path()
            library.mkdir(parents=True, exist_ok=True)
            audio = library / "The Testers - E2E Anthem.mp3"
            audio.write_bytes(b"e2e-audio-bytes")
            async with app.state.sessionmaker() as session:  # type: ignore[attr-defined]
                batch = DownloadBatch(kind=BatchKind.SINGLE, total_jobs=1)
                session.add(batch)
                await session.flush()
                job = DownloadJob(
                    batch_id=batch.id,
                    status=DownloadStatus.COMPLETED,
                    list_position=1,
                    output_format="mp3",
                    bitrate="auto",
                    output_template="{artists} - {title}.{output-ext}",
                    output_path=str(audio),
                    progress=1.0,
                )
                session.add(job)
                await session.commit()


def main() -> None:
    port = int(os.environ.get("SPOTDL_E2E_PORT", "8811"))
    host = os.environ.get("SPOTDL_E2E_HOST", "127.0.0.1")

    # A fresh tmp DB per boot: a clean seed every run (no "email already taken").
    data_dir = Path(tempfile.mkdtemp(prefix="spotdl-e2e-"))
    settings = _settings(data_dir)
    upgrade_to_head(settings)

    app = create_app(
        settings,
        registry=_registry(),
        download_engine=FakeDownloadEngine(config=settings.download_config()),
    )
    asyncio.run(_seed(app, settings))

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
