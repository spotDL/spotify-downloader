"""Business logic services."""

from spotdl.core.services.match import (
    Match,
    MatchService,
    MatchServiceError,
    NoMatchFoundError,
    get_match_service,
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
]
