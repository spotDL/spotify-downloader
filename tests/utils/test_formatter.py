from pathlib import Path

from spotdl.types.song import Song, SongList
from spotdl.utils.formatter import (
    create_file_name,
    create_song_title,
    parse_duration,
    sanitize_string,
    restrict_filename,
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


def test_restrict_filename_sanitizes_directories():
    """
    Test that restrict_filename sanitizes ALL path components, not just filename.
    
    This test verifies the fix for issue #2371:
    https://github.com/spotDL/spotify-downloader/issues/2371
    """
    
    input_path = Path("Mötley Crüe/Girls, Girls, Girls (Deluxe Version)/Wild Side.m4a")
    result = restrict_filename(input_path, strict=True)
    expected = Path("Motley_Crue/Girls_Girls_Girls_Deluxe_Version/Wild_Side.m4a")
    
    assert result == expected


def test_create_file_name_with_directory_restrict():
    """
    Test that create_file_name with restrict sanitizes directory paths.
    
    This is the main fix for issue #2371 - testing the actual use case
    where users specify {artist}/{album}/{title} templates.
    """

    song = Song.from_dict({
        "name": "Wild Side",
        "artists": ["Mötley Crüe"],
        "artist": "Mötley Crüe",
        "album_name": "Girls, Girls, Girls (Deluxe Version)",
        "album_artist": "Mötley Crüe",
        "album_type": "album",
        "genres": ["rock"],
        "disc_number": 1,
        "disc_count": 1,
        "duration": 263.0,
        "year": "1987",
        "date": "1987-05-15",
        "track_number": 1,
        "tracks_count": 13,
        "song_id": "7zVpUAOuXY7pHHSm21jFEq",
        "explicit": False,
        "url": "https://open.spotify.com/track/7zVpUAOuXY7pHHSm21jFEq",
        "publisher": "Elektra Records",
        "isrc": "USUM71700123",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273test",
        "copyright_text": "1987 Elektra Entertainment",
    })
    
    result = create_file_name(
        song, "{artist}/{album}/{title}", "m4a", restrict="strict"
    )
    expected = Path("Motley_Crue/Girls_Girls_Girls_Deluxe_Version/Wild_Side.m4a")
    
    assert result == expected


def test_fat32_compatibility_characters():
    """
    Test that characters problematic for FAT32 are properly sanitized.
    """

    test_cases = [
        (Path("Björk/Homogenic/Jóga.m4a"), Path("Bjork/Homogenic/Joga.m4a")),
        (Path("AC/DC/Back in Black/T.N.T.m4a"), Path("AC_DC/Back_in_Black/T.N.T.m4a")),
        (Path("Sigur Rós/Ágætis byrjun/Svefn-g-englar.m4a"), Path("Sigur_Ros/Agaetis_byrjun/Svefn-g-englar.m4a")),
    ]
    
    for input_path, expected_path in test_cases:
        result = restrict_filename(input_path, strict=True)
        assert result == expected_path, f"Expected {expected_path}, got {result}"