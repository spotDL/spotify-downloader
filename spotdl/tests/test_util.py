import sys
import os
import subprocess

import spotdl.util

import pytest


def test_default_music_directory():
    if sys.platform.startswith("linux"):
        output = subprocess.check_output(["xdg-user-dir", "MUSIC"])
        expect_directory = output.decode("utf-8").rstrip()
    else:
        home = os.path.expanduser("~")
        expect_directory = os.path.join(home, "Music")

    directory = spotdl.util.get_music_dir()
    assert directory == expect_directory


@pytest.fixture(scope="module")
def directory_fixture(tmpdir_factory):
    dir_path = os.path.join(str(tmpdir_factory.mktemp("tmpdir")), "filter_this_directory")
    return dir_path


class TestPathFilterer:
    def test_create_directory(self, directory_fixture):
        expect_path = True
        spotdl.util.filter_path(directory_fixture)
        is_path = os.path.isdir(directory_fixture)
        assert is_path == expect_path

    def test_remove_temp_files(self, directory_fixture):
        expect_file = False
        file_path = os.path.join(directory_fixture, "pesky_file.temp")
        open(file_path, "a")
        spotdl.util.filter_path(directory_fixture)
        is_file = os.path.isfile(file_path)
        assert is_file == expect_file


@pytest.mark.parametrize("sec_duration, str_duration", [
    (35, "35"),
    (23, "23"),
    (158, "2:38"),
    (263, "4:23"),
    (4562, "1:16:02"),
    (26765, "7:26:05"),
])
def test_video_time_from_seconds(sec_duration, str_duration):
    duration = spotdl.util.videotime_from_seconds(sec_duration)
    assert duration == str_duration


@pytest.mark.parametrize("str_duration, sec_duration", [
    ("0:23", 23),
	("0:45", 45),
	("2:19", 139),
	("3:33", 213),
	("7:38", 458),
	("1:30:05", 5405),
])
def test_get_seconds_from_video_time(str_duration, sec_duration):
    secs = spotdl.util.get_sec(str_duration)
    assert secs == sec_duration


@pytest.mark.parametrize("duplicates, expected", [
    (("https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",
      "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",),
    ( "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",),),

    (("https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",
      "",
      "https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD",),
    ( "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",
      "https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD",),),

    (("ncs fade",
      "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",
      "",
      "ncs fade",),
    ("ncs fade",
     "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ"),),

    (("ncs spectre ",
      "  https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ",
      ""),
    ( "ncs spectre",
      "https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ"),),
])
def test_remove_duplicates(duplicates, expected):
    uniques = spotdl.util.remove_duplicates(
		duplicates,
		condition=lambda x: x,
		operation=str.strip,
	)
    assert tuple(uniques) == expected

