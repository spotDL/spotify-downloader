"""Server-only DB enums.

Core enums (``ProviderId``, ``EntityType``, ``MatchStatus``, ``LyricsKind``) are
imported from :mod:`spotdl_core.model`; these three live only in the server DB.
"""

from enum import StrEnum


class LinkStatus(StrEnum):
    """State of an ``entity_links`` row (canonical entity ↔ snapshot linkage)."""

    AUTO = "auto"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class DownloadStatus(StrEnum):
    """Lifecycle state of a ``download_jobs`` row (Plan 7 queue)."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchKind(StrEnum):
    """Shape of a ``download_batches`` submission (Plan 7)."""

    SINGLE = "single"  # one submitted track/url
    ALBUM = "album"  # album url expanded to N tracks
    PLAYLIST = "playlist"  # playlist url expanded to N tracks


# --------------------------------------------------------------------------- #
# Plan 6 community layer (auth / voting / reports)
# --------------------------------------------------------------------------- #
class OAuthProvider(StrEnum):
    """Third-party OAuth identity provider for ``oauth_identities.provider``."""

    GITHUB = "github"
    DISCORD = "discord"


class VotableType(StrEnum):
    """Polymorphic discriminator for ``votes.votable_type``.

    Values are the string form of the target table: ``votable_id`` points into
    ``matches.id`` / ``lyrics.id`` / ``entity_links.id`` respectively (no
    cross-table FK).
    """

    MATCH = "match"
    LYRICS = "lyrics"
    ENTITY_LINK = "entity_link"


class ReportStatus(StrEnum):
    """Minimal review state of a metadata-correction ``reports`` row."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
