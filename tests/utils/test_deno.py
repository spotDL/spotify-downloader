import pathlib
import platform
import shutil
import zipfile
from io import BytesIO

import pytest

import spotdl.utils.deno
from spotdl.utils.deno import *
from spotdl.utils.formatter import args_to_ytdlp_options


class MockResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        """
        Match the subset of the requests.Response API used by download_deno.
        """


def make_deno_archive(filename="deno"):
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as deno_archive:
        deno_archive.writestr(filename, b"deno")

    return archive.getvalue()


def test_is_not_deno_installed(monkeypatch):
    """
    Test is_deno_installed function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: False)

    assert is_deno_installed() is False


def test_get_none_deno_path(monkeypatch):
    """
    Test get_deno_path function.
    """

    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: False)

    assert get_deno_path() is None


def test_get_none_local_deno(monkeypatch, tmp_path):
    """
    Test get_local_deno function.
    """

    monkeypatch.setattr(spotdl.utils.deno, "get_spotdl_path", lambda: tmp_path)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: False)

    assert get_local_deno() is None


def test_get_local_deno(monkeypatch, tmp_path):
    """
    Test get_local_deno function.
    """

    monkeypatch.setattr(spotdl.utils.deno, "get_spotdl_path", lambda: tmp_path)
    monkeypatch.setattr(pathlib.Path, "is_file", lambda *_: True)

    local_deno = get_local_deno()

    assert local_deno is not None

    if platform.system() == "Windows":
        assert str(local_deno).endswith("deno.exe")
    else:
        assert str(local_deno).endswith("deno")


def test_get_local_deno_yt_dlp_options(monkeypatch, tmp_path):
    """
    Test get_local_deno_yt_dlp_options function.
    """

    local_deno = tmp_path / "deno"
    local_deno.write_bytes(b"deno")
    local_deno.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(spotdl.utils.deno, "get_local_deno", lambda *_: local_deno)

    assert get_local_deno_yt_dlp_options() == {
        "js_runtimes": {"deno": {"path": str(local_deno.absolute())}}
    }


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows does not use POSIX executable bits.",
)
def test_get_local_deno_yt_dlp_options_ignores_non_executable(monkeypatch, tmp_path):
    """
    Test get_local_deno_yt_dlp_options ignores non-executable files.
    """

    local_deno = tmp_path / "deno"
    local_deno.write_bytes(b"deno")
    local_deno.chmod(0o644)
    monkeypatch.setattr(shutil, "which", lambda *_: None)
    monkeypatch.setattr(spotdl.utils.deno, "get_local_deno", lambda *_: local_deno)

    assert get_local_deno_yt_dlp_options() == {}


def test_get_local_deno_yt_dlp_options_ignores_missing_local(monkeypatch):
    """
    Test get_local_deno_yt_dlp_options ignores missing local Deno.
    """

    monkeypatch.setattr(spotdl.utils.deno, "get_local_deno", lambda *_: None)

    assert get_local_deno_yt_dlp_options() == {}


def test_user_js_runtime_overrides_local_deno(monkeypatch, tmp_path):
    """
    Test user-provided yt-dlp js runtime options override spotDL's local Deno.
    """

    local_deno = tmp_path / "deno"
    user_deno = tmp_path / "user-deno"
    local_deno.write_bytes(b"deno")
    local_deno.chmod(0o755)
    monkeypatch.setattr(spotdl.utils.deno, "get_local_deno", lambda *_: local_deno)

    options = args_to_ytdlp_options(
        ["--js-runtimes", f"deno:{user_deno}"],
        get_local_deno_yt_dlp_options(),
    )

    assert options["js_runtimes"] == {"deno": {"path": str(user_deno)}}


def test_audio_provider_uses_local_deno_yt_dlp_options(monkeypatch, tmp_path):
    """
    Test AudioProvider passes spotDL's local Deno options to yt-dlp.
    """

    from spotdl.providers.audio import base

    captured_options = {}

    def mock_youtube_dl(options):
        captured_options.update(options)
        return object()

    monkeypatch.setattr(base, "YoutubeDL", mock_youtube_dl)
    monkeypatch.setattr(base, "get_temp_path", lambda *_: tmp_path)
    monkeypatch.setattr(
        base,
        "get_local_deno_yt_dlp_options",
        lambda *_: {"js_runtimes": {"deno": {"path": "local-deno"}}},
    )

    base.AudioProvider()

    assert captured_options["js_runtimes"] == {"deno": {"path": "local-deno"}}


def test_piped_uses_local_deno_yt_dlp_options(monkeypatch, tmp_path):
    """
    Test Piped passes spotDL's local Deno options to yt-dlp.
    """

    from spotdl.providers.audio import piped

    captured_options = {}

    def mock_youtube_dl(options):
        captured_options.update(options)
        return object()

    monkeypatch.setattr(piped, "YoutubeDL", mock_youtube_dl)
    monkeypatch.setattr(piped, "get_temp_path", lambda *_: tmp_path)
    monkeypatch.setattr(
        piped,
        "get_local_deno_yt_dlp_options",
        lambda *_: {"js_runtimes": {"deno": {"path": "local-deno"}}},
    )

    piped.Piped()

    assert captured_options["js_runtimes"] == {"deno": {"path": "local-deno"}}


@pytest.mark.parametrize(
    ("system", "machine", "filename", "target"),
    [
        ("Windows", "AMD64", "deno.exe", "x86_64-pc-windows-msvc"),
        ("Windows", "ARM64", "deno.exe", "aarch64-pc-windows-msvc"),
        ("Linux", "x86_64", "deno", "x86_64-unknown-linux-gnu"),
        ("Linux", "aarch64", "deno", "aarch64-unknown-linux-gnu"),
        ("Darwin", "x86_64", "deno", "x86_64-apple-darwin"),
        ("Darwin", "arm64", "deno", "aarch64-apple-darwin"),
    ],
)
def test_download_deno(monkeypatch, tmp_path, system, machine, filename, target):
    """
    Test download_deno function.
    """

    urls = []

    def mock_get(url, *_args, **_kwargs):
        urls.append(url)
        if url == DENO_RELEASE_LATEST_URL:
            return MockResponse(b"v1.0.0\n")

        return MockResponse(make_deno_archive(filename))

    monkeypatch.setattr(spotdl.utils.deno, "get_spotdl_path", lambda *_: tmp_path)
    monkeypatch.setattr(spotdl.utils.deno.platform, "system", lambda: system)
    monkeypatch.setattr(spotdl.utils.deno.platform, "machine", lambda: machine)
    monkeypatch.setattr(spotdl.utils.deno.requests, "get", mock_get)

    deno_path = download_deno()

    assert urls == [
        DENO_RELEASE_LATEST_URL,
        f"https://dl.deno.land/release/v1.0.0/deno-{target}.zip",
    ]
    assert deno_path == tmp_path / filename
    assert deno_path.read_bytes() == b"deno"


def test_download_deno_unsupported_platform(monkeypatch):
    """
    Test download_deno raises when Deno does not publish a matching binary.
    """

    monkeypatch.setattr(spotdl.utils.deno.platform, "system", lambda: "FreeBSD")
    monkeypatch.setattr(spotdl.utils.deno.platform, "machine", lambda: "x86_64")

    with pytest.raises(DenoError):
        download_deno()


def test_download_deno_invalid_archive(monkeypatch, tmp_path):
    """
    Test download_deno raises when the downloaded archive is invalid.
    """

    def mock_get(url, *_args, **_kwargs):
        if url == DENO_RELEASE_LATEST_URL:
            return MockResponse(b"v1.0.0\n")

        return MockResponse(b"not a zip")

    monkeypatch.setattr(spotdl.utils.deno, "get_spotdl_path", lambda *_: tmp_path)
    monkeypatch.setattr(spotdl.utils.deno.platform, "system", lambda: "Linux")
    monkeypatch.setattr(spotdl.utils.deno.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(spotdl.utils.deno.requests, "get", mock_get)

    with pytest.raises(DenoError):
        download_deno()
