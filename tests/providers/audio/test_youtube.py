from spotdl.providers.audio.youtube import YouTube
from spotdl.types.song import Song


def test_yt_search(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": "test_video_id",
                    "title": "Abstrakt - Nobody Else",
                    "duration": 162,
                    "uploader": "Abstrakt",
                    "view_count": 123456,
                }
            ]
        },
    )

    provider = YouTube()

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
                    "album_type": "single",
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


def test_yt_get_results(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": f"video_{index}",
                    "title": f"Lost Identities Moments {index}",
                    "duration": 180 + index,
                    "uploader": "Lost Identities",
                    "view_count": 1000 + index,
                }
                for index in range(6)
            ]
        },
    )

    provider = YouTube()

    results = provider.get_results("Lost Identities Moments")

    assert results and len(results) > 5
    assert results[0].url == "https://www.youtube.com/watch?v=video_0"
    assert results[0].duration == 180
    assert results[0].author == "Lost Identities"


def test_yt_get_results_normalizes_null_metadata(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": "video_0",
                    "title": "Live Stream",
                    "duration": None,
                    "uploader": None,
                    "view_count": None,
                }
            ]
        },
    )

    provider = YouTube()

    results = provider.get_results("live stream")

    assert len(results) == 1
    assert results[0].duration == 0
    assert results[0].author == ""
    assert results[0].views == 0
