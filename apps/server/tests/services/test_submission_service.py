"""Offline unit tests for :class:`SubmissionService` (spec §6.2 match submit).

A community submission adds a user-provided audio target for a track: it must be
a **playable** (audio-provider) **track** URL, it upserts by the Plan 5 unique
``(track_id, target_provider, target_id)`` key with ``matcher_version="community"``
and ``submitted_by`` set (so the row is distinguishable from an algorithmic
match, which has ``submitted_by IS NULL``), and it is idempotent — a duplicate
submit returns the existing row without clobbering an algorithmic match's
provenance. These tests pin every branch offline (no provider fetch).
"""

from __future__ import annotations

import uuid

import pytest
from spotdl_core.model import MatchStatus, ProviderId
from spotdl_core.providers import UnsupportedURL
from spotdl_server.db.models import Match as MatchModel
from spotdl_server.repositories.entities import TrackRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.services.errors import NotAnAudioTarget, NotFoundError
from spotdl_server.services.submissions import COMMUNITY_MATCHER_VERSION, SubmissionService
from sqlalchemy.ext.asyncio import AsyncSession

_YT_URL = "https://music.youtube.com/watch?v=dQw4w9WgXcQ"


def _service(session: AsyncSession) -> SubmissionService:
    return SubmissionService(
        session=session,
        tracks=TrackRepository(session),
        matches=MatchRepository(session),
    )


async def _make_track(session: AsyncSession) -> uuid.UUID:
    track = await TrackRepository(session).create(name="Test Track", duration_ms=211000)
    return track.id


async def test_submit_valid_youtube_url_creates_community_match(session: AsyncSession) -> None:
    track_id = await _make_track(session)
    user_id = uuid.uuid4()

    match = await _service(session).submit_match(
        track_id=track_id, url=_YT_URL, submitted_by=user_id
    )

    assert match.track_id == track_id
    assert match.target_provider is ProviderId.YTMUSIC
    assert match.target_id == "dQw4w9WgXcQ"
    assert match.status is MatchStatus.AUTO
    assert match.submitted_by == user_id
    assert match.matcher_version == COMMUNITY_MATCHER_VERSION == "community"
    assert match.score == 0.0
    # No synchronous provider fetch in v1 — denormalized candidate fields stay NULL.
    assert match.candidate_name is None
    assert match.candidate_artists is None
    assert match.candidate_duration_ms is None


async def test_unknown_track_raises_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await _service(session).submit_match(
            track_id=uuid.uuid4(), url=_YT_URL, submitted_by=uuid.uuid4()
        )


async def test_spotify_url_is_not_an_audio_target(session: AsyncSession) -> None:
    track_id = await _make_track(session)
    with pytest.raises(NotAnAudioTarget):
        await _service(session).submit_match(
            track_id=track_id,
            url="https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            submitted_by=uuid.uuid4(),
        )


async def test_garbage_url_raises_unsupported_url(session: AsyncSession) -> None:
    track_id = await _make_track(session)
    with pytest.raises(UnsupportedURL):
        await _service(session).submit_match(
            track_id=track_id, url="not a url at all", submitted_by=uuid.uuid4()
        )


async def test_duplicate_submit_is_idempotent(session: AsyncSession) -> None:
    track_id = await _make_track(session)
    user_id = uuid.uuid4()
    svc = _service(session)

    first = await svc.submit_match(track_id=track_id, url=_YT_URL, submitted_by=user_id)
    second = await svc.submit_match(track_id=track_id, url=_YT_URL, submitted_by=uuid.uuid4())

    assert first.id == second.id
    # Provenance of the first submitter is preserved on a repeat submit.
    assert second.submitted_by == user_id

    rows = await MatchRepository(session).list_for_track(track_id)
    assert len([r for r in rows if r.target_id == "dQw4w9WgXcQ"]) == 1


async def test_submitting_an_existing_algorithmic_match_does_not_clobber_provenance(
    session: AsyncSession,
) -> None:
    track_id = await _make_track(session)
    matches = MatchRepository(session)
    # An algorithmic match already exists for this exact target (submitted_by IS NULL).
    existing = await matches.create_submission(
        track_id=track_id,
        target_provider=ProviderId.YTMUSIC,
        target_id="dQw4w9WgXcQ",
        target_url=_YT_URL,
        matcher_version="v5.0",
        submitted_by=None,
    )
    existing.score = 87.5
    await session.flush()

    returned = await _service(session).submit_match(
        track_id=track_id, url=_YT_URL, submitted_by=uuid.uuid4()
    )

    assert returned.id == existing.id
    # The algorithmic provenance and score are left as-is.
    assert returned.submitted_by is None
    assert returned.matcher_version == "v5.0"
    assert returned.score == 87.5


class _RacingMatchRepository(MatchRepository):
    """A repo that simulates a concurrent submitter winning the unique-target race.

    On the *first* ``get_by_target`` (the service's check-then-act read) it returns
    ``None`` — as if our SELECT ran before the rival's commit — but actually inserts
    the conflicting row so the service's subsequent ``create_submission`` flush trips
    the ``(track_id, target_provider, target_id)`` IntegrityError. Later reads
    (the post-IntegrityError retry) behave normally and see the rival's row.
    """

    def __init__(self, session: AsyncSession, rival_submitter: uuid.UUID) -> None:
        super().__init__(session)
        self._rival_submitter = rival_submitter
        self._raced = False
        self.rival_id: uuid.UUID | None = None

    async def get_by_target(
        self, track_id: uuid.UUID, target_provider: ProviderId, target_id: str
    ) -> MatchModel | None:
        if not self._raced:
            self._raced = True
            rival = MatchModel(
                track_id=track_id,
                target_provider=target_provider,
                target_id=target_id,
                target_url=_YT_URL,
                score=0.0,
                matcher_version=COMMUNITY_MATCHER_VERSION,
                status=MatchStatus.AUTO,
                submitted_by=self._rival_submitter,
            )
            self.session.add(rival)
            await self.session.flush()
            self.rival_id = rival.id
            return None  # Our SELECT ran before the rival became visible.
        return await super().get_by_target(track_id, target_provider, target_id)


async def test_concurrent_duplicate_insert_returns_rival_row(session: AsyncSession) -> None:
    """A concurrent submitter losing the unique-constraint race is idempotent, not a 500."""
    track_id = await _make_track(session)
    rival_submitter = uuid.uuid4()
    matches = _RacingMatchRepository(session, rival_submitter)
    svc = SubmissionService(session=session, tracks=TrackRepository(session), matches=matches)

    returned = await svc.submit_match(track_id=track_id, url=_YT_URL, submitted_by=uuid.uuid4())

    # The IntegrityError from our insert is swallowed; we return the rival's row.
    assert returned.id == matches.rival_id
    assert returned.submitted_by == rival_submitter

    # Exactly one row for the target survives — our losing insert was rolled back.
    rows = await MatchRepository(session).list_for_track(track_id)
    assert len([r for r in rows if r.target_id == "dQw4w9WgXcQ"]) == 1
