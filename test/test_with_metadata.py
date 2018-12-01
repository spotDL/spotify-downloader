import os

from spotdl import const
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import convert
from spotdl import metadata
from spotdl import downloader

import loader

loader.load_defaults()

TRACK_URL_SPOTI = "https://open.spotify.com/track/2nT5m433s95hvYJH4S7ont"
EXPECTED_TITLE_SPOTI = "Eminem - Curtains Up"
TRACK_URL_YT = "http://youtube.com/watch?v=0BZ6JYwrl2Y"


def test_metadata():
    expect_number = 23
    global meta_tags
    meta_tags = spotify_tools.generate_metadata(TRACK_URL_SPOTI)
    assert len(meta_tags) == expect_number


class TestFileFormat:
    def test_with_spaces(self):
        title = internals.format_string(const.args.file_format, meta_tags)
        assert title == EXPECTED_TITLE_SPOTI

    def test_without_spaces(self):
        const.args.no_spaces = True
        title = internals.format_string(const.args.file_format, meta_tags)
        assert title == EXPECTED_TITLE_SPOTI.replace(" ", "_")


def test_youtube_url():
    global url
    url = youtube_tools.generate_youtube_url(TRACK_URL_SPOTI, meta_tags)
    global match_video
    match_video = loader.match_url_in_search_results(TRACK_URL_YT, TRACK_URL_SPOTI)
    assert url == ('http://youtube.com/watch?v=' + match_video['link'])


def test_youtube_title():
    global content
    content = youtube_tools.go_pafy(url, meta_tags)
    title = youtube_tools.get_youtube_title(content)
    assert title == match_video['title']


def test_check_track_exists_before_download(tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    songname = internals.format_string(const.args.file_format, meta_tags)
    global file_name
    file_name = internals.sanitize_title(songname)
    track_existence = downloader.CheckExists(file_name, meta_tags)
    check = track_existence.already_exists(TRACK_URL_SPOTI)
    assert check == expect_check


class TestDownload:
    def test_m4a(self):
        expect_download = True
        download = youtube_tools.download_song(file_name + ".m4a", content)
        assert download == expect_download

    def test_webm(self):
        expect_download = True
        download = youtube_tools.download_song(file_name + ".webm", content)
        assert download == expect_download


class TestFFmpeg:
    def test_convert_from_webm_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".webm", file_name + ".mp3", const.args.folder
        )
        assert return_code == expect_return_code

    def test_convert_from_webm_to_m4a(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".webm", file_name + ".m4a", const.args.folder
        )
        assert return_code == expect_return_code

    def test_convert_from_m4a_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".m4a", file_name + ".mp3", const.args.folder
        )
        assert return_code == expect_return_code

    def test_convert_from_m4a_to_webm(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".m4a", file_name + ".webm", const.args.folder
        )
        assert return_code == expect_return_code

    def test_convert_from_m4a_to_flac(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".m4a", file_name + ".flac", const.args.folder
        )
        assert return_code == expect_return_code


class TestAvconv:
    def test_convert_from_m4a_to_mp3(self):
        expect_return_code = 0
        return_code = convert.song(
            file_name + ".m4a", file_name + ".mp3", const.args.folder, avconv=True
        )
        assert return_code == expect_return_code


class TestEmbedMetadata:
    def test_embed_in_mp3(self):
        expect_embed = True
        global track_path
        track_path = os.path.join(const.args.folder, file_name)
        embed = metadata.embed(track_path + ".mp3", meta_tags)
        assert embed == expect_embed

    def test_embed_in_m4a(self):
        expect_embed = True
        embed = metadata.embed(track_path + ".m4a", meta_tags)
        os.remove(track_path + ".m4a")
        assert embed == expect_embed

    def test_embed_in_webm(self):
        expect_embed = False
        embed = metadata.embed(track_path + ".webm", meta_tags)
        os.remove(track_path + ".webm")
        assert embed == expect_embed

    def test_embed_in_flac(self):
        expect_embed = True
        embed = metadata.embed(track_path + ".flac", meta_tags)
        os.remove(track_path + ".flac")
        assert embed == expect_embed


def test_check_track_exists_after_download():
    expect_check = True
    track_existence = downloader.CheckExists(file_name, meta_tags)
    check = track_existence.already_exists(TRACK_URL_SPOTI)
    os.remove(track_path + ".mp3")
    assert check == expect_check
