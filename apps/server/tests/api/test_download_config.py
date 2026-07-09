"""Task 1 — download settings, ``DownloadConfig`` builder, ``/config`` surface.

The settings names/defaults and the ``/config`` ``download_defaults`` shape are a
CONTRACT (web/TUI read them; Plan 8 clients generate against them). These tests
pin the v4-parity defaults, the ``DownloadConfig`` build (dirs + shlex-tokenized
passthrough args), the auth-consistency fail-fast, and the mode-gated
``download_defaults`` block on ``GET /config``.
"""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr
from spotdl_core.download import DownloadConfig, OutputFormat, RestrictMode
from spotdl_server.app import create_app
from spotdl_server.auth.clock import SystemClock
from spotdl_server.ratelimit.memory import InMemoryRateLimiter
from spotdl_server.settings import DeploymentMode, Settings


# --------------------------------------------------------------------------- #
# settings + DownloadConfig builder
# --------------------------------------------------------------------------- #
def test_download_defaults_present() -> None:
    s = Settings(mode=DeploymentMode.SELFHOST)
    assert s.download_concurrency == 2
    assert s.default_output_format is OutputFormat.MP3
    assert s.default_bitrate == "auto"
    assert s.default_output_template == "{artists} - {title}.{output-ext}"
    assert s.ffmpeg_path == "ffmpeg"
    assert s.downloads_enabled() is True


def test_effective_library_and_temp_resolve_inside_data_dir(tmp_path: object) -> None:
    s = Settings(mode=DeploymentMode.SELFHOST, data_dir=tmp_path)  # type: ignore[arg-type]
    lib = s.effective_library_path()
    tmp = s.effective_temp_dir()
    assert lib == (s.data_dir / "music")
    assert tmp == (s.data_dir / "temp")
    assert str(lib).startswith(str(s.data_dir))
    assert str(tmp).startswith(str(s.data_dir))


def test_explicit_library_and_temp_override(tmp_path: object) -> None:
    lib = tmp_path / "L"  # type: ignore[operator]
    tmp = tmp_path / "T"  # type: ignore[operator]
    s = Settings(mode=DeploymentMode.SELFHOST, library_path=lib, download_temp_dir=tmp)
    assert s.effective_library_path() == lib
    assert s.effective_temp_dir() == tmp


def test_download_config_builds_dirs_and_tokenizes_args(tmp_path: object) -> None:
    s = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=tmp_path,  # type: ignore[arg-type]
        ytdlp_args="--no-cache-dir --retries 3",
        ffmpeg_args="-hide_banner -loglevel error",
    )
    cfg = s.download_config()
    assert isinstance(cfg, DownloadConfig)
    assert cfg.output_dir == s.effective_library_path()
    assert cfg.temp_dir == s.effective_temp_dir()
    assert cfg.ffmpeg_path == "ffmpeg"
    assert cfg.ytdlp_args == ("--no-cache-dir", "--retries", "3")
    assert cfg.ffmpeg_args == ("-hide_banner", "-loglevel", "error")
    # mkdir(parents=True, exist_ok=True) both dirs.
    assert cfg.output_dir.is_dir()
    assert cfg.temp_dir.is_dir()


def test_download_config_cookie_and_proxy(tmp_path: object) -> None:
    cookie = tmp_path / "cookies.txt"  # type: ignore[operator]
    s = Settings(
        mode=DeploymentMode.SELFHOST,
        data_dir=tmp_path,  # type: ignore[arg-type]
        download_cookie_file=cookie,
        download_proxy="http://localhost:8080",
    )
    cfg = s.download_config()
    assert cfg.cookie_file == cookie
    assert cfg.proxy == "http://localhost:8080"


def test_engine_knob_settings_present() -> None:
    """Plan-8 amendment check: all eleven engine/session knobs, v4-parity defaults."""
    s = Settings(mode=DeploymentMode.SELFHOST)
    assert s.download_restrict is RestrictMode.NONE
    assert s.download_max_filename_length is None
    assert s.download_id3_separator == "/"
    assert s.download_detect_formats == ()
    assert s.download_skip_explicit is False
    assert s.download_respect_skip_file is False
    assert s.download_create_skip_file is False
    assert s.download_playlist_numbering is False
    assert s.download_retain_track_cover is False
    assert s.download_add_unavailable is False
    assert s.download_scan_existing is False


# --------------------------------------------------------------------------- #
# require_download_auth_consistency — startup fail-fast
# --------------------------------------------------------------------------- #
def test_auth_consistency_raises_when_require_but_auth_inactive() -> None:
    s = Settings(
        mode=DeploymentMode.SELFHOST,
        downloads_require_auth=True,
        auth_enabled=False,
    )
    with pytest.raises(RuntimeError, match="downloads_require_auth"):
        s.require_download_auth_consistency()


def test_auth_consistency_passes_when_auth_active() -> None:
    s = Settings(
        mode=DeploymentMode.SELFHOST,
        downloads_require_auth=True,
        auth_enabled=True,
        auth_secret_key=SecretStr("x" * 32),
    )
    # No raise.
    s.require_download_auth_consistency()


def test_auth_consistency_noop_when_not_required() -> None:
    Settings(mode=DeploymentMode.SELFHOST).require_download_auth_consistency()


def test_ws_progress_require_auth_derives_from_downloads_require_auth() -> None:
    s = Settings(mode=DeploymentMode.SELFHOST)
    assert s.ws_progress_require_auth is None


# --------------------------------------------------------------------------- #
# GET /config download_defaults
# --------------------------------------------------------------------------- #
def _client(settings: Settings) -> httpx.AsyncClient:
    app = create_app(settings)
    app.state.clock = SystemClock()
    app.state.rate_limiter = InMemoryRateLimiter(app.state.clock)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def _config(settings: Settings) -> dict:  # type: ignore[type-arg]
    async with _client(settings) as client:
        resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    return resp.json()


async def test_config_selfhost_download_defaults() -> None:
    body = await _config(Settings(mode=DeploymentMode.SELFHOST))
    assert body["features"]["downloads"] is True
    dd = body["download_defaults"]
    assert dd["output_format"] == "mp3"
    assert dd["bitrate"] == "auto"
    assert dd["output_template"] == "{artists} - {title}.{output-ext}"
    assert dd["concurrency"] == 2
    assert dd["restrict"] == "none"
    assert dd["max_filename_length"] is None
    assert dd["id3_separator"] == "/"
    assert dd["detect_formats"] == []
    assert dd["skip_explicit"] is False
    assert dd["respect_skip_file"] is False
    assert dd["create_skip_file"] is False
    assert dd["playlist_numbering"] is False
    assert dd["retain_track_cover"] is False
    assert dd["add_unavailable"] is False
    assert dd["scan_existing"] is False


async def test_config_hosted_has_no_download_defaults() -> None:
    body = await _config(Settings(mode=DeploymentMode.HOSTED))
    assert body["features"]["downloads"] is False
    assert body["download_defaults"] is None
