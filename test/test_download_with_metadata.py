import subprocess
import os

from spotdl import const
from spotdl import internals
from spotdl import spotify_tools
from spotdl import youtube_tools
from spotdl import convert
from spotdl import metadata
from spotdl import downloader

import pytest
import loader

loader.load_defaults()

SPOTIFY_TRACK_URL = "https://open.spotify.com/track/3SipFlNddvL0XNZRLXvdZD"
EXPECTED_YOUTUBE_TITLE = "Janji - Heroes Tonight (feat. Johnning) [NCS Release]"
EXPECTED_SPOTIFY_TITLE = "Janji - Heroes Tonight"
EXPECTED_YOUTUBE_URL = "http://youtube.com/watch?v=3nQNiWdeH2Q"
# GIST_URL is the monkeypatched version of: https://www.youtube.com/results?search_query=janji+-+heroes
# so that we get same results even if YouTube changes the list/order of videos on their page.
GIST_URL = "https://gist.githubusercontent.com/ritiek/e731338e9810e31c2f00f13c249a45f5/raw/c11a27f3b5d11a8d082976f1cdd237bd605ec2c2/search_results.html"


def pytest_namespace():
    # XXX: We override the value of `content_fixture` later in the tests.
    # We do not use an acutal @pytest.fixture because it does not accept
    # the monkeypatch parameter and we need to monkeypatch the network
    # request before creating the Pafy object.
    return {"content_fixture": None}


@pytest.fixture(scope="module")
def metadata_fixture():
    meta_tags = spotify_tools.generate_metadata(SPOTIFY_TRACK_URL)
    return meta_tags


def test_metadata(metadata_fixture):
    expect_number = 24
    assert len(metadata_fixture) == expect_number


class TestFileFormat:
    def test_with_spaces(self, metadata_fixture):
        title = internals.format_string(const.args.file_format, metadata_fixture)
        assert title == EXPECTED_SPOTIFY_TITLE

    def test_without_spaces(self, metadata_fixture):
        const.args.no_spaces = True
        title = internals.format_string(const.args.file_format, metadata_fixture)
        assert title == EXPECTED_SPOTIFY_TITLE.replace(" ", "_")


def test_youtube_url(metadata_fixture, monkeypatch):
    monkeypatch.setattr(
        youtube_tools.GenerateYouTubeURL,
        "_fetch_response",
        loader.monkeypatch_youtube_search_page,
    )
    url = youtube_tools.generate_youtube_url(SPOTIFY_TRACK_URL, metadata_fixture)
    assert url == EXPECTED_YOUTUBE_URL


def test_youtube_title(metadata_fixture, monkeypatch):
    monkeypatch.setattr(
        youtube_tools.GenerateYouTubeURL,
        "_fetch_response",
        loader.monkeypatch_youtube_search_page,
    )
    content = youtube_tools.go_pafy(SPOTIFY_TRACK_URL, metadata_fixture)
    pytest.content_fixture = content
    title = youtube_tools.get_youtube_title(content)
    assert title == EXPECTED_YOUTUBE_TITLE


@pytest.fixture(scope="module")
def filename_fixture(metadata_fixture):
    songname = internals.format_string(const.args.file_format, metadata_fixture)
    filename = internals.sanitize_title(songname)
    return filename


def test_check_track_exists_before_download(tmpdir, metadata_fixture, filename_fixture):
    expect_check = False
    const.args.folder = str(tmpdir)
    # prerequisites for determining filename
    track_existence = downloader.CheckExists(filename_fixture, metadata_fixture)
    check = track_existence.already_exists(SPOTIFY_TRACK_URL)
    assert check == expect_check


class TestDownload:
    def blank_audio_generator(self, filepath):
        if filepath.endswith(".m4a"):
            cmd = "ffmpeg -f lavfi -i anullsrc -t 1 -c:a aac {}".format(filepath)
        elif filepath.endswith(".webm"):
            cmd = "ffmpeg -f lavfi -i anullsrc -t 1 -c:a libopus {}".format(filepath)
        subprocess.call(cmd.split(" "))

    def test_m4a(self, monkeypatch, filename_fixture):
        expect_download = True
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", self.blank_audio_generator)
        monkeypatch.setattr("pafy.backend_youtube_dl.YtdlStream.download", self.blank_audio_generator)
        download = youtube_tools.download_song(filename_fixture + ".m4a", pytest.content_fixture)
        assert download == expect_download

    def test_webm(self, monkeypatch, filename_fixture):
        expect_download = True
        monkeypatch.setattr("pafy.backend_shared.BaseStream.download", self.blank_audio_generator)
        monkeypatch.setattr("pafy.backend_youtube_dl.YtdlStream.download", self.blank_audio_generator)
        download = youtube_tools.download_song(filename_fixture + ".webm", pytest.content_fixture)
        assert download == expect_download


