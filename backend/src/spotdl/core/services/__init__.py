"""Business logic services."""

from spotdl.core.services.entity import (
    EntityPersistenceError,
    EntityPersistenceService,
    PersistResult,
)
from spotdl.core.services.lyrics import (
    LyricsResult,
    LyricsService,
    LyricsServiceError,
    get_lyrics_service,
)
from spotdl.core.services.match import (
    Match,
    MatchService,
    MatchServiceError,
    NoMatchFoundError,
    get_match_service,
)
from spotdl.core.services.metadata import (
    MetadataService,
    MetadataServiceError,
    get_metadata_service,
)
from spotdl.core.services.song import (
    SongService,
    SongServiceError,
    UnsupportedURLError,
    get_song_service,
)
from spotdl.core.services.vote import (
    DuplicateVoteError,
    MatchNotFoundError,
    VoteNotFoundError,
    VoteService,
    VoteServiceError,
    VoteSummary,
    VoteType,
)

__all__ = [
    # Song Service
    "SongService",
    "SongServiceError",
    "UnsupportedURLError",
    "get_song_service",
    # Metadata Service
    "MetadataService",
    "MetadataServiceError",
    "get_metadata_service",
    # Match Service
    "MatchService",
    "MatchServiceError",
    "NoMatchFoundError",
    "Match",
    "get_match_service",
    # Vote Service
    "VoteService",
    "VoteServiceError",
    "VoteNotFoundError",
    "DuplicateVoteError",
    "MatchNotFoundError",
    "VoteSummary",
    "VoteType",
    # Entity Persistence Service
    "EntityPersistenceService",
    "EntityPersistenceError",
    "PersistResult",
    # Lyrics Service
    "LyricsService",
    "LyricsServiceError",
    "LyricsResult",
    "get_lyrics_service",
]
