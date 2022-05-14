import pytest

from spotdl.providers.lyrics.genius import Genius

lyrics = "[Verse 1]\nMore than lovers\nDestined to find, one another\nLike lightning and thunder\nCan't have one without the other (woah)\n\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Beat-Bass]\n\n\n[Verse 2]\nPast the rings of Saturn\nAcross the Milky Way\nWhere it's raining diamonds\nWe'll return someday\nSpeaking life of words\nIn perfect harmony\nI'll run away with you to another galaxy\n\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Beat-Bass]\n\nWe are linked, together\nWe are linked, together\nWe are linked, together\nWe are linked, together\n(oh, Woah)"


@pytest.mark.vcr()
def test_get_genius_lyrics():
    genius = Genius()

    res_lyrics = genius.get_lyrics("Linked", ["Jim Yosef"])

    assert res_lyrics is not None and res_lyrics.lower() == lyrics.lower()
