"""
Synced lyrics provider using the syncedlyrics library
"""

from typing import List, Optional

import syncedlyrics

from spotdl.providers.lyrics.base import LyricsProvider

__all__ = ["Synced"]


class Synced(LyricsProvider):
    """
    Lyrics provider for synced lyrics using the syncedlyrics library
    Currently supported websites: Deezer, NetEase
    """

    def get_lyrics(self, name: str, artists: List[str], **_) -> Optional[str]:
        """
        Try to get lyrics using syncedlyrics

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        lyrics = syncedlyrics.search(f"{name} - {artists[0]}", allow_plain_format=True)
        return lyrics
