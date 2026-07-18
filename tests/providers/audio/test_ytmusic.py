import pytest

from spotdl.providers.audio import YouTubeMusic
from spotdl.types.song import Song


@pytest.mark.vcr()
def test_ytm_search():
    provider = YouTubeMusic()

    assert (
        provider.search(
            Song.from_dict(
                {
                    "name": "Nobody Else",
                    "artists": ["Abstrakt"],
                    "artist": "Abstrakt",
                    "album_id": "0kx3ml8bdAYrQtcIwvkhp8",
                    "album_name": "Nobody Else",
                    "album_artist": "Abstrakt",
                    "album_type": "album",
                    "genres": [],
                    "disc_number": 1,
                    "disc_count": 1,
                    "duration": 162.406,
                    "year": 2022,
                    "date": "2022-03-17",
                    "track_number": 1,
                    "tracks_count": 1,
                    "isrc": "GB2LD2210007",
                    "song_id": "0kx3ml8bdAYrQtcIwvkhp8",
                    "cover_url": "https://i.scdn.co/image/ab67616d0000b27345f5ba253b9825efc88bc236",
                    "explicit": False,
                    "publisher": "NCS",
                    "url": "https://open.spotify.com/track/0kx3ml8bdAYrQtcIwvkhp8",
                    "copyright_text": "2022 NCS",
                    "download_url": None,
                }
            )
        )
        is not None
    )


@pytest.mark.vcr()
def test_ytm_get_results():
    provider = YouTubeMusic()

    results = provider.get_results("Lost Identities Moments")

    assert len(results) > 3


def test_ytm_get_results_retries_with_new_client(mocker):
    first_client = mocker.Mock()
    first_client.search.return_value = []
    second_client = mocker.Mock()
    second_client.search.return_value = [
        {
            "videoId": "video_0",
            "resultType": "song",
            "title": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "duration": "1:23",
        }
    ]
    mocker.patch(
        "spotdl.providers.audio.ytmusic.YTMusic",
        side_effect=[first_client, second_client],
    )

    provider = YouTubeMusic()
    results = provider.get_results("Test Song")

    assert len(results) == 1
    assert results[0].url == "https://music.youtube.com/watch?v=video_0"
    assert results[0].name == "Test Song"
    assert first_client.search.call_count == 1
    assert second_client.search.call_count == 1
