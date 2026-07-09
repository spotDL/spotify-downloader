"""Task 4 — ``DownloadQueueService`` submit / expand / list / get.

Offline: an in-memory SQLite ``session`` plus a fake ``ResolveService`` whose
canned :class:`ResolveResult` echoes ids of rows seeded directly into the DB, so
``submit`` reads real ``matches`` rows via ``MatchRepository`` without any
provider/network I/O.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from spotdl_core.model import MatchStatus, ProviderId
from spotdl_core.providers import NoMatchFound
from spotdl_server.api.schemas import DownloadSubmitRequest
from spotdl_server.db.enums import BatchKind, DownloadStatus
from spotdl_server.db.models import Artist, Match, Track, track_artists
from spotdl_server.repositories.batches import DownloadBatchRepository
from spotdl_server.repositories.downloads import DownloadJobRepository
from spotdl_server.repositories.entities import TrackRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.services.downloads import DownloadQueueService
from spotdl_server.services.dto import AlbumView, PlaylistView, ResolveResult, TrackView
from spotdl_server.services.entities import EntityService
from spotdl_server.services.errors import NotFoundError, UnsupportedBatchEntity
from sqlalchemy.ext.asyncio import AsyncSession


class FakeResolveService:
    """A stand-in ``ResolveService`` returning a pre-built :class:`ResolveResult`."""

    def __init__(self, result: ResolveResult) -> None:
        self._result = result
        self.queries: list[str] = []

    async def resolve(self, query: str) -> ResolveResult:
        self.queries.append(query)
        return self._result


async def _seed_track(
    session: AsyncSession,
    *,
    name: str = "Song",
    artists: tuple[str, ...] | None = None,
    match: bool = True,
) -> tuple[Track, Match | None]:
    # Default to a per-track-unique artist so the ``artists.normalized_name``
    # unique constraint never collides across tracks seeded in one test.
    if artists is None:
        artists = (f"Artist {name}",)
    track = Track(name=name, duration_ms=180_000)
    session.add(track)
    await session.flush()
    for pos, artist_name in enumerate(artists):
        artist = Artist(name=artist_name, normalized_name=artist_name.lower())
        session.add(artist)
        await session.flush()
        await session.execute(
            track_artists.insert().values(track_id=track.id, artist_id=artist.id, position=pos)
        )
    row: Match | None = None
    if match:
        row = Match(
            track_id=track.id,
            target_provider=ProviderId.YOUTUBE,
            target_id=f"yt-{name}",
            target_url=f"https://youtube.com/watch?v={name}",
            score=0.91,
            matcher_version="v5",
            status=MatchStatus.AUTO,
        )
        session.add(row)
        await session.flush()
    await session.refresh(track)
    return track, row


def _track_view(track: Track) -> TrackView:
    return TrackView(
        id=str(track.id),
        name=track.name,
        artists=tuple(a.name for a in track.artists),
        duration_ms=track.duration_ms,
    )


def _service(
    session: AsyncSession, result: ResolveResult, settings: object, clock: object
) -> DownloadQueueService:
    return DownloadQueueService(
        session=session,
        resolve_service=FakeResolveService(result),  # type: ignore[arg-type]
        entity_service=EntityService(session=session),
        match_repo=MatchRepository(session),
        track_repo=TrackRepository(session),
        job_repo=DownloadJobRepository(session),
        batch_repo=DownloadBatchRepository(session),
        settings=settings,  # type: ignore[arg-type]
        requested_by=None,
        clock=clock,  # type: ignore[arg-type]
    )


async def test_submit_track_single_batch_defaults(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    track, _ = await _seed_track(session, artists=("A",))
    result = ResolveResult(entity_type="track", track=_track_view(track))
    svc = _service(session, result, download_settings, clock)

    batch, job_ids = await svc.submit(DownloadSubmitRequest(query="https://x/track"))

    assert batch.kind is BatchKind.SINGLE
    assert batch.name is None
    assert batch.total_jobs == 1
    assert len(job_ids) == 1
    (job,) = batch.jobs
    assert job.status is DownloadStatus.QUEUED
    assert job.output_format == "mp3"  # settings.default_output_format
    assert job.bitrate == "auto"
    assert job.output_template == "{artists} - {title}.{output-ext}"
    assert job.list_position == 1
    assert job.track_name == "Song"
    assert job.artists == ["A"]


async def test_submit_track_persists_chosen_match(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    track, match = await _seed_track(session)
    result = ResolveResult(entity_type="track", track=_track_view(track))
    svc = _service(session, result, download_settings, clock)

    _, job_ids = await svc.submit(DownloadSubmitRequest(query="q"))

    row = await DownloadJobRepository(session).get(job_ids[0])
    assert row is not None
    assert row.match_id == match.id  # type: ignore[union-attr]


async def test_submit_track_no_match_raises(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    track, _ = await _seed_track(session, match=False)
    result = ResolveResult(entity_type="track", track=_track_view(track))
    svc = _service(session, result, download_settings, clock)

    with pytest.raises(NoMatchFound):
        await svc.submit(DownloadSubmitRequest(query="q"))


async def test_submit_album_orders_jobs_and_keeps_no_match(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    t1, m1 = await _seed_track(session, name="One")
    t2, _ = await _seed_track(session, name="Two", match=False)  # no viable match
    t3, m3 = await _seed_track(session, name="Three")
    album = AlbumView(
        id=str(uuid4()),
        name="Greatest Hits",
        tracks=(_track_view(t1), _track_view(t2), _track_view(t3)),
    )
    result = ResolveResult(entity_type="album", album=album)
    svc = _service(session, result, download_settings, clock)

    batch, job_ids = await svc.submit(DownloadSubmitRequest(query="album-url"))

    assert batch.kind is BatchKind.ALBUM
    assert batch.name == "Greatest Hits"
    assert batch.total_jobs == 3
    positions = [j.list_position for j in batch.jobs]
    assert positions == [1, 2, 3]

    repo = DownloadJobRepository(session)
    rows = [await repo.get(jid) for jid in job_ids]
    assert rows[0].match_id == m1.id  # type: ignore[union-attr]
    assert rows[1].match_id is None  # no-match track is NOT dropped
    assert rows[2].match_id == m3.id  # type: ignore[union-attr]
    assert rows[1].track_id == t2.id  # type: ignore[union-attr]


async def test_submit_playlist_kind_and_name(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    t1, _ = await _seed_track(session, name="P1")
    t2, _ = await _seed_track(session, name="P2")
    playlist = PlaylistView(
        id=str(uuid4()), name="My Mix", tracks=(_track_view(t1), _track_view(t2))
    )
    result = ResolveResult(entity_type="playlist", playlist=playlist)
    svc = _service(session, result, download_settings, clock)

    batch, _ = await svc.submit(DownloadSubmitRequest(query="playlist-url"))

    assert batch.kind is BatchKind.PLAYLIST
    assert batch.name == "My Mix"
    assert batch.total_jobs == 2


async def test_submit_artist_unsupported(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    from spotdl_server.services.dto import ArtistView

    result = ResolveResult(entity_type="artist", artist=ArtistView(id=str(uuid4()), name="Band"))
    svc = _service(session, result, download_settings, clock)

    with pytest.raises(UnsupportedBatchEntity) as excinfo:
        await svc.submit(DownloadSubmitRequest(query="artist-url"))
    assert excinfo.value.entity_type_value == "artist"


async def test_submit_overrides_flow_to_batch_and_jobs(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    track, _ = await _seed_track(session)
    result = ResolveResult(entity_type="track", track=_track_view(track))
    svc = _service(session, result, download_settings, clock)

    from spotdl_core.download import OutputFormat, OverwriteMode

    batch, _ = await svc.submit(
        DownloadSubmitRequest(
            query="q",
            output_format=OutputFormat.FLAC,
            bitrate="320k",
            output_template="{title}.{output-ext}",
            generate_m3u=True,
            m3u_template="{list}.m3u8",
            generate_save_file=True,
            update_archive=True,
            sponsor_block=True,
            overwrite=OverwriteMode.FORCE,
        )
    )
    (job,) = batch.jobs
    assert job.output_format == "flac"
    assert job.bitrate == "320k"
    assert job.output_template == "{title}.{output-ext}"

    stored = await DownloadBatchRepository(session).get(batch.batch_id)
    assert stored is not None
    assert stored.generate_m3u is True
    assert stored.m3u_template == "{list}.m3u8"
    assert stored.generate_save_file is True
    assert stored.update_archive is True
    assert stored.sponsor_block is True
    assert stored.output_format == "flac"
    assert stored.overwrite == "force"


async def test_list_jobs_filters_and_paginates(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    t1, _ = await _seed_track(session, name="A1")
    t2, _ = await _seed_track(session, name="A2")
    album = AlbumView(id=str(uuid4()), name="Album", tracks=(_track_view(t1), _track_view(t2)))
    svc = _service(
        session, ResolveResult(entity_type="album", album=album), download_settings, clock
    )
    batch, _ = await svc.submit(DownloadSubmitRequest(query="album"))

    page = await svc.list_jobs(limit=1, offset=0)
    assert page.total == 2
    assert len(page.jobs) == 1
    assert page.limit == 1

    by_batch = await svc.list_jobs(batch_id=batch.batch_id)
    assert by_batch.total == 2

    queued = await svc.list_jobs(status=DownloadStatus.QUEUED)
    assert queued.total == 2
    completed = await svc.list_jobs(status=DownloadStatus.COMPLETED)
    assert completed.total == 0


async def test_get_job_and_batch_not_found(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    result = ResolveResult(entity_type="track")
    svc = _service(session, result, download_settings, clock)
    with pytest.raises(NotFoundError):
        await svc.get_job(uuid4())
    with pytest.raises(NotFoundError):
        await svc.get_batch(uuid4())


async def test_get_job_and_get_batch_round_trip(
    session: AsyncSession, download_settings: object, clock: object
) -> None:
    track, _ = await _seed_track(session)
    result = ResolveResult(entity_type="track", track=_track_view(track))
    svc = _service(session, result, download_settings, clock)
    batch, job_ids = await svc.submit(DownloadSubmitRequest(query="q"))

    job_out = await svc.get_job(job_ids[0])
    assert job_out.id == job_ids[0]
    assert job_out.track_name == "Song"

    batch_out = await svc.get_batch(batch.batch_id)
    assert batch_out.batch_id == batch.batch_id
    assert batch_out.finalized is False
    assert batch_out.counts["queued"] == 1
