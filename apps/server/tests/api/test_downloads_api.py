"""Task 9 — the ``/api/v1/downloads`` HTTP surface (submit / list / cancel / save-file).

Fully offline: the app is built through ``api_client`` (which injects the
``FakeDownloadEngine`` seam and pre-creates the schema), and the provider registry
is faked so a resolve persists a real track + match without any network. The pool
runs on the same event loop as the test, so a submitted job actually executes and
settles while the test polls.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
from spotdl_core.download import DownloadOutcome, ProgressPhase
from spotdl_core.model import AlbumRef, AudioCandidate, EntityType, ProviderId, Track
from spotdl_core.providers import ResolvedEntity
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.api.support import api_client
from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import FakeAudioProvider, FakeResolver, build_fake_registry

TRACK_URL = "https://open.spotify.com/track/track123"
ALBUM_URL = "https://open.spotify.com/album/album123"


def _track(name: str = "Song", artist: str = "Artist", isrc: str = "USABC1234567") -> Track:
    return Track(name=name, artists=(artist,), duration_ms=200_000, isrc=isrc)


def _track_registry() -> Any:
    """A resolver + audio provider so a track resolve persists a viable match."""
    candidate = AudioCandidate(
        provider=ProviderId.YOUTUBE,
        provider_id="yt1",
        url="https://audio/yt1",
        name="Song",
        artists=("Artist",),
        duration_ms=200_000,
    )
    return build_fake_registry(
        FakeResolver(id=ProviderId.SPOTIFY, track=_track()),
        FakeAudioProvider(id=ProviderId.YOUTUBE, candidates=[candidate]),
    )


def _album_registry() -> Any:
    """A resolver returning a 3-track album entity (album tracks are not matched)."""
    album = ResolvedEntity(
        provider=ProviderId.SPOTIFY,
        provider_id="album123",
        entity_type=EntityType.ALBUM,
        album=AlbumRef(name="Greatest Hits"),
        tracks=(
            _track("One", "A", isrc="USAAA0000001"),
            _track("Two", "B", isrc="USBBB0000002"),
            _track("Three", "C", isrc="USCCC0000003"),
        ),
    )
    return build_fake_registry(FakeResolver(id=ProviderId.SPOTIFY, entity=album))


async def _poll_job(client: httpx.AsyncClient, job_id: str, *, timeout: float = 5.0) -> dict:
    """Poll ``GET /downloads/{id}`` until it reaches a terminal state."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    terminal = {"completed", "failed", "cancelled"}
    while loop.time() < deadline:
        body = (await client.get(f"/api/v1/downloads/{job_id}")).json()
        if body["status"] in terminal:
            return body
        await asyncio.sleep(0.02)
    raise AssertionError(f"job {job_id} never settled (last={body})")


