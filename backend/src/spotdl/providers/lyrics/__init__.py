"""Lyrics providers for fetching song lyrics from various sources."""

from spotdl.providers.lyrics.azlyrics import AZLyricsProvider
from spotdl.providers.lyrics.base import BaseLyricsProvider
from spotdl.providers.lyrics.genius import GeniusProvider, GeniusWebProvider
from spotdl.providers.lyrics.musixmatch import MusixMatchProvider
from spotdl.providers.lyrics.synced import SyncedLyricsProvider

__all__ = [
    "AZLyricsProvider",
    "BaseLyricsProvider",
    "GeniusProvider",
    "GeniusWebProvider",
    "MusixMatchProvider",
    "SyncedLyricsProvider",
]
