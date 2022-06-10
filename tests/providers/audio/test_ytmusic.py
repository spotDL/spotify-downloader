import pytest

from spotdl.providers.audio import YouTubeMusic
from spotdl.types.song import Song


@pytest.mark.vcr()
def find_songs():
    provider = YouTubeMusic()

    assert (
        provider.search(Song.from_search_term("Lost Identities Moments"))
        == "https://youtube.com/watch?v=0h6XAAwX8II"
    )
