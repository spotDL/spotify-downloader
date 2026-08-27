from spotdl.download.downloader import Downloader
from spotdl.types.song import Song
from spotdl.utils.downloader import check_ytmusic_connection


def test_check_ytmusic_connection_suppresses_empty_search_log(mocker):
    ytm = mocker.Mock()
    ytm.get_results.return_value = []
    mocker.patch("spotdl.utils.downloader.YouTubeMusic", return_value=ytm)

    assert check_ytmusic_connection() is False
    ytm.get_results.assert_called_once_with("a", log_search_failures=False)


def test_search_falls_back_to_next_audio_provider(mocker):
    first_provider = mocker.Mock()
    first_provider.name = "youtube-music"
    first_provider.search.return_value = None

    second_provider = mocker.Mock()
    second_provider.name = "youtube"
    second_provider.search.return_value = "https://www.youtube.com/watch?v=test"

    downloader = Downloader({"audio_providers": ["youtube-music", "youtube"]})
    downloader.audio_providers = [first_provider, second_provider]

    song = Song.from_dict(
        {
            "name": "The Talented Mr. Tripley",
            "artists": ["DJ Koze"],
            "artist": "DJ Koze",
            "album_id": "test-album",
            "album_name": "Music Can Hear Us",
            "album_artist": "DJ Koze",
            "album_type": "album",
            "genres": [],
            "disc_number": 1,
            "disc_count": 1,
            "duration": 327,
            "year": 2024,
            "date": "2024-04-05",
            "track_number": 1,
            "tracks_count": 1,
            "isrc": "TESTISRC12345",
            "song_id": "test-song",
            "cover_url": "https://example.com/cover.jpg",
            "explicit": False,
            "publisher": "Pampa",
            "url": "https://open.spotify.com/track/test-song",
            "copyright_text": "2024 Pampa Records",
            "download_url": None,
        }
    )

    result = downloader.search(song)

    assert result == "https://www.youtube.com/watch?v=test"
    first_provider.search.assert_called_once_with(song, False)
    second_provider.search.assert_called_once_with(song, False)
