"""Data-access layer: the sole holders of ORM query code (spec §6).

Repositories accept an :class:`~sqlalchemy.ext.asyncio.AsyncSession` (a unit of
work owned by the caller), take and return ORM models or plain values, and never
commit — the service/UoW commits.
"""

from spotdl_server.repositories.entities import (
    AlbumRepository,
    ArtistRepository,
    PlaylistRepository,
    TrackRepository,
    normalize_artist_name,
)
from spotdl_server.repositories.links import EntityLinkRepository
from spotdl_server.repositories.lyrics import LyricsRepository
from spotdl_server.repositories.matches import MatchRepository
from spotdl_server.repositories.merge import SOURCE_PRIORITY, CanonicalMerger
from spotdl_server.repositories.snapshots import SnapshotRepository

__all__ = [
    "SOURCE_PRIORITY",
    "AlbumRepository",
    "ArtistRepository",
    "CanonicalMerger",
    "EntityLinkRepository",
    "LyricsRepository",
    "MatchRepository",
    "PlaylistRepository",
    "SnapshotRepository",
    "TrackRepository",
    "normalize_artist_name",
]
