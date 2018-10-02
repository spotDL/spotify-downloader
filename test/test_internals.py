import sys
import os
import subprocess

from spotdl import internals

import pytest


DUPLICATE_TRACKS_TEST_TABLE = [
    (('https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',
      'https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ'),
     ('https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',)),

    (('https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',
      '',
      'https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD'),
     ('https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',
      'https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD')),

    (('ncs fade',
      'https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',
      '',
      'ncs fade'),
     ('ncs fade',
      'https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ')),

    (('ncs spectre ',
      '  https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ',
      ''),
     ('ncs spectre',
      'https://open.spotify.com/track/2DGa7iaidT5s0qnINlwMjJ'))
]


def test_default_music_directory():
    if sys.platform.startswith('linux'):
        output = subprocess.check_output(['xdg-user-dir', 'MUSIC'])
        expect_directory = output.decode('utf-8').rstrip()
    else:
        home = os.path.expanduser('~')
        expect_directory = os.path.join(home, 'Music')

    directory = internals.get_music_dir()
    assert directory == expect_directory


class TestPathFilterer:
    def test_create_directory(self, tmpdir):
        expect_path = True
        global folder_path
        folder_path = os.path.join(str(tmpdir), 'filter_this_folder')
        internals.filter_path(folder_path)
        is_path = os.path.isdir(folder_path)
        assert is_path == expect_path

    def test_remove_temp_files(self, tmpdir):
        expect_file = False
        file_path = os.path.join(folder_path, 'pesky_file.temp')
        open(file_path, 'a')
        internals.filter_path(folder_path)
        is_file = os.path.isfile(file_path)
        assert is_file == expect_file


class TestVideoTimeFromSeconds:
    def test_from_seconds(self):
        expect_duration = '35'
        duration = internals.videotime_from_seconds(35)
        assert duration == expect_duration

    def test_from_minutes(self):
        expect_duration = '2:38'
        duration = internals.videotime_from_seconds(158)
        assert duration == expect_duration

    def test_from_hours(self):
        expect_duration = '1:16:02'
        duration = internals.videotime_from_seconds(4562)
        assert duration == expect_duration


class TestGetSeconds:
    def test_from_seconds(self):
        expect_secs = 45
        secs = internals.get_sec('0:45')
        assert secs == expect_secs
        secs = internals.get_sec('0.45')
        assert secs == expect_secs

    def test_from_minutes(self):
        expect_secs = 213
        secs = internals.get_sec('3.33')
        assert secs == expect_secs
        secs = internals.get_sec('3:33')
        assert secs == expect_secs

    def test_from_hours(self):
        expect_secs = 5405
        secs = internals.get_sec('1.30.05')
        assert secs == expect_secs
        secs = internals.get_sec('1:30:05')
        assert secs == expect_secs

    def test_raise_error(self):
        with pytest.raises(ValueError):
            internals.get_sec('10*05')
        with pytest.raises(ValueError):
            internals.get_sec('02,28,46')


@pytest.mark.parametrize("duplicates, expected", DUPLICATE_TRACKS_TEST_TABLE)
def test_get_unique_tracks(tmpdir, duplicates, expected):
    file_path = os.path.join(str(tmpdir), 'test_duplicates.txt')
    with open(file_path, 'w') as f:
        f.write('\n'.join(duplicates))

    unique_tracks = internals.get_unique_tracks(file_path)
    assert tuple(unique_tracks) == expected
