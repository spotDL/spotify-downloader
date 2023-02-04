import pytest
from rapidfuzz import fuzz

from spotdl.providers.lyrics.genius import Genius

lyrics = "[Verse 1]\nMore than lovers\nDestined to find one another\nLike lightning and thunder\nCan't have one without the other (woah)\n\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Drop]\n\n[Verse 2]\nPast the rings of Saturn\nAcross the Milky Way\nWhere it's raining diamonds\nWe'll return someday\nSpeaking life of words\nIn perfect harmony\nI'll run away with you to another galaxy\n[Chorus]\nIt was written in the stars\nOh, we can't be torn apart\nWe are linked together\nForged in fire forever\nWe are linked together, together\n\n[Drop]\n\n[Outro]\nWe are linked, together\nWe are linked, together\nWe are linked, together\nWe are linked, together\n(Oh, woah)"


@pytest.mark.vcr()
def test_get_genius_lyrics():
    genius = Genius()

    result = genius.get_lyrics("Linked", ["Jim Yosef"])

    assert result is not None

    assert fuzz.ratio(result, lyrics) > 80
