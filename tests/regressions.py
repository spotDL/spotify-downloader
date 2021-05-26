import sys

from spotdl.__main__ import console_entry_point
from spotdl.download import ffmpeg

SONGS = {
    "https://open.spotify.com/track/6CN3e26iQSj1N5lomh0mfO": "Eminem - Like Toy Soldiers.mp3",
    "https://open.spotify.com/track/3bNv3VuUOKgrf5hu3YcuRo": "Adele - Someone Like You.mp3",
}


def test_regressions(monkeypatch, tmpdir):
    """
    Download songs that caused problems in the past, to make sure they won't happen again.
    """
    monkeypatch.chdir(tmpdir)
    monkeypatch.setattr(sys, "argv", ["dummy", *SONGS.keys()])
    monkeypatch.setattr(ffmpeg, "has_correct_version", lambda *_: True)

    console_entry_point()

    assert sorted(
        [
            file.basename
            for file in tmpdir.listdir()
            if file.isfile() and file.basename.startswith(".") is False
        ]
    ) == sorted([*SONGS.values()])
