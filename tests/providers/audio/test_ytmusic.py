import pytest

from spotdl.providers.audio import YouTubeMusic
from spotdl.types.song import Song


@pytest.mark.vcr()
def test_find_isrc_song():
    provider = YouTubeMusic()

    results = provider.get_results("GB2LD2210068")

    assert results[0].link == "https://youtube.com/watch?v=0h6XAAwX8II"


def test_find_song():
    provider = YouTubeMusic()

    song = Song.from_search_term("Lost Identities Moments")

    results = provider.search(song)

    assert results == "https://youtube.com/watch?v=0h6XAAwX8II"
