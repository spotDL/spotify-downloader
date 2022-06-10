import pytest

from spotdl.providers.lyrics.azlyrics import AzLyrics

lyrics = "Always think about you\nAlways thought I have a life I could grow with you\nAs time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nAlways think about you\nAlways thought I have a life I could grow with you\nAs time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nAlways think about you\nAlways thought I have a life I could grow with you\nBut as time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nFeeling like a shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave\n\nFeeling like this shockwave\nGet out of this shockwave\n\nShockwave without you\nShockwave without you\n\nAlways think about you\nAlways thought I have a life I could grow with you\nAs time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nAlways think about you\nAlways thought I have a life I could grow with you\nBut as time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nAlways think about you\nAlways thought I have a life I could grow with you\nBut as time fades, crazy how our lifes changed\nFeeling like a shockwave without you\n\nFeeling like a shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave, shockwave\n\nFeeling like this shockwave\nGet out of this shockwave\n"


@pytest.mark.vcr()
def test_get_azlyrics_lyrics():
    azlyrics = AzLyrics()

    assert azlyrics.get_lyrics("Shockwave", ["Marshmello"]) == lyrics
