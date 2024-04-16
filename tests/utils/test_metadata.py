from pathlib import Path

import pytest
from yt_dlp import YoutubeDL

import spotdl.utils.config
import spotdl.utils.ffmpeg
from spotdl.types.song import Song
from spotdl.utils.ffmpeg import convert
from spotdl.utils.metadata import embed_metadata, get_file_metadata


@pytest.mark.parametrize(
    "output_format",
    [
        "mp3",
        "flac",
        "opus",
        "ogg",
        "m4a",
    ],
)
def test_embed_metadata(tmpdir, monkeypatch, output_format):
    """
    Test convert function.
    """

    monkeypatch.chdir(tmpdir)
    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_spotdl_path", lambda *_: tmpdir)

    youtube = YoutubeDL(
        {
            "format": "bestaudio",
            "encoding": "UTF-8",
        }
    )

    download_info = youtube.extract_info(
        "https://www.youtube.com/watch?v=h-nHdqC3pPs", download=False
    )

    song_obj = {
        "name": "Ropes",
        "artists": ["Dirty Palm", "Chandler Jewels"],
        "album_id": "15b3456b34562b3456b34",
        "album_name": "Ropes",
        "album_artist": "Dirty Palm",
        "album_year": 2021,
        "genres": ["Gaming Edm"],
        "disc_number": 1,
        "duration": 188,
        "year": 2021,
        "date": "2021-10-28",
        "track_number": 1,
        "tracks_count": 1,
        "isrc": "GB2LD2110301",
        "song_id": "1t2qKa8K72IBC8yQlhD9bU",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
        "explicit": False,
        "download_url": "link",
        "artist": "Dirty Palm",
        "disc_count": 1,
        "copyright_text": "",
        "publisher": "",
        "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU",
        "popularity": 0,
    }

    song = Song.from_dict(song_obj)
    output_file = Path(tmpdir / f"test.{output_format}")

    assert download_info is not None
    assert convert(
        input_file=(download_info["url"], download_info["ext"]),
        output_file=output_file,
        output_format=output_format,
    ) == (True, None)

    embed_metadata(output_file, song)

    assert output_file.exists()

    file_metadata = get_file_metadata(output_file)

    assert file_metadata is not None

    for key, value in song_obj.items():
        meta_val = file_metadata.get(key)
        if meta_val is None:
            continue

        assert file_metadata[key] == value


def test_embed_metadata_album_year(tmpdir):
    # Create a mock song object with specific metadata including album year
    song_obj = {
        "name": "Ropes",
        "artists": ["Dirty Palm", "Chandler Jewels"],
        "album_id": "15b3456b34562b3456b34",
        "album_name": "Ropes",
        "album_artist": "Dirty Palm",
        "album_year": 2021,  # This is the field we're testing
        "genres": ["Gaming Edm"],
        "disc_number": 1,
        "duration": 188,
        "year": 2020,  # This is the track release year
        "date": "2021-10-28",
        "track_number": 1,
        "tracks_count": 1,
        "isrc": "GB2LD2110301",
        "song_id": "1t2qKa8K72IBC8yQlhD9bU",
        "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
        "explicit": False,
        "download_url": "link",
        "artist": "Dirty Palm",
        "disc_count": 1,
        "copyright_text": "",
        "publisher": "",
        "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU",
        "popularity": 0,
    }

    song = Song.from_dict(song_obj)

    # Use a temporary directory for output files
    output_file = Path(tmpdir) / "test.mp3"
    embed_metadata(output_file, song, id3_separator="/")

    # Retrieve metadata from the file
    file_metadata = get_file_metadata(output_file)

    # Assert that the album year (or track year) is embedded and retrieved correctly
    assert file_metadata["year"] == song.album_year, f"Expected album year {song.album_year} but got {file_metadata.get('year')}"
