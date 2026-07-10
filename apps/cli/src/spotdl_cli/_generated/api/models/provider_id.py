from enum import Enum


class ProviderId(str, Enum):
    AZLYRICS = "azlyrics"
    BANDCAMP = "bandcamp"
    DEEZER = "deezer"
    GENIUS = "genius"
    ITUNES = "itunes"
    LASTFM = "lastfm"
    LRCLIB = "lrclib"
    MUSICBRAINZ = "musicbrainz"
    MUSIXMATCH = "musixmatch"
    PIPED = "piped"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    YTMUSIC = "ytmusic"

    def __str__(self) -> str:
        return str(self.value)
