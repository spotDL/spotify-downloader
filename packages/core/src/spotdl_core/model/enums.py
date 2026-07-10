from enum import StrEnum


class EntityType(StrEnum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"


class ProviderId(StrEnum):
    # metadata sources
    SPOTIFY = "spotify"
    DEEZER = "deezer"
    ITUNES = "itunes"
    MUSICBRAINZ = "musicbrainz"
    # name-keyed engagement/bio/tags source (Last.fm; not a URL resolver)
    LASTFM = "lastfm"
    # audio targets (ytmusic is also a metadata source)
    YTMUSIC = "ytmusic"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    BANDCAMP = "bandcamp"
    PIPED = "piped"
    # lyrics sources
    LRCLIB = "lrclib"
    GENIUS = "genius"
    MUSIXMATCH = "musixmatch"
    AZLYRICS = "azlyrics"


class MatchStatus(StrEnum):
    AUTO = "auto"
    COMMUNITY_VERIFIED = "community_verified"
    REJECTED = "rejected"


class LyricsKind(StrEnum):
    PLAIN = "plain"
    SYNCED = "synced"
