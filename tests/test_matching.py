import pytest

from spotdl.types.song import Song
from spotdl.providers.audio.ytmusic import YouTubeMusic
from spotdl.utils.spotify import SpotifyClient
from tests.conftest import new_initialize


@pytest.mark.parametrize(
    "query, expected",
    [
        (
            "https://open.spotify.com/track/0l9XhUIYk2EjT6MHdh4wJU",
            "https://music.youtube.com/watch?v=TIULUkt30Os",
        ),
        (
            "https://open.spotify.com/track/1OdYXTMwjl4f4g4ch05CEq",
            "https://music.youtube.com/watch?v=5uwTXzxOseg",
        ),
        (
            "https://open.spotify.com/track/0QsZ3W21xNvnUnUMbiAY4z",
            "https://www.youtube.com/watch?v=UlYwnX5DO2Y",
        ),
        (
            "https://open.spotify.com/track/6kUB88CQG4dAOkUmURwBLA",
            "https://music.youtube.com/watch?v=_IS-Tvbvjn0",
        ),
        (
            "https://open.spotify.com/track/6cmm1LMvZdB5zsCwX5BjqE",
            "https://music.youtube.com/watch?v=DQ514qIthSc",
        ),
    ],
)
def test_ytmusic_matching(monkeypatch, query, expected):
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    yt_music = YouTubeMusic()

    assert yt_music.search(Song.from_url(query)) == expected
