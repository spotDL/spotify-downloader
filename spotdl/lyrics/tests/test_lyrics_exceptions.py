from spotdl.lyrics.exceptions import LyricsNotFoundError

def test_lyrics_not_found_subclass():
    assert issubclass(LyricsNotFoundError, Exception)

