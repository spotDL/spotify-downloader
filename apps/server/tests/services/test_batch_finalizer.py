"""Task 7 — ``BatchFinalizer``: archive update, m3u generation, ``.spotdl`` v2.

Offline: a file-backed ``download_sessionmaker`` + a tmp library dir. Delegated
Plan 4 utilities (``gen_m3u_files`` / ``archive_update`` / ``save_archive``) are
trusted; the tests assert the finalizer's *orchestration* — which files it writes,
what the archive/m3u/save-file contain, and idempotency.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from spotdl_core.model import MatchStatus, ProviderId
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import Artist, DownloadBatch, DownloadJob, Match, Track, track_artists
from spotdl_server.services.batch import BatchFinalizer
from spotdl_server.settings import Settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _seed_playlist_batch(maker: async_sessionmaker[AsyncSession], library: Any) -> Any:
    """A PLAYLIST batch with 2 completed jobs + 1 failed job (all with matches)."""
    async with maker() as session:
        batch = DownloadBatch(
            kind=BatchKind.PLAYLIST,
            name="My Mix",
            source="https://open.spotify.com/playlist/mix",
            output_format="mp3",
            output_template="{artists} - {title}.{output-ext}",
            generate_m3u=True,
            generate_save_file=True,
            update_archive=True,
            total_jobs=3,
        )
        session.add(batch)
        await session.flush()

        specs = [
            ("One", DownloadStatus.COMPLETED, "https://youtube.com/watch?v=1", False),
            ("Two", DownloadStatus.COMPLETED, "https://youtube.com/watch?v=2", False),
            ("Three", DownloadStatus.FAILED, "https://youtube.com/watch?v=3", True),
        ]
        job_ids = []
        for position, (name, status, target_url, failed) in enumerate(specs, start=1):
            track = Track(name=name, duration_ms=180_000, track_number=position)
            session.add(track)
            await session.flush()
            artist = Artist(name=f"Artist {name}", normalized_name=f"a-{uuid4().hex[:8]}")
            session.add(artist)
            await session.flush()
            await session.execute(
                track_artists.insert().values(track_id=track.id, artist_id=artist.id, position=0)
            )
            match = Match(
                track_id=track.id,
                target_provider=ProviderId.YOUTUBE,
                target_id=f"yt{position}",
                target_url=target_url,
                score=0.9,
                matcher_version="matcher-v5",
                status=MatchStatus.AUTO,
                candidate_name=name,
                candidate_artists=[f"Artist {name}"],
                candidate_duration_ms=181_000,
            )
            session.add(match)
            await session.flush()

            output_path = None
            if not failed:
                file = library / f"Artist {name} - {name}.mp3"
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b"audio")
                output_path = str(file)
            job = DownloadJob(
                batch_id=batch.id,
                track_id=track.id,
                match_id=match.id,
                status=status,
                list_position=position,
                output_format="mp3",
                bitrate="auto",
                output_template="{artists} - {title}.{output-ext}",
                output_path=output_path,
                skip_reason=None,
                error_step="convert" if failed else None,
            )
            session.add(job)
            await session.flush()
            job_ids.append(job.id)
        await session.commit()
        return batch.id


async def test_finalize_writes_archive_m3u_and_savefile(
    download_sessionmaker: Any, download_settings: Settings
) -> None:
    library = download_settings.effective_library_path()
    library.mkdir(parents=True, exist_ok=True)
    batch_id = await _seed_playlist_batch(download_sessionmaker, library)

    finalizer = BatchFinalizer(sessionmaker=download_sessionmaker, settings=download_settings)
    result = await finalizer.finalize(batch_id)

    # 1. archive: only the two completed track urls, sorted, no failed one.
    archive_path = library / ".spotdl-archive.txt"
    assert archive_path.is_file()
    urls = archive_path.read_text(encoding="utf-8").split()
    assert urls == ["https://youtube.com/watch?v=1", "https://youtube.com/watch?v=2"]

    # 2. m3u: at least one file written, with the EXTM3U header + both entries.
    assert result.m3u_paths
    m3u_text = result.m3u_paths[0].read_text(encoding="utf-8")
    assert m3u_text.startswith("#EXTM3U")
    assert m3u_text.count("#EXTINF") == 2  # only the two completed tracks

    # 3. save-file: v2 envelope, all three jobs present, failed one included.
    assert result.save_file_path is not None
    payload = json.loads(result.save_file_path.read_text(encoding="utf-8"))
    assert payload["version"] == 2
    assert payload["kind"] == "playlist"
    assert payload["name"] == "My Mix"
    assert len(payload["songs"]) == 3
    statuses = sorted(song["download"]["status"] for song in payload["songs"])
    assert statuses == ["completed", "completed", "failed"]
    for song in payload["songs"]:
        assert song["match"] is not None
        assert song["match"]["url"].startswith("https://youtube.com/watch?v=")


async def test_finalize_savefile_carries_match_and_metadata(
    download_sessionmaker: Any, download_settings: Settings
) -> None:
    library = download_settings.effective_library_path()
    library.mkdir(parents=True, exist_ok=True)
    batch_id = await _seed_playlist_batch(download_sessionmaker, library)

    finalizer = BatchFinalizer(sessionmaker=download_sessionmaker, settings=download_settings)
    result = await finalizer.finalize(batch_id)
    assert result.save_file_path is not None
    payload = json.loads(result.save_file_path.read_text(encoding="utf-8"))

    song = next(s for s in payload["songs"] if s["download"]["status"] == "completed")
    assert song["name"] in {"One", "Two"}
    assert song["match"]["provider"] == "youtube"
    assert song["match"]["matcher_version"] == "matcher-v5"
    assert song["match"]["duration_ms"] == 181_000
    assert song["download"]["output_format"] == "mp3"
    assert song["download"]["output_path"] is not None


async def test_finalize_is_idempotent_archive_not_double_appended(
    download_sessionmaker: Any, download_settings: Settings
) -> None:
    library = download_settings.effective_library_path()
    library.mkdir(parents=True, exist_ok=True)
    batch_id = await _seed_playlist_batch(download_sessionmaker, library)

    finalizer = BatchFinalizer(sessionmaker=download_sessionmaker, settings=download_settings)
    await finalizer.finalize(batch_id)
    await finalizer.finalize(batch_id)  # a second direct call must not double-append

    urls = (library / ".spotdl-archive.txt").read_text(encoding="utf-8").split()
    assert urls == ["https://youtube.com/watch?v=1", "https://youtube.com/watch?v=2"]


async def test_finalize_no_postprocessing_flags_writes_nothing(
    download_sessionmaker: Any, download_settings: Settings
) -> None:
    async with download_sessionmaker() as session:
        batch = DownloadBatch(kind=BatchKind.SINGLE, total_jobs=1)
        session.add(batch)
        await session.flush()
        job = DownloadJob(
            batch_id=batch.id, status=DownloadStatus.COMPLETED, list_position=1, output_format="mp3"
        )
        session.add(job)
        await session.flush()
        await session.commit()
        batch_id = batch.id

    finalizer = BatchFinalizer(sessionmaker=download_sessionmaker, settings=download_settings)
    result = await finalizer.finalize(batch_id)

    assert result.m3u_paths == []
    assert result.save_file_path is None
    assert not (download_settings.effective_library_path() / ".spotdl-archive.txt").exists()
