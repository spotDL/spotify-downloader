import subprocess
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

TRACK_URL = "https://open.spotify.com/track/2nT5m433s95hvYJH4S7ont"
EXPECTED_TITLE = "Eminem - Curtains Up"
EXPECTED_YT_TITLE = "Eminem - 01 - Eminem - Curtains Up (Skit)"
EXPECTED_YT_URL = "http://youtube.com/watch?v=qk13SFlwG9A"


def test_metadata():
    expect_number = 23
    global meta_tags
    meta_tags = spotify_tools.generate_metadata(TRACK_URL)
    assert len(meta_tags) == expect_number


class TestFileFormat:
    def test_with_spaces(self):
        title = internals.format_string(const.args.file_format, meta_tags)
        assert title == EXPECTED_TITLE

    def test_without_spaces(self):
        const.args.no_spaces = True
        title = internals.format_string(const.args.file_format, meta_tags)
        assert title == EXPECTED_TITLE.replace(" ", "_")


def test_youtube_url():
    url = youtube_tools.generate_youtube_url(TRACK_URL, meta_tags)
    assert url == EXPECTED_YT_URL


def test_youtube_title():
    global content
    content = youtube_tools.go_pafy(TRACK_URL, meta_tags)
    title = youtube_tools.get_youtube_title(content)
    assert title == EXPECTED_YT_TITLE


def test_check_track_exists_before_download(tmpdir):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    songname = internals.format_string(const.args.file_format, meta_tags)
    global file_name
    file_name = internals.sanitize_title(songname)
    track_existence = downloader.CheckExists(file_name, meta_tags)
    check = track_existence.already_exists(TRACK_URL)
    assert check == expect_check


class TestDownload:
    def blank_audio_generator(self, filepath):
        if filepath.endswith(".m4a"):
            cmd = "ffmpeg -f lavfi -i anullsrc -t 1 -c:a aac {}".format(filepath)
        elif filepath.endswith(".webm"):
            cmd = "ffmpeg -f lavfi -i anullsrc -t 1 -c:a libopus {}".format(filepath)
        subprocess.call(cmd.split(" "))

    def test_m4a(self, monkeypatch):
        expect_download = True
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", self.blank_audio_generator)
        download = youtube_tools.download_song(file_name + ".m4a", content)
        assert download == expect_download

    def test_webm(self, monkeypatch):
        expect_download = True
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", self.blank_audio_generator)
        download = youtube_tools.download_song(file_name + ".webm", content)
        assert download == expect_download


class TestFFmpeg:
    def test_convert_from_webm_to_mp3(self, monkeypatch):
        expect_command = "ffmpeg -y -i {0}.webm -codec:a libmp3lame -ar 44100 -b:a 192k -vn {0}.mp3".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".webm", file_name + ".mp3", const.args.folder
        )
        assert ' '.join(command) == expect_command

    def test_convert_from_webm_to_m4a(self, monkeypatch):
        expect_command = "ffmpeg -y -i {0}.webm -cutoff 20000 -codec:a aac -ar 44100 -b:a 192k -vn {0}.m4a".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".webm", file_name + ".m4a", const.args.folder
        )
        assert ' '.join(command) == expect_command

    def test_convert_from_m4a_to_mp3(self, monkeypatch):
        expect_command = "ffmpeg -y -i {0}.m4a -codec:v copy -codec:a libmp3lame -ar 44100 -b:a 192k -vn {0}.mp3".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".m4a", file_name + ".mp3", const.args.folder
        )
        assert ' '.join(command) == expect_command

    def test_convert_from_m4a_to_webm(self, monkeypatch):
        expect_command = "ffmpeg -y -i {0}.m4a -codec:a libopus -vbr on -b:a 192k -vn {0}.webm".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".m4a", file_name + ".webm", const.args.folder
        )
        assert ' '.join(command) == expect_command

    def test_convert_from_m4a_to_flac(self, monkeypatch):
        expect_command = "ffmpeg -y -i {0}.m4a -codec:a flac -ar 44100 -b:a 192k -vn {0}.flac".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".m4a", file_name + ".flac", const.args.folder
        )
        assert ' '.join(command) == expect_command


class TestAvconv:
    def test_convert_from_m4a_to_mp3(self):
        expect_command = "avconv -loglevel debug -i {0}.m4a -ab 192k {0}.mp3 -y".format(os.path.join(const.args.folder, file_name))
        _, command = convert.song(
            file_name + ".m4a", file_name + ".mp3", const.args.folder, avconv=True
        )
        assert ' '.join(command) == expect_command


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
    check = track_existence.already_exists(TRACK_URL)
    os.remove(track_path + ".mp3")
    assert check == expect_check
