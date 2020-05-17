import sys
import os
import subprocess

import spotdl.util

import pytest


@pytest.fixture(scope="module")
def directory_fixture(tmpdir_factory):
    dir_path = os.path.join(str(tmpdir_factory.mktemp("tmpdir")), "filter_this_directory")
    return dir_path


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

