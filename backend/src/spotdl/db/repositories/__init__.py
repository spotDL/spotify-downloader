"""Database repositories for data access."""

from spotdl.db.repositories.album import AlbumRepository
from spotdl.db.repositories.artist import ArtistRepository
from spotdl.db.repositories.lyrics import LyricsRepository
from spotdl.db.repositories.match import MatchRepository
from spotdl.db.repositories.metadata_snapshot import MetadataSnapshotRepository
from spotdl.db.repositories.playlist import PlaylistRepository
from spotdl.db.repositories.refresh_cooldown import RefreshCooldownRepository
from spotdl.db.repositories.song import SongRepository
from spotdl.db.repositories.user import UserRepository
from spotdl.db.repositories.vote import VoteRepository

__all__ = [
    "AlbumRepository",
    "ArtistRepository",
    "LyricsRepository",
    "MatchRepository",
    "MetadataSnapshotRepository",
    "PlaylistRepository",
    "RefreshCooldownRepository",
    "SongRepository",
    "UserRepository",
    "VoteRepository",
]
