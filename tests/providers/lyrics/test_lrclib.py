import pytest

from spotdl.providers.lyrics.lrclib import Lrclib


@pytest.mark.vcr()
def test_get_lrclib_lyrics():
    lrclib = Lrclib()

    result = lrclib.get_lyrics("Zertarako amestu", ["Berri Txarrak"])

    assert result is not None
    # A distinctive line from the actual Basque lyrics.
    assert "zertarako amestu" in result.lower()
