from pathlib import Path

from spotdl.types.song import Song, SongList
from spotdl.utils.formatter import (
    create_file_name,
    create_song_title,
    parse_duration,
    sanitize_string,
)


def test_create_song_title():
    """
    Test create song title function
    """

    assert (
        create_song_title("title", ["artist1", "artist2"]) == "artist1, artist2 - title"
    )
    assert create_song_title("title", []) == "title"


def test_sanitize_string():
    """
    Test sanitize string function
    """

    assert sanitize_string("test") == "test"
    assert sanitize_string("test/?\\*|<>") == "test"
    assert sanitize_string('test" and :') == "test' and -"


def test_create_file_name():
    """
    Test create file name function
    """

    song_dict = {
        "name": "Ropes",
        "artists": ["Dirty Palm", "Chandler Jewels"],
        "album_id": "test",
        "album_name": "Ropes",
        "album_artist": "Dirty Palm",
        "album_type": "single",
        "genres": ["gaming edm", "melbourne bounce international"],
        "disc_number": 1,
        "duration": 188.0,
        "year": "2021",
        "date": "2021-10-28",
        "track_number": 1,
        "tracks_count": 1,
        "isrc": "GB2LD2110301",
        "song_id": "1t2qKa8K72IBC8yQlhD9bU",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
        "explicit": False,
        "download_url": "https://youtube.com/watch?v=rXwPt8DIj74",
        "artist": "Dirty Palm",
        "disc_count": 1,
        "copyright_text": "",
        "publisher": "",
        "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU",
        "list_position": 5,
        "list_name": "test",
        "list_length": 11,
    }

    song = Song.from_dict(song_dict)

    assert create_file_name(song, "test", "mp3") == Path(
        "test/Dirty Palm, Chandler Jewels - Ropes.mp3"
    )

    assert create_file_name(song, "test", "mp3", short=True) == Path(
        "test/Dirty Palm - Ropes.mp3"
    )

    assert create_file_name(song, "{title} - {artist}", "mp3") == Path(
        "Ropes - Dirty Palm.mp3"
    )

    assert create_file_name(song, "{title} - {artist}", "mp3", short=True) == Path(
        "Ropes - Dirty Palm.mp3"
    )

    assert create_file_name(song, "{isrc}/", "mp3") == Path(
        "GB2LD2110301/Dirty Palm, Chandler Jewels - Ropes.mp3"
    )

    assert create_file_name(song, "{isrc}", "mp3") == Path("GB2LD2110301.mp3")

    assert create_file_name(song, "{isrc}.../...{title} - {artist}...", "mp3") == Path(
        "GB2LD2110301/Ropes - Dirty Palm....mp3"
    )

    assert create_file_name(
        song,
        "{list-position}/{list-length} {title} - {artist}",
        "mp3",
    ) == Path(  # type: ignore
        "05/11 Ropes - Dirty Palm.mp3"
    )


def test_create_file_name_restrict():
    """
    Test restrict options in create file name function
    """

    song = Song.from_dict(
        {
            "name": "Crazy - Nôze Remix - Extended Club Version",
            "artists": ["Ornette"],
            "artist": "Ornette",
            "genres": ["french indie pop"],
            "disc_number": 1,
            "disc_count": 1,
            "album_name": "Crazy (Nôze Remix)",
            "album_artist": "Ornette",
            "album_type": "album",
            "duration": 359.835,
            "year": 2012,
            "date": "2012-02-06",
            "track_number": 2,
            "tracks_count": 2,
            "song_id": "5OkuO5pfHG6Gmput8aV4ju",
            "explicit": False,
            "publisher": "Discograph",
            "url": "https://open.spotify.com/track/5OkuO5pfHG6Gmput8aV4ju",
            "isrc": "FRP211100610",
            "cover_url": "https://i.scdn.co/image/ab67616d0000b273336ebd9ff0bfe3fe97652887",
            "copyright_text": "2012 Discograph",
            "download_url": None,
            "lyrics": None,
            "popularity": 42,
            "album_id": "5WH54AbrW5ILvVavvuqFwo",
            "list_name": None,
            "list_url": None,
            "list_position": None,
            "list_length": None,
        }
    )

    assert create_file_name(
        song, "{artist} - {title}", "mp3", restrict="strict"
    ) == Path("Ornette-Crazy-Noze_Remix-Extended_Club_Version.mp3")

    assert create_file_name(
        song, "{artist} - {title}", "mp3", restrict="ascii"
    ) == Path("Ornette - Crazy - Noze Remix - Extended Club Version.mp3")

    assert create_file_name(song, "{artist} - {title}", "mp3", restrict=None) == Path(
        "Ornette - Crazy - Nôze Remix - Extended Club Version.mp3"
    )


def test_parse_duration():
    """
    Test the duration parsing
    """

    assert parse_duration("3:16") == float(196.0)  # 3 min song
    assert parse_duration("20") == float(20.0)  # 20 second song
    assert parse_duration("25:59") == float(1559.0)  # 26 min result
    assert parse_duration("25:59:59") == float(93599.0)  # 26 hour result
    assert parse_duration("likes") == float(0.0)  # bad values
    assert parse_duration("views") == float(0.0)
    assert parse_duration([1, 2, 3]) == float(0.0)  # type: ignore
    assert parse_duration({"json": "data"}) == float(0.0)  # type: ignore
