import pytest

from spotdl.types.saved import SavedError
from spotdl.types.song import Song
from spotdl.utils.search import get_search_results, get_simple_songs, parse_query

SONG = ["https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv"]
PLAYLIST = ["https://open.spotify.com/playlist/78Lg6HmUqlTnmipvNxc536"]
ALBUM = ["https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT"]
YT = [
    "https://www.youtube.com/watch?v=BZKwsPIhVO8|https://open.spotify.com/track/4B2kkxg3wKSTZw5JPaUtzQ"
]
ARTIST = ["https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6"]
ALBUM_SEARCH = ["album: yeezus"]

QUERY = SONG + PLAYLIST + ALBUM + YT + ARTIST

SAVED = ["saved"]


@pytest.mark.vcr()
def test_playlist_with_only_duplicates():
    query = ["https://open.spotify.com/playlist/1MmajbspTdQCnCSVveSlG3?si=05981d33e9b24d57"]
    songs = get_simple_songs(query)
    assert len(songs) == 2


@pytest.mark.vcr()
def test_regular_playlist():
    query = ["https://open.spotify.com/album/0YniOccoeVuymVK8Lpb7VR?si=EIgojuhsQka2cf1c19Yr7w"]
    songs = get_simple_songs(query)
    assert len(songs) == 21


@pytest.mark.vcr()
def test_playlist_with_duplicate():
    query = ["https://open.spotify.com/playlist/30orXVZ79dv640tpOoWNDP?si=1d1ad6c047ff45a4"]
    songs = get_simple_songs(query)
    assert len(songs) == 5


@pytest.mark.vcr()
def test_playlist_with_songs_with_same_name():
    query = ["https://open.spotify.com/playlist/7FPXF1EQp4FnWBMdhT05R4?si=e4a920a5ce094341"]
    songs = get_simple_songs(query)
    assert len(songs) == 3


@pytest.mark.vcr()
def test_parse_song():
    songs = parse_query(SONG)

    song = songs[0]
    assert len(songs) == 1
    assert song.download_url == None


@pytest.mark.vcr()
def test_parse_album():
    songs = parse_query(ALBUM)

    assert len(songs) == 16
    assert songs[0].url == "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv"


@pytest.mark.vcr()
def test_parse_yt_link():
    songs = parse_query(YT)

    assert len(songs) == 1
    assert songs[0].url == "https://open.spotify.com/track/4B2kkxg3wKSTZw5JPaUtzQ"
    assert songs[0].download_url == "https://www.youtube.com/watch?v=BZKwsPIhVO8"


@pytest.mark.vcr()
def test_parse_artist():
    songs = parse_query(ARTIST)

    assert len(songs) > 1


@pytest.mark.vcr()
def test_parse_album_search():
    songs = parse_query(ALBUM_SEARCH)

    assert len(songs) > 1


@pytest.mark.vcr()
def test_parse_saved():
    with pytest.raises(SavedError):
        parse_query(SAVED)


def test_parse_query():
    songs = parse_query(QUERY)

    assert len(songs) > 1


@pytest.mark.vcr()
def test_get_search_results():
    results = get_search_results("test")
    assert len(results) > 1


def test_create_empty_song():
    song = Song.from_missing_data(name="test")
    assert song.name == "test"
    assert song.url == None
    assert song.download_url == None
    assert song.duration == None
    assert song.artists == None


@pytest.mark.vcr()
def test_get_simple_songs():
    songs = get_simple_songs(QUERY)
    assert len(songs) > 1
