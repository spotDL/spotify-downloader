"""Task 11 — the offline end-to-end download acceptance test (spec §6.3).

The **real boot path**: a tmp-file SQLite DB migrated by
:func:`spotdl_server.bootstrap.upgrade_to_head` (so the Plan-5 amendment columns
``batch_id``/``list_position``/``skip_reason``/``attempts`` and the
``download_batches`` table are exercised by Alembic, not ``create_all``), a faked
provider registry (resolve persists a track + a viable match), the
``FakeDownloadEngine`` injected via ``create_app(download_engine=...)``, and both
the HTTP surface and ``WS /ws/progress`` driven through Starlette's ``TestClient``
on the same app. No network / ffmpeg / real engine.

Covers the whole flow (submit → WS lifecycle → file → save-file → finalizer
artifacts + batch_finished) plus crash-recovery and cancellation wired through the
HTTP/WS surface.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from spotdl_core.download import DownloadOutcome, ProgressPhase
from spotdl_core.model import AudioCandidate, EntityType, MatchStatus, ProviderId, Track
from spotdl_core.providers import ResolvedEntity
from spotdl_server.app import create_app
from spotdl_server.bootstrap import upgrade_to_head
from spotdl_server.db.engine import build_engine
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import Artist, DownloadBatch, DownloadJob, Match, track_artists
from spotdl_server.db.models import Track as TrackModel
from spotdl_server.settings import DeploymentMode, Settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.testclient import TestClient

from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import FakeAudioProvider, FakeResolver, build_fake_registry

TRACK_URL = "https://open.spotify.com/track/track123"


def _registry() -> Any:
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )
    return build_fake_registry(
        FakeResolver(
            id=ProviderId.SPOTIFY,
            track=Track(name="Song", artists=("Artist",), duration_ms=200_000, isrc="USABC1234567"),
        ),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        mode=DeploymentMode.EMBEDDED,
        data_dir=tmp_path,
        library_path=tmp_path / "music",
        download_temp_dir=tmp_path / "temp",
    )


def _drain_until(ws: Any, wanted: str, *, limit: int = 100) -> list[str]:
    seen: list[str] = []
    for _ in range(limit):
        msg = ws.receive_json()
        seen.append(msg["type"])
        if msg["type"] == wanted:
            return seen
    raise AssertionError(f"never saw {wanted!r} (seen={seen})")


def test_end_to_end_submit_ws_file_savefile(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    upgrade_to_head(settings)  # real Alembic boot path (exercises the amendment migration)
    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, registry=_registry(), download_engine=engine)

    with TestClient(app) as client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json()["type"] == "hello"

        resp = client.post(
            "/api/v1/downloads",
            json={"query": TRACK_URL, "generate_save_file": True, "generate_m3u": True},
        )
        assert resp.status_code == 201
        batch = resp.json()["batch"]
        assert batch["total_jobs"] == 1
        job_id = batch["jobs"][0]["id"]
        batch_id = batch["batch_id"]

        seen = _drain_until(ws, "batch_finished")
        for expected in ("job_queued", "job_started", "progress", "job_finished", "batch_finished"):
            assert expected in seen, f"missing {expected} in {seen}"
        assert seen.index("job_started") < seen.index("job_finished") < seen.index("batch_finished")

        # GET the job → completed; GET the file → the real bytes + attachment.
        job = client.get(f"/api/v1/downloads/{job_id}").json()
        assert job["status"] == "completed"

        file_resp = client.get(f"/api/v1/downloads/{job_id}/file")
        assert file_resp.status_code == 200
        assert file_resp.content  # the fake engine wrote real bytes into the library
        assert "attachment" in file_resp.headers["content-disposition"]

        # The .spotdl v2 save-file for the batch.
        save_file = client.get(f"/api/v1/downloads/batches/{batch_id}/save-file").json()
        assert save_file["version"] == 2
        assert save_file["kind"] == "single"
        assert len(save_file["songs"]) == 1

    # The finalizer wrote the .spotdl save-file into the library on disk. A single
    # track is not a playlist, so — matching v4 — no m3u is emitted for it (the
    # m3u path is exercised end-to-end by ``test_end_to_end_playlist_generates_m3u``
    # below, and at the finalizer level by ``test_batch_finalizer``).
    library = settings.effective_library_path()
    on_disk = list(library.rglob("*"))
    assert any(p.suffix == ".spotdl" for p in on_disk), on_disk
    assert not any(p.suffix == ".m3u8" for p in on_disk), on_disk


def _playlist_registry() -> Any:
    """A resolver returning a 2-track PLAYLIST entity + an audio provider.

    The playlist resolve persists both tracks but — like v4 — kicks no per-track
    matching, so :func:`_seed_playlist_matches` seeds a viable ``Match`` for each
    persisted track before the download submit reads them via ``_top_match``.
    """
    tracks = (
        Track(name="One", artists=("A1",), duration_ms=180_000, isrc="US0000000001"),
        Track(name="Two", artists=("A2",), duration_ms=190_000, isrc="US0000000002"),
    )
    entity = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="mix123",
        entity_type=EntityType.PLAYLIST,
        name="My Mix",
        tracks=tracks,
    )
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt",
        url="https://audio/yt",
        name="Song",
        artists=("A1",),
        duration_ms=180_000,
    )
    return build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, entity=entity),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )


async def _seed_playlist_matches(settings: Settings) -> None:
    """Seed one AUTO ``Match`` per already-persisted track (playlist resolve
    persists tracks but no matches — see :func:`_playlist_registry`)."""
    engine = build_engine(settings)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        tracks = (await session.execute(select(TrackModel))).scalars().all()
        for track in tracks:
            session.add(
                Match(
                    track_id=track.id,
                    target_provider=ProviderId.YOUTUBE,
                    target_id=f"yt-{track.name}",
                    target_url=f"https://youtube.com/watch?v={track.name}",
                    score=0.9,
                    matcher_version="v5",
                    status=MatchStatus.AUTO,
                )
            )
        await session.commit()
    await engine.dispose()


def test_end_to_end_playlist_generates_m3u(tmp_path: Path) -> None:
    """A playlist submit drives 2 jobs to completion and the finalizer emits an
    m3u (playlist-named) + a playlist ``.spotdl`` on disk, all over HTTP/WS."""
    settings = _settings(tmp_path)
    upgrade_to_head(settings)
    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, registry=_playlist_registry(), download_engine=engine)

    with TestClient(app) as client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json()["type"] == "hello"

        # Resolve first (persists the 2 playlist tracks), then seed their matches.
        resolve = client.post(
            "/api/v1/resolve", json={"query": "https://open.spotify.com/playlist/mix123"}
        )
        assert resolve.status_code == 200, resolve.text
        assert resolve.json()["entity"]["type"] == "playlist"
        asyncio.run(_seed_playlist_matches(settings))

        resp = client.post(
            "/api/v1/downloads",
            json={
                "query": "https://open.spotify.com/playlist/mix123",
                "generate_m3u": True,
                "generate_save_file": True,
            },
        )
        assert resp.status_code == 201, resp.text
        batch = resp.json()["batch"]
        assert batch["kind"] == "playlist"
        assert batch["total_jobs"] == 2
        batch_id = batch["batch_id"]

        seen = _drain_until(ws, "batch_finished")
        assert seen.count("job_finished") == 2, seen

        save_file = client.get(f"/api/v1/downloads/batches/{batch_id}/save-file").json()
        assert save_file["version"] == 2
        assert save_file["kind"] == "playlist"
        assert len(save_file["songs"]) == 2

    # The finalizer wrote a playlist-named m3u (both tracks) + a .spotdl on disk.
    library = settings.effective_library_path()
    on_disk = list(library.rglob("*"))
    m3u = next((p for p in on_disk if p.suffix == ".m3u8"), None)
    assert m3u is not None, on_disk
    m3u_text = m3u.read_text(encoding="utf-8")
    assert m3u_text.startswith("#EXTM3U")
    assert m3u_text.count("#EXTINF") == 2, m3u_text
    assert any(p.suffix == ".spotdl" for p in on_disk), on_disk


async def _seed_stale_running_job(settings: Settings) -> str:
    """Seed a batch + a RUNNING job (a crashed prior process) before the app boots."""
    engine = build_engine(settings)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        batch = DownloadBatch(kind=BatchKind.SINGLE, total_jobs=1)
        session.add(batch)
        await session.flush()
        track = TrackModel(name="Recovered", duration_ms=180_000)
        session.add(track)
        await session.flush()
        artist = Artist(name="A", normalized_name=f"a-{uuid4().hex[:8]}")
        session.add(artist)
        await session.flush()
        await session.execute(
            track_artists.insert().values(track_id=track.id, artist_id=artist.id, position=0)
        )
        match = Match(
            track_id=track.id,
            target_provider=ProviderId.YOUTUBE,
            target_id="yt",
            target_url="https://youtube.com/watch?v=x",
            score=0.9,
            matcher_version="v5",
            status=MatchStatus.AUTO,
        )
        session.add(match)
        await session.flush()
        job = DownloadJob(
            batch_id=batch.id,
            track_id=track.id,
            match_id=match.id,
            status=DownloadStatus.RUNNING,  # orphaned by a crash — no started_at reset yet
            list_position=1,
            output_format="mp3",
            bitrate="auto",
            output_template="{artists} - {title}.{output-ext}",
        )
        session.add(job)
        await session.flush()
        await session.commit()
        job_id = str(job.id)
    await engine.dispose()
    return job_id


def test_crash_recovery_completes_stale_running_job(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    upgrade_to_head(settings)
    job_id = asyncio.run(_seed_stale_running_job(settings))

    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, registry=_registry(), download_engine=engine)
    with TestClient(app) as client:
        # pool.start() recovered the orphaned RUNNING row (→ queued, attempts+1) and a
        # worker re-ran it to completion (forcing overwrite=FORCE for the re-run).
        final: dict = {}
        for _ in range(200):
            final = client.get(f"/api/v1/downloads/{job_id}").json()
            if final["status"] in ("completed", "failed", "cancelled"):
                break
        assert final["status"] == "completed"
        assert final["output_path"]


def test_cancellation_via_delete_emits_ws_cancelled(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    upgrade_to_head(settings)
    release = asyncio.Event()

    async def block(fake: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        fake.emit(on_progress, ProgressPhase.FETCH, 0)
        await release.wait()  # hold the job in-flight until the DELETE cancels the task
        return DownloadOutcome.downloaded(request.track, fake.write_output(request))

    engine = FakeDownloadEngine(config=settings.download_config(), script=block)
    app = create_app(settings, registry=_registry(), download_engine=engine)

    with TestClient(app) as client, client.websocket_connect("/ws/progress") as ws:
        assert ws.receive_json()["type"] == "hello"
        job = client.post("/api/v1/downloads", json={"query": TRACK_URL}).json()["batch"]["jobs"][0]

        _drain_until(ws, "job_started")  # ensure the worker claimed + started it
        resp = client.delete(f"/api/v1/downloads/{job['id']}")
        assert resp.status_code == 200

        _drain_until(ws, "job_cancelled")
        final = client.get(f"/api/v1/downloads/{job['id']}").json()
        assert final["status"] == "cancelled"