class TestFFmpeg:
    def test_convert_from_webm_to_mp3(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.webm -codec:a libmp3lame -ar 44100 -b:a 192k -vn {0}.mp3".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        monkeypatch.setattr("os.remove", lambda x: None)
        _, command = convert.song(
            filename_fixture + ".webm", filename_fixture + ".mp3", const.args.folder
        )
        assert " ".join(command) == expect_command

    def test_convert_from_webm_to_m4a(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.webm -cutoff 20000 -codec:a aac -ar 44100 -b:a 192k -vn {0}.m4a".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        monkeypatch.setattr("os.remove", lambda x: None)
        _, command = convert.song(
            filename_fixture + ".webm", filename_fixture + ".m4a", const.args.folder
        )
        assert " ".join(command) == expect_command

    def test_convert_from_m4a_to_mp3(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.m4a -codec:v copy -codec:a libmp3lame -ar 44100 -b:a 192k -vn {0}.mp3".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        monkeypatch.setattr("os.remove", lambda x: None)
        _, command = convert.song(
            filename_fixture + ".m4a", filename_fixture + ".mp3", const.args.folder
        )
        assert " ".join(command) == expect_command

    def test_convert_from_m4a_to_webm(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.m4a -codec:a libopus -vbr on -b:a 192k -vn {0}.webm".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        monkeypatch.setattr("os.remove", lambda x: None)
        _, command = convert.song(
            filename_fixture + ".m4a", filename_fixture + ".webm", const.args.folder
        )
        assert " ".join(command) == expect_command

    def test_convert_from_m4a_to_flac(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.m4a -codec:a flac -ar 44100 -b:a 192k -vn {0}.flac".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        monkeypatch.setattr("os.remove", lambda x: None)
        _, command = convert.song(
            filename_fixture + ".m4a", filename_fixture + ".flac", const.args.folder
        )
        assert " ".join(command) == expect_command

    def test_correct_container_for_m4a(self, filename_fixture, monkeypatch):
        expect_command = "ffmpeg -y -hide_banner -nostats -v panic -i {0}.m4a.temp -acodec copy -b:a 192k -vn {0}.m4a".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        _, command = convert.song(
            filename_fixture + ".m4a", filename_fixture + ".m4a", const.args.folder
        )
        assert " ".join(command) == expect_command


class TestAvconv:
    @pytest.mark.skip(reason="avconv is no longer provided with FFmpeg")
    def test_convert_from_m4a_to_mp3(self, filename_fixture, monkeypatch):
        monkeypatch.setattr("os.remove", lambda x: None)
        expect_command = "avconv -loglevel 0 -i {0}.m4a -ab 192k {0}.mp3 -y".format(
            os.path.join(const.args.folder, filename_fixture)
        )
        _, command = convert.song(
            filename_fixture + ".m4a",
            filename_fixture + ".mp3",
            const.args.folder,
            avconv=True,
        )
        assert " ".join(command) == expect_command


@pytest.fixture(scope="module")
def trackpath_fixture(filename_fixture):
    trackpath = os.path.join(const.args.folder, filename_fixture)
    return trackpath


class TestEmbedMetadata:
    def test_embed_in_mp3(self, metadata_fixture, trackpath_fixture):
        expect_embed = True
        embed = metadata.embed(trackpath_fixture + ".mp3", metadata_fixture)
        assert embed == expect_embed

    def test_embed_in_m4a(self, metadata_fixture, trackpath_fixture):
        expect_embed = True
        embed = metadata.embed(trackpath_fixture + ".m4a", metadata_fixture)
        os.remove(trackpath_fixture + ".m4a")
        assert embed == expect_embed

    def test_embed_in_webm(self, metadata_fixture, trackpath_fixture):
        expect_embed = False
        embed = metadata.embed(trackpath_fixture + ".webm", metadata_fixture)
        os.remove(trackpath_fixture + ".webm")
        assert embed == expect_embed

    def test_embed_in_flac(self, metadata_fixture, trackpath_fixture):
        expect_embed = True
        embed = metadata.embed(trackpath_fixture + ".flac", metadata_fixture)
        os.remove(trackpath_fixture + ".flac")
        assert embed == expect_embed


def test_check_track_exists_after_download(
    metadata_fixture, filename_fixture, trackpath_fixture
):
    expect_check = True
    track_existence = downloader.CheckExists(filename_fixture, metadata_fixture)
    check = track_existence.already_exists(SPOTIFY_TRACK_URL)
    os.remove(trackpath_fixture + ".mp3")
    assert check == expect_check
