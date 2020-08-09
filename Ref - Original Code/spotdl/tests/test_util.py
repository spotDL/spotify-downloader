import sys
import os
import subprocess

import spotdl.util

import pytest


@pytest.fixture(scope="module")
def directory_fixture(tmpdir_factory):
    dir_path = os.path.join(str(tmpdir_factory.mktemp("tmpdir")), "filter_this_directory")
    return dir_path


@pytest.mark.parametrize("value", [
    5,
    "string",
    {"a": 1, "b": 2},
    (10, 20, 30, "string"),
    [2, 4, "sample"]
])
def test_thread_with_return_value(value):
    returner = lambda x: x
    thread = spotdl.util.ThreadWithReturnValue(
        target=returner,
        args=(value,)
    )
    thread.start()
    assert value == thread.join()


@pytest.mark.parametrize("track, track_type", [
  ("https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD", "spotify"),
  ("spotify:track:3SipFlNddvL0XNZRLXvdZD", "spotify"),
  ("3SipFlNddvL0XNZRLXvdZD", "spotify"),
  ("https://www.youtube.com/watch?v=oMiNsd176NM", "youtube"),
  ("oMiNsd176NM", "youtube"),
  ("kodaline - saving grace", "query"),
  ("or anything else", "query"),
])
def test_track_type(track, track_type):
    assert spotdl.util.track_type(track) == track_type


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

