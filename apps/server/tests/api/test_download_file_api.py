"""Task 9 — ``GET /api/v1/downloads/{job_id}/file`` delivery semantics (CONTRACT 6).

Fully offline. Jobs are seeded directly through the app's session factory so each
scenario pins an exact ``status`` / ``output_path`` without running the pool:
a completed real download streams with a ``Content-Disposition`` attachment; a
not-yet-ready job is 409; a path outside the library root, or a missing file, is
404 (never leaked); and an ``X-Accel-Redirect`` prefix delegates streaming to a
reverse proxy (empty body + header, correct relative path).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from spotdl_server.app import create_app
from spotdl_server.db.base import Base
from spotdl_server.db.engine import build_engine
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import DownloadBatch, DownloadJob
from spotdl_server.settings import DeploymentMode, Settings

from apps.server.tests.conftest import FakeDownloadEngine
from apps.server.tests.fakes import build_fake_registry


@asynccontextmanager
async def _file_app(
    tmp_path: Path, *, x_accel: str | None = None
) -> AsyncIterator[tuple[httpx.AsyncClient, Settings, object]]:
    settings = Settings(
        mode=DeploymentMode.EMBEDDED,
        data_dir=tmp_path,
        library_path=tmp_path / "music",
        download_temp_dir=tmp_path / "temp",
        download_x_accel_prefix=x_accel,
    )
    pre = build_engine(settings)
    async with pre.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await pre.dispose()

    engine = FakeDownloadEngine(config=settings.download_config())
    app = create_app(settings, registry=build_fake_registry(), download_engine=engine)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, settings, app


async def _seed_job(
    app: object,
    *,
    status: DownloadStatus,
    output_path: str | None,
    skip_reason: str | None = None,
) -> str:
    """Insert a batch + a single job with an explicit terminal state + path."""
    async with app.state.sessionmaker() as session:  # type: ignore[attr-defined]
        batch = DownloadBatch(kind=BatchKind.SINGLE, total_jobs=1)
        session.add(batch)
        await session.flush()
        job = DownloadJob(
            batch_id=batch.id,
            status=status,
            list_position=1,
            output_format="mp3",
            bitrate="auto",
            output_template="{artists} - {title}.{output-ext}",
            output_path=output_path,
            skip_reason=skip_reason,
            progress=1.0 if status is DownloadStatus.COMPLETED else 0.0,
        )
        session.add(job)
        await session.flush()
        await session.commit()
        return str(job.id)


async def test_completed_job_streams_file_with_attachment(tmp_path: Path) -> None:
    async with _file_app(tmp_path) as (client, settings, app):
        library = settings.effective_library_path()
        library.mkdir(parents=True, exist_ok=True)
        audio = library / "Artist - Song.mp3"
        audio.write_bytes(b"real-audio-bytes")
        job_id = await _seed_job(app, status=DownloadStatus.COMPLETED, output_path=str(audio))

        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 200
    assert resp.content == b"real-audio-bytes"
    assert resp.headers["content-type"] == "audio/mpeg"
    assert "attachment" in resp.headers["content-disposition"]
    assert "Artist%20-%20Song.mp3" in resp.headers["content-disposition"]


async def test_not_ready_job_is_409(tmp_path: Path) -> None:
    async with _file_app(tmp_path) as (client, _settings, app):
        job_id = await _seed_job(app, status=DownloadStatus.QUEUED, output_path=None)
        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "download_failed"
    assert body["detail"] == {"reason": "not_ready"}


async def test_skipped_job_is_not_ready_409(tmp_path: Path) -> None:
    async with _file_app(tmp_path) as (client, settings, app):
        library = settings.effective_library_path()
        library.mkdir(parents=True, exist_ok=True)
        audio = library / "existing.mp3"
        audio.write_bytes(b"x")
        # A completed *skip* claims no freshly-produced file → treated as not-ready.
        job_id = await _seed_job(
            app,
            status=DownloadStatus.COMPLETED,
            output_path=str(audio),
            skip_reason="already_exists",
        )
        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 409
    assert resp.json()["detail"] == {"reason": "not_ready"}


async def test_path_traversal_outside_library_is_404(tmp_path: Path) -> None:
    async with _file_app(tmp_path) as (client, _settings, app):
        outside = tmp_path / "outside.mp3"
        outside.write_bytes(b"secret")
        job_id = await _seed_job(app, status=DownloadStatus.COMPLETED, output_path=str(outside))
        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_missing_file_is_404(tmp_path: Path) -> None:
    async with _file_app(tmp_path) as (client, settings, app):
        library = settings.effective_library_path()
        library.mkdir(parents=True, exist_ok=True)
        phantom = library / "gone.mp3"  # under the root but never written
        job_id = await _seed_job(app, status=DownloadStatus.COMPLETED, output_path=str(phantom))
        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"


async def test_x_accel_redirect_delivers_empty_body_with_header(tmp_path: Path) -> None:
    async with _file_app(tmp_path, x_accel="/internal-music/") as (client, settings, app):
        library = settings.effective_library_path()
        subdir = library / "Album"
        subdir.mkdir(parents=True, exist_ok=True)
        audio = subdir / "Song.flac"
        audio.write_bytes(b"flac-bytes")
        job_id = await _seed_job(app, status=DownloadStatus.COMPLETED, output_path=str(audio))

        resp = await client.get(f"/api/v1/downloads/{job_id}/file")

    assert resp.status_code == 200
    assert resp.content == b""  # streaming delegated to the proxy; Python reads nothing
    assert resp.headers["x-accel-redirect"] == "/internal-music/Album/Song.flac"
    assert resp.headers["content-type"] == "audio/flac"
    assert "attachment" in resp.headers["content-disposition"]
