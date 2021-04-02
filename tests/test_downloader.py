import asyncio
import shlex
from pathlib import Path
from types import SimpleNamespace

import pytest

from spotdl.download.downloader import DownloadManager
from spotdl.search.songObj import SongObj
from spotdl.download import ffmpeg


def create_song_obj(name="test song", artistsInput:list=["test artist"]) -> SongObj:
    artists = list(map(lambda x: {"name": x},artistsInput))
    raw_track_meta = {
        "name": name,
        "album": {
            "name": "test album",
            "artists": artists,
            "release_date": "2021",
            "images": [
                {"url": "https://i.ytimg.com/vi_webp/iqKdEhx-dD4/hqdefault.webp"}
            ],
        },
        "artists": artists,
        "track_number": "1",
        "genres": ["test genre"],
    }
    raw_album_meta = {"genres": ["test genre"]}
    raw_artist_meta = {"genres": ["test artist genre"]}
    return SongObj(
        raw_track_meta,
        raw_album_meta,
        raw_artist_meta,
        "https://www.youtube.com/watch?v=Th_C95UMegc",
        "test lyrics"
    )


class FakeProcess:
    """Instead of running ffmpeg, just fake it"""

    def __init__(self, command):
        command = shlex.split(command)
        self._input = Path(command[command.index("-i") + 1])
        self._output = Path(command[-1])

    async def communicate(self):
        """
        Ensure that the file has been download, and create empty output file,
        to avoid infinite loop.
        """
        assert self._input.is_file()
        self._output.open("w").close()
        return (None, None)

    async def wait(self):
        return None

    @property
    def returncode(self):
        return 0


async def fake_create_subprocess_shell(command, stdout=None, stderr=None):
    return FakeProcess(command)


@pytest.fixture()
def setup(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    monkeypatch.setattr(ffmpeg, "has_correct_version", lambda *_: True)
    monkeypatch.setattr(
        asyncio.subprocess, "create_subprocess_shell", fake_create_subprocess_shell
    )
    monkeypatch.setattr(DownloadManager, "set_id3_data", lambda *_: None)
    data = SimpleNamespace()
    data.directory = tmpdir
    yield data


@pytest.mark.vcr()
def test_download_single_song(setup):
    song_obj = create_song_obj()
    with DownloadManager() as dm:
        dm.download_single_song(song_obj)

    assert [file.basename for file in setup.directory.listdir() if file.isfile()] == [
        "test artist - test song.mp3"
    ]

@pytest.mark.vcr()
def test_download_long_artists_song(setup):
    # ! Generates a long list of artists, numbered 1 to 260, to trigger filename length cases
    artists = [str(i) for i in range(260)]
    song_obj = create_song_obj(artistsInput=artists)
    with DownloadManager() as dm:
        dm.download_single_song(song_obj)

    assert [file.basename for file in setup.directory.listdir() if file.isfile()] == [
        "0 - test song.mp3"
    ]

@pytest.mark.vcr()
def test_download_long_name_song(setup):
    # ! Generates a long title name,numbered 1 to 260, to trigger filename length cases
    # ! In this case the program cannot save the song, and fails with an OSError
    song = ''.join([str(i) for i in range(260)]d)
    song_obj = create_song_obj(name=song)

    with pytest.raises(OSError):
        with DownloadManager() as dm:
            dm.download_single_song(song_obj)


def test_download_multiple_songs(pytestconfig, setup):
    if not "--disable-vcr" in pytestconfig.invocation_params.args:
        # this test is very similar to the other one, and the http request
        # seems not deterministic so it can't be reliably capture into cassette,
        # therefore run this test only when VCR is disabled
        pytest.skip()

    song_objs = [
        create_song_obj(name="song1"),
        create_song_obj(name="song2"),
        create_song_obj(name="song3"),
    ]
    with DownloadManager() as dm:
        dm.download_multiple_songs(song_objs)

    assert sorted(
        [file.basename for file in setup.directory.listdir() if file.isfile()]
    ) == sorted(
        [
            "test artist - song1.mp3",
            "test artist - song2.mp3",
            "test artist - song3.mp3",
        ]
    )
