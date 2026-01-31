"""SQLAlchemy database models."""

from spotdl.db.models.album import Album, AlbumPlatformLink
from spotdl.db.models.artist import Artist, ArtistPlatformLink
from spotdl.db.models.base import Base
from spotdl.db.models.match import Match
from spotdl.db.models.playlist import Playlist, PlaylistPlatformLink, PlaylistTrack
from spotdl.db.models.song import Song
from spotdl.db.models.user import User
from spotdl.db.models.user_settings import UserSettings
from spotdl.db.models.vote import Vote

__all__ = [
    "Base",
    "User",
    "UserSettings",
    "Song",
    "Match",
    "Vote",
    "Artist",
    "ArtistPlatformLink",
    "Album",
    "AlbumPlatformLink",
    "Playlist",
    "PlaylistPlatformLink",
    "PlaylistTrack",
]
