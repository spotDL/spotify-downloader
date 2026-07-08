from spotdl_core.model import EntityType, LyricsKind, MatchStatus, ProviderId


def test_entity_type_values() -> None:
    assert EntityType.TRACK == "track"
    assert set(EntityType) == {"track", "album", "artist", "playlist"}


def test_provider_ids_include_metadata_and_audio_sources() -> None:
    values = set(ProviderId)
    assert {"spotify", "deezer", "itunes", "musicbrainz"} <= values
    assert {"ytmusic", "youtube", "soundcloud", "bandcamp", "piped"} <= values
    assert {"lrclib", "genius", "musixmatch", "azlyrics"} <= values


def test_match_status_values() -> None:
    assert set(MatchStatus) == {"auto", "community_verified", "rejected"}


def test_lyrics_kind_values() -> None:
    assert set(LyricsKind) == {"plain", "synced"}
