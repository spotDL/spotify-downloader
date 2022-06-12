import pytest

from spotdl.providers.audio.youtube import YouTube
from spotdl.types.song import Song


@pytest.mark.vcr()
def test_yt_search():
    provider = YouTube()

    assert (
        provider.search(Song.from_search_term("Lost Identities Moments"))
        == "https://youtube.com/watch?v=14CjyUYO8lE"
    )


@pytest.mark.vcr()
def test_yt_get_results():
    provider = YouTube()

    results = provider.get_results("Lost Identities Moments")

    assert results and len(results) > 5
