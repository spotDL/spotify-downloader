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
        (
            "https://open.spotify.com/track/4n7jnSxVLd8QioibtTDBDq",
            "https://music.youtube.com/watch?v=Hkvopu9hVd8",
        ),
        (
            "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv",
            "https://music.youtube.com/watch?v=sJpzMSHKUqI",
        ),
        (
            "https://open.spotify.com/track/4uOHYc6dCVLcNdQBRUlA0G",
            "https://www.youtube.com/watch?v=Mb3tyjibXCg",
        ),
        (
            # this song is bugged on ytmusic for some reason
            # it doesn't show up in search results
            # so we can only find the lyrics version of it
            # which is fine but not ideal
            "https://open.spotify.com/track/1zi7xx7UVEFkmKfv06H8x0",
            "https://www.youtube.com/watch?v=ki0Ocze98U8",
        ),
        (
            "https://open.spotify.com/track/2eaSMmKfigsm96aTUJMoIk",
            "https://music.youtube.com/watch?v=A-PjXUzhFDk",
        ),
        (
            "https://open.spotify.com/track/3rwdcyPQ37SSsf1loOpux9",
            "https://music.youtube.com/watch?v=OWAVbUpr8b4",
        ),
        (
            "https://open.spotify.com/track/760xwlNMwa6IZGff1eBhFW",
            "https://music.youtube.com/watch?v=7xRMrGO-OLo",
        ),
        (
            "https://open.spotify.com/track/07paTkxx4R7rmiGjqm84RM",
            "https://music.youtube.com/watch?v=f-VuVq0I0-U",
        ),
        (
            "https://open.spotify.com/track/6fAmcQ6DjLDA0uHnbdAQmJ",
            "https://music.youtube.com/watch?v=8WIPgiDVeDs",
        ),
        (
            "https://open.spotify.com/track/70C4NyhjD5OZUMzvWZ3njJ",
            "https://music.youtube.com/watch?v=LLbew85exp0",
        ),
        (
            "https://open.spotify.com/track/6l0oJ8fzG0WEplj5uBqwzm",
            "https://music.youtube.com/watch?v=AoXNtriCLt4",
        ),
        (
            "https://open.spotify.com/track/2cqRMfCvT9WIdUiaIVB6EJ",
            "https://music.youtube.com/watch?v=gXElRbmTm2c",
        ),
    ],
)
def test_ytmusic_matching(monkeypatch, query, expected):
    monkeypatch.setattr(SpotifyClient, "init", new_initialize)

    yt_music = YouTubeMusic()

    assert yt_music.search(Song.from_url(query)) == expected
