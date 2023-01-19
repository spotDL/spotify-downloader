import os
import pathlib
import platform
import shutil
from pathlib import Path

import pytest
from yt_dlp import YoutubeDL

import spotdl.utils.config
import spotdl.utils.ffmpeg
from spotdl.utils.ffmpeg import *

ffmpeg_stdout = """
ffmpeg version 4.3.1-2020-11-19-essentials_build-www.gyan.dev Copyright (c) 2000-2020 the FFmpeg developers
built with gcc 10.2.0 (Rev5, Built by MSYS2 project)
configuration: --enable-gpl --enable-version3 --enable-static --disable-w32threads --disable-autodetect --enable-fontconfig --enable-iconv --enable-gnutls --enable-libxml2 --enable-gmp --enable-lzma --enable-zlib --enable-libsrt --enable-libssh --enable-libzmq --enable-avisynth --enable-sdl2 --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxvid --enable-libaom --enable-libopenjpeg --enable-libvpx --enable-libass --enable-libfreetype --enable-libfribidi --enable-libvidstab --enable-libvmaf --enable-libzimg --enable-amf --enable-cuda-llvm --enable-cuvid --enable-ffnvcodec --enable-nvdec --enable-nvenc --enable-d3d11va --enable-dxva2 --enable-libmfx --enable-libgme --enable-libopenmpt --enable-libopencore-amrwb --enable-libmp3lame --enable-libtheora --enable-libvo-amrwbenc --enable-libgsm --enable-libopencore-amrnb --enable-libopus --enable-libspeex --enable-libvorbis --enable-librubberband
libavutil      56. 51.100 / 56. 51.100
libavcodec     58. 91.100 / 58. 91.100
libavformat    58. 45.100 / 58. 45.100
libavdevice    58. 10.100 / 58. 10.100
libavfilter     7. 85.100 /  7. 85.100
libswscale      5.  7.100 /  5.  7.100
libswresample   3.  7.100 /  3.  7.100
libpostproc    55.  7.100 / 55.  7.100
"""


def test_is_not_ffmpeg_installed(monkeypatch):
    """
    Test is_ffmpeg_installed function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(os.path, "isfile", lambda *_: False)
    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_local_ffmpeg", lambda *_: None)

    # Assert is False because ffmpeg is not installed
    assert is_ffmpeg_installed() is False


def test_get_none_ffmpeg_path(monkeypatch):
    """
    Test get_ffmpeg_path function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(os.path, "isfile", lambda *_: False)
    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_local_ffmpeg", lambda *_: None)

    # Assert is None because ffmpeg is not installed
    assert get_ffmpeg_path() is None


def test_get_none_ffmpeg_version(monkeypatch):
    """
    Test get_ffmpeg_version function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(os.path, "isfile", lambda *_: False)
    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_local_ffmpeg", lambda *_: None)

    # Assert is None because ffmpeg is not installed
    with pytest.raises(FFmpegError):
        get_ffmpeg_version()


def test_get_none_local_ffmpeg(monkeypatch):
    """
    Test get_local_ffmpeg function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(os.path, "isfile", lambda *_: False)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: False)

    # Assert is None because ffmpeg is not installed
    assert get_local_ffmpeg() is None


def test_get_local_ffmpeg(monkeypatch):
    """
    Test get_local_ffmpeg function.
    """

    monkeypatch.setattr(os.path, "isfile", lambda *_: True)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: True)

    platform_str = platform.system()

    local_ffmpeg = get_local_ffmpeg()

    assert local_ffmpeg is not None

    if platform_str == "Linux":
        assert str(local_ffmpeg).endswith("ffmpeg")
    elif platform_str == "Darwin":
        assert str(local_ffmpeg).endswith("ffmpeg")
    elif platform_str == "Windows":
        assert str(local_ffmpeg).endswith("ffmpeg.exe")


def test_download_ffmpeg(monkeypatch, tmpdir):
    """
    Test download_ffmpeg function.
    """

    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_spotdl_path", lambda *_: tmpdir)

    assert download_ffmpeg() is not None


def test_convert(tmpdir, monkeypatch):
    """
    Test convert function.
    """

    monkeypatch.chdir(tmpdir)
    monkeypatch.setattr(spotdl.utils.ffmpeg, "get_spotdl_path", lambda *_: tmpdir)

    yt = YoutubeDL(
        {
            "format": "bestaudio",
            "encoding": "UTF-8",
        }
    )

    download_info = yt.extract_info(
        "https://www.youtube.com/watch?v=h-nHdqC3pPs", download=False
    )

    assert download_info is not None

    assert convert(
        input_file=(download_info["url"], download_info["ext"]),
        output_file=Path(tmpdir, "test.mp3"),
    ) == (True, None)

    assert convert(
        input_file=Path(tmpdir, "test.mp3"),
        output_file=Path(tmpdir, "test.m4a"),
        output_format="m4a",
        bitrate="320K",
    ) == (True, None)
