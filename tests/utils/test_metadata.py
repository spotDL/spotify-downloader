import pytest

import spotdl.utils.ffmpeg
import spotdl.utils.config

from pathlib import Path

from yt_dlp import YoutubeDL

from spotdl.utils.ffmpeg import convert
from spotdl.utils.metadata import embed_metadata
from spotdl.types.song import Song


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

    yt = YoutubeDL(
        {
            "format": "bestaudio",
            "encoding": "UTF-8",
        }
    )

    download_info = yt.extract_info(
        "https://www.youtube.com/watch?v=h-nHdqC3pPs", download=False
    )

    song = Song.from_data_dump(
        """
        {
            "name": "Ropes",
            "artists": ["Dirty Palm", "Chandler Jewels"],
            "album_name": "Ropes",
            "album_artist": "Dirty Palm",
            "genres": ["gaming edm", "melbourne bounce international"],
            "disc_number": 1,
            "duration": 188,
            "year": 2021,
            "date": "2021-10-28",
            "track_number": 1,
            "tracks_count": 1,
            "isrc": "GB2LD2110301",
            "song_id": "1t2qKa8K72IBC8yQlhD9bU",
            "cover_url": "https://i.scdn.co/image/ab67616d0000b273fe2cb38e4d2412dbb0e54332",
            "explicit": false,
            "download_url": "link",
            "artist" : "Dirty Palm",
            "disc_count": 1,
            "copyright_text": "",
            "publisher": "",
            "url": "https://open.spotify.com/track/1t2qKa8K72IBC8yQlhD9bU"
        }
        """
    )

    output_file = Path(tmpdir / f"test.{output_format}")

    assert download_info is not None
    assert convert(
        input_file=(download_info["url"], download_info["ext"]),
        output_file=output_file,
        output_format=output_format,
    ) == (True, None)

    embed_metadata(output_file, song, output_format)
