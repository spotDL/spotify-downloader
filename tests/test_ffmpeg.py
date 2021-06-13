from spotdl.download import ffmpeg

valid_version = """
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

outdated_version = """
ffmpeg version 1.0.1-2020-11-19-essentials_build-www.gyan.dev Copyright (c) 2000-2020 the FFmpeg developers
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

nightly_version = """
ffmpeg version N-56723-ga4e518c321-static https://johnvansickle.com/ffmpeg/  Copyright (c) 2000-2021 the FFmpeg developers
built with gcc 8 (Debian 8.3.0-6)
configuration: --enable-gpl --enable-version3 --enable-static --disable-debug --disable-ffplay --disable-indev=sndio --disable-outdev=sndio --cc=gcc --enable-fontconfig --enable-frei0r --enable-gnutls --enable-gmp --enable-libgme --enable-gray --enable-libaom --enable-libfribidi --enable-libass --enable-libvmaf --enable-libfreetype --enable-libmp3lame --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenjpeg --enable-librubberband --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libvorbis --enable-libopus --enable-libtheora --enable-libvidstab --enable-libvo-amrwbenc --enable-libvpx --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxml2 --enable-libdav1d --enable-libxvid --enable-libzvbi --enable-libzimg
libavutil      56. 72.100 / 56. 72.100
libavcodec     58.135.100 / 58.135.100
libavformat    58. 77.100 / 58. 77.100
libavdevice    58. 14.100 / 58. 14.100
libavfilter     7.111.100 /  7.111.100
libswscale      5. 10.100 /  5. 10.100
libswresample   3. 10.100 /  3. 10.100
libpostproc    55. 10.100 / 55. 10.100
"""

invalid_version = """
ffmpeg version N-56723-ga4e518c321-static https://johnvansickle.com/ffmpeg/  Copyright (c) 1998-2001 the FFmpeg developers
built with gcc 8 (Debian 8.3.0-6)
configuration: --enable-gpl --enable-version3 --enable-static --disable-debug --disable-ffplay --disable-indev=sndio --disable-outdev=sndio --cc=gcc --enable-fontconfig --enable-frei0r --enable-gnutls --enable-gmp --enable-libgme --enable-gray --enable-libaom --enable-libfribidi --enable-libass --enable-libvmaf --enable-libfreetype --enable-libmp3lame --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenjpeg --enable-librubberband --enable-libsoxr --enable-libspeex --enable-libsrt --enable-libvorbis --enable-libopus --enable-libtheora --enable-libvidstab --enable-libvo-amrwbenc --enable-libvpx --enable-libwebp --enable-libx264 --enable-libx265 --enable-libxml2 --enable-libdav1d --enable-libxvid --enable-libzvbi --enable-libzimg
libavutil      56. 72.100 / 56. 72.100
libavcodec     58.135.100 / 58.135.100
libavformat    58. 77.100 / 58. 77.100
libavdevice    58. 14.100 / 58. 14.100
libavfilter     7.111.100 /  7.111.100
libswscale      5. 10.100 /  5. 10.100
libswresample   3. 10.100 /  3. 10.100
libpostproc    55. 10.100 / 55. 10.100
"""


def test_valid_version(fake_process):
    fake_process.register_subprocess(["ffmpeg", "-version"], stdout=valid_version)

    assert ffmpeg.has_correct_version() == True


def test_nightly_version(fake_process):
    fake_process.register_subprocess(["ffmpeg", "-version"], stdout=nightly_version)

    assert ffmpeg.has_correct_version() == True


def test_invalid_version(fake_process, capsys):
    fake_process.register_subprocess(["ffmpeg", "-version"], stdout=invalid_version)

    assert ffmpeg.has_correct_version() == False

    output, error = capsys.readouterr()
    assert "Your FFmpeg version couldn't be detected" in error


def test_outdated_version(fake_process, capsys):
    fake_process.register_subprocess(["ffmpeg", "-version"], stdout=outdated_version)

    assert ffmpeg.has_correct_version() == False

    output, error = capsys.readouterr()
    assert "Your FFmpeg installation is too old (1.0), please update to 4.2+\n" in error
