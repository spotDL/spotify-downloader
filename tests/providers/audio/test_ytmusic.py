import pytest

from spotdl.providers.audio import YouTubeMusic
from spotdl.providers.audio.ytmusic import is_view_count
from spotdl.types.song import Song


@pytest.mark.vcr()
def test_ytm_search(mocker):
    # Tie-breaking on view count goes through yt-dlp, which YouTube bot-checks on CI
    mocker.patch.object(YouTubeMusic, "get_views", return_value=0)
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


@pytest.mark.parametrize(
    "name",
    [
        "185.711\xa0Wiedergaben",
        "1\xa0Wiedergabe",
        "42 Wiedergaben",
        "1,2\xa0Mio.\xa0Wiedergaben",
        "3,4 Mrd. Wiedergaben",
    ],
)
def test_is_view_count(name):
    assert is_view_count(name)


@pytest.mark.parametrize(
    "name",
    ["LUCØ", "Alice Gray", "Wiedergaben", "Mio. Wiedergaben", "Blink-182", "112"],
)
def test_is_not_view_count(name):
    assert not is_view_count(name)


def test_ytm_get_results_drops_view_count_artists(mocker):
    client = mocker.Mock()
    client.search.return_value = [
        {
            "videoId": "0X93DSg2ZQg",
            "resultType": "song",
            "title": "Wasted",
            "artists": [
                {"name": "LUCØ", "id": "UCUtQq-artist"},
                {"name": "185.711\xa0Wiedergaben", "id": None},
            ],
            "duration": "2:40",
        },
        {
            "videoId": "video_1",
            "resultType": "song",
            "title": "Wasted",
            "artists": [
                {"name": "LUCØ", "id": "UCUtQq-artist"},
                {"name": "Alice Gray", "id": None},
                {"name": "1,2\xa0Mio.\xa0Wiedergaben", "id": None},
            ],
            "duration": "2:40",
        },
        {
            "videoId": "video_2",
            "resultType": "song",
            "title": "Only Views",
            "artists": [{"name": "1\xa0Wiedergabe", "id": None}],
            "duration": "2:40",
        },
    ]
    mocker.patch("spotdl.providers.audio.ytmusic.YTMusic", return_value=client)

    provider = YouTubeMusic()
    results = provider.get_results("LUCØ - Wasted", filter="songs")

    assert [result.result_id for result in results] == ["0X93DSg2ZQg", "video_1"]
    assert results[0].artists == ("LUCØ",)
    assert results[0].author == "LUCØ"
    # Real artists without a channel id are kept
    assert results[1].artists == ("LUCØ", "Alice Gray")
