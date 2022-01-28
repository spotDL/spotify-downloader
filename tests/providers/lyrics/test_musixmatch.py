import pytest

from spotdl.providers.lyrics.musixmatch import MusixMatch

lyrics = "Stranded in the open\nDried out tears of sorrow\nLacking all emotion\nStaring down the barrel waiting for the\nFinal gates to open\nTo a new tomorrow\nMoving with the motion\nFollowing the light that sets me free\n\nSets me free"


@pytest.mark.vcr()
def test_get_musixmatch_lyrics():
    musixmatch = MusixMatch()

    assert musixmatch.get_lyrics("Mortals", ["Warriyo"]) == lyrics
