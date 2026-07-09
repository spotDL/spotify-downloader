"""SubmissionService — community-submitted audio matches (spec §6.2, CONTRACT).

A logged-in user proposes a playable audio target for a canonical track by URL
(``POST /tracks/{id}/matches``). The service:

1. resolves the track (:class:`NotFoundError` → 404 if absent);
2. parses the URL through core's :func:`~spotdl_core.providers.parse`
   (:class:`~spotdl_core.providers.UnsupportedURL` → 400 on garbage);
3. requires the ref to be an **audio-provider** ``track`` — Spotify / Deezer /
   iTunes / MusicBrainz URLs are metadata-only, not playable targets, so they raise
   :class:`NotAnAudioTarget` (→ 400);
4. upserts by the Plan 5 unique ``(track_id, target_provider, target_id)`` key.

The submission is stored as ``status=auto`` with ``submitted_by`` set (algorithmic
matches have ``submitted_by IS NULL``); it becomes ``community_verified`` only
through voting (Task 8). The upsert is **idempotent** — a target that already
exists (whether a prior submission or an algorithmic match) is returned unchanged,
so a re-submit never duplicates the row or clobbers an algorithmic match's
provenance. There is **no** synchronous provider fetch in v1: the denormalized
``candidate_*`` fields stay NULL for a later enrichment job to backfill.

Nothing here imports FastAPI; the only ORM type it returns is the ``Match`` row
named in the CONTRACT, which the router maps to a schema. Following Plan 5's
unit-of-work rule the service flushes (through the repository) but never commits.
"""

from __future__ import annotations

from uuid import UUID

from spotdl_core.model import EntityType, ProviderId
from spotdl_core.providers import parse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from spotdl_server.db.models import Match as MatchModel
from spotdl_server.repositories.entities import TrackRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.services.errors import NotAnAudioTarget, NotFoundError

# Sentinel stored in ``matches.matcher_version`` for user submissions (CONTRACT).
COMMUNITY_MATCHER_VERSION = "community"

# The audio (playable) providers. A community match must name a downloadable
# target; metadata-only providers (spotify/deezer/itunes/musicbrainz) are rejected.
_AUDIO_PROVIDERS = frozenset(
    {
        ProviderId.YTMUSIC,
        ProviderId.YOUTUBE,
        ProviderId.SOUNDCLOUD,
        ProviderId.BANDCAMP,
        ProviderId.PIPED,
    }
)


class SubmissionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        tracks: TrackRepository,
        matches: MatchRepository,
    ) -> None:
        self._session = session
        self._tracks = tracks
        self._matches = matches

    async def submit_match(self, *, track_id: UUID, url: str, submitted_by: UUID) -> MatchModel:
        """Add ``url`` as a community audio match for ``track_id`` (idempotent).

        Raises :class:`NotFoundError` if the track is unknown,
        :class:`~spotdl_core.providers.UnsupportedURL` if the URL is unparseable,
        and :class:`NotAnAudioTarget` if it is not an audio-provider track URL.
        """
        if await self._tracks.get(track_id) is None:
            raise NotFoundError(entity_type=EntityType.TRACK, entity_id=track_id)

        ref = parse(url)  # UnsupportedURL (→ 400) on garbage — propagated as-is.
        if ref.provider not in _AUDIO_PROVIDERS or ref.entity_type is not EntityType.TRACK:
            raise NotAnAudioTarget()

        existing = await self._matches.get_by_target(track_id, ref.provider, ref.entity_id)
        if existing is not None:
            # Idempotent: return the row unchanged — never clobber provenance
            # (an algorithmic match keeps ``submitted_by IS NULL`` and its scoring).
            return existing

        # The check-then-act above races the unique ``(track_id, target_provider,
        # target_id)`` constraint: a concurrent submitter (or an algorithmic match
        # landing) can insert the same target in the window after our SELECT. Guard
        # the insert with a savepoint — on the resulting IntegrityError roll back
        # just the failed insert, re-read, and return the now-existing row so the
        # submit stays idempotent instead of surfacing a 500. Mirrors
        # ``VoteService._persist_ledger``'s concurrent-insert handling.
        try:
            async with self._session.begin_nested():
                return await self._matches.create_submission(
                    track_id=track_id,
                    target_provider=ref.provider,
                    target_id=ref.entity_id,
                    target_url=ref.url or url,
                    matcher_version=COMMUNITY_MATCHER_VERSION,
                    submitted_by=submitted_by,
                )
        except IntegrityError:
            conflicting = await self._matches.get_by_target(track_id, ref.provider, ref.entity_id)
            if conflicting is None:
                raise  # Not the target-uniqueness race we handle — propagate.
            return conflicting