async def _wait_all_settled(client: httpx.AsyncClient, *, timeout: float = 5.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        queued = (await client.get("/api/v1/downloads?status=queued")).json()["total"]
        running = (await client.get("/api/v1/downloads?status=running")).json()["total"]
        if queued == 0 and running == 0:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("jobs never settled")


async def test_submit_track_runs_to_completion(tmp_path: Path) -> None:
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        resp = await client.post("/api/v1/downloads", json={"query": TRACK_URL})
        assert resp.status_code == 201
        batch = resp.json()["batch"]
        assert batch["kind"] == "single"
        assert batch["total_jobs"] == 1
        (job,) = batch["jobs"]
        assert job["status"] == "queued"

        final = await _poll_job(client, job["id"])
        assert final["status"] == "completed"
        assert final["output_path"]
        assert final["progress"] == 1.0
        assert Path(final["output_path"]).is_file()


async def test_submit_album_orders_jobs_by_list_position(tmp_path: Path) -> None:
    async with api_client(
        _album_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        resp = await client.post("/api/v1/downloads", json={"query": ALBUM_URL})
        assert resp.status_code == 201
        batch = resp.json()["batch"]
        assert batch["kind"] == "album"
        assert batch["name"] == "Greatest Hits"
        assert batch["total_jobs"] == 3
        assert [job["list_position"] for job in batch["jobs"]] == [1, 2, 3]


async def test_list_filters_and_paginates(tmp_path: Path) -> None:
    async with api_client(
        _album_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        batch = (await client.post("/api/v1/downloads", json={"query": ALBUM_URL})).json()["batch"]
        batch_id = batch["batch_id"]
        await _wait_all_settled(client)

        page = (await client.get("/api/v1/downloads?limit=2&offset=0")).json()
        assert page["total"] == 3
        assert len(page["jobs"]) == 2
        assert page["limit"] == 2

        by_batch = (await client.get(f"/api/v1/downloads?batch_id={batch_id}")).json()
        assert by_batch["total"] == 3

        # Album tracks carry no match row → every job fails fast at the fetch step.
        failed = (await client.get("/api/v1/downloads?status=failed")).json()
        assert failed["total"] == 3
        assert all(job["error_step"] == "fetch" for job in failed["jobs"])


async def test_get_batch_and_unknown_ids_404(tmp_path: Path) -> None:
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        batch = (await client.post("/api/v1/downloads", json={"query": TRACK_URL})).json()["batch"]
        batch_id = batch["batch_id"]

        got = (await client.get(f"/api/v1/downloads/batches/{batch_id}")).json()
        assert got["batch_id"] == batch_id
        assert got["total_jobs"] == 1

        missing = "00000000-0000-0000-0000-000000000000"
        assert (await client.get(f"/api/v1/downloads/{missing}")).status_code == 404
        assert (await client.get(f"/api/v1/downloads/batches/{missing}")).status_code == 404


async def test_cancel_terminal_job_is_409(tmp_path: Path) -> None:
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        job = (await client.post("/api/v1/downloads", json={"query": TRACK_URL})).json()["batch"][
            "jobs"
        ][0]
        final = await _poll_job(client, job["id"])
        assert final["status"] == "completed"

        resp = await client.delete(f"/api/v1/downloads/{job['id']}")
        assert resp.status_code == 409
        body = resp.json()
        assert body["code"] == "download_failed"
        assert body["detail"] == {"reason": "already_terminal"}


async def test_cancel_in_flight_job_transitions_to_cancelled(tmp_path: Path) -> None:
    settings = Settings(mode=DeploymentMode.SELFHOST, data_dir=tmp_path)
    release = asyncio.Event()

    async def block(engine: FakeDownloadEngine, request: Any, on_progress: Any) -> DownloadOutcome:
        engine.emit(on_progress, ProgressPhase.FETCH, 0)
        await release.wait()  # hold the job open so DELETE lands mid-run
        return DownloadOutcome.downloaded(request.track, engine.write_output(request))

    engine = FakeDownloadEngine(config=settings.download_config(), script=block)
    try:
        async with api_client(
            _track_registry(),
            data_dir=tmp_path,
            mode=DeploymentMode.EMBEDDED,
            download_engine=engine,
        ) as client:
            job = (await client.post("/api/v1/downloads", json={"query": TRACK_URL})).json()[
                "batch"
            ]["jobs"][0]

            resp = await client.delete(f"/api/v1/downloads/{job['id']}")
            assert resp.status_code == 200
            # Generous deadline: in-flight cancellation must unwind the engine task,
            # run _on_cancelled's fresh-session commit, and broadcast — under a
            # loaded machine (parallel suites) 5s has proven flaky.
            final = await _poll_job(client, job["id"], timeout=20.0)
            assert final["status"] == "cancelled"
    finally:
        release.set()


async def test_save_file_endpoint_returns_v2_attachment(tmp_path: Path) -> None:
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        batch = (
            await client.post(
                "/api/v1/downloads", json={"query": TRACK_URL, "generate_save_file": True}
            )
        ).json()["batch"]
        await _poll_job(client, batch["jobs"][0]["id"])

        resp = await client.get(f"/api/v1/downloads/batches/{batch['batch_id']}/save-file")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        assert "attachment" in resp.headers["content-disposition"]
        body = resp.json()
        assert body["version"] == 2
        assert body["kind"] == "single"
        assert len(body["songs"]) == 1
        assert body["songs"][0]["download"]["status"] == "completed"


async def test_hosted_has_no_downloads_endpoint(tmp_path: Path) -> None:
    from pydantic import SecretStr

    registry = build_fake_registry()
    settings = Settings(
        mode=DeploymentMode.HOSTED, data_dir=tmp_path, auth_secret_key=SecretStr("x")
    )
    # Hosted mounts nothing — a direct POST 404s (route absent, not merely gated).
    from spotdl_server.app import create_app
    from spotdl_server.db.base import Base
    from spotdl_server.db.engine import build_engine

    eng = build_engine(settings)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()
    app = create_app(settings, registry=registry)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/downloads", json={"query": TRACK_URL})
    assert resp.status_code == 404


async def test_submit_accepts_canonical_uuid_query(tmp_path: Path) -> None:
    """The web UI's enqueue-all posts the canonical entity id (not a URL)."""
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        first = (await client.post("/api/v1/downloads", json={"query": TRACK_URL})).json()
        track_id = first["batch"]["jobs"][0]["track_id"]
        await _wait_all_settled(client)

        again = await client.post("/api/v1/downloads", json={"query": track_id})
        assert again.status_code == 201
        body = again.json()
        assert body["batch"]["kind"] == "single"
        assert body["batch"]["jobs"][0]["track_id"] == track_id


async def test_submit_unknown_uuid_is_not_found(tmp_path: Path) -> None:
    async with api_client(
        _track_registry(), data_dir=tmp_path, mode=DeploymentMode.EMBEDDED
    ) as client:
        resp = await client.post(
            "/api/v1/downloads", json={"query": "00000000-0000-0000-0000-000000000042"}
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "not_found"
