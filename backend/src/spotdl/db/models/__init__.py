"""SQLAlchemy database models."""

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.base import Base
from spotdl.db.models.entity_unified import (
    Entity,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
    RelationVote,
)
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.models.match import Match
from spotdl.db.models.metadata_report import (
    MetadataReport,
    MetadataReportEntityType,
    ReportStatus,
)
from spotdl.db.models.metadata_snapshot import MetadataSnapshot
from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink, PlaylistTrack
from spotdl.db.models.refresh_cooldown import RefreshCooldown
from spotdl.db.models.song import Song
from spotdl.db.models.token_blacklist import BlacklistedToken
from spotdl.db.models.user import User
from spotdl.db.models.user_settings import UserSettings
from spotdl.db.models.vote import Vote

__all__ = [
    "Base",
    "User",
    "UserSettings",
    "Song",
    "Entity",
    "EntitySnapshot",
    "EntityFieldProvenance",
    "EntityRelation",
    "RelationVote",
    "Match",
    "Vote",
    "Artist",
    "ArtistPlatformLink",
    "Album",
    "AlbumPlatformLink",
    "Playlist",
    "PlaylistPlatformLink",
    "PlaylistTrack",
    "Lyrics",
    "MetadataReport",
    "MetadataReportEntityType",
    "ReportStatus",
    "MetadataSnapshot",
    "RefreshCooldown",
    "BlacklistedToken",
]
