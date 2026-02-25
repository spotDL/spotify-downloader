"""SQLAlchemy database models."""

from spotdl.db.models.base import Base
from spotdl.db.models.entity_unified import (
    Entity,
    EntityFieldProvenance,
    EntityRelation,
    EntitySnapshot,
    RelationVote,
)
from spotdl.db.models.lyrics import Lyrics
from spotdl.db.models.metadata_report import (
    MetadataReport,
    MetadataReportEntityType,
    ReportStatus,
)
from spotdl.db.models.refresh_cooldown import RefreshCooldown
from spotdl.db.models.token_blacklist import BlacklistedToken
from spotdl.db.models.user import User
from spotdl.db.models.user_settings import UserSettings
from spotdl.db.models.vote import Vote

__all__ = [
    "Base",
    "User",
    "UserSettings",
    "Entity",
    "EntitySnapshot",
    "EntityFieldProvenance",
    "EntityRelation",
    "RelationVote",
    "Vote",
    "Lyrics",
    "MetadataReport",
    "MetadataReportEntityType",
    "ReportStatus",
    "RefreshCooldown",
    "BlacklistedToken",
]
