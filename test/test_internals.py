from core import internals

import os


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


class TestVideoTime:
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
