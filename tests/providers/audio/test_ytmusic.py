import pytest

from spotdl.providers.audio import YouTubeMusic
from spotdl.types.song import Song


@pytest.mark.vcr()
def test_ytm_search():
    provider = YouTubeMusic()

    assert (
        provider.search(Song.from_search_term("Lost Identities Moments"))
        == "https://youtube.com/watch?v=0h6XAAwX8II"
    )


@pytest.mark.vcr()
def test_ytm_get_results():
    provider = YouTubeMusic()

    results = provider.get_results("Lost Identities Moments")

    assert len(results) > 5
