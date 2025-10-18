import os
import platform
from pathlib import Path

import pytest

from spotdl.utils.config import (
    get_cache_path,
    get_config_file,
    get_spotdl_path,
    get_spotify_cache_path,
)


@pytest.mark.parametrize(
    "os_name, xdg_exists, legacy_exists, expected_path_type",
    [
        ("Linux", False, False, "xdg"),
        ("Linux", False, True, "legacy"),
        ("Linux", True, False, "xdg"),
        ("Linux", True, True, "xdg"),
        ("Windows", False, False, "legacy"),
    ],
)
def test_get_spotdl_path_scenarios(
    monkeypatch, tmp_path, os_name, xdg_exists, legacy_exists, expected_path_type
):
    """
    Tests that get_spotdl_path correctly follows XDG standards and backward compatibility
    across different operating systems and folder configurations.
    """
    monkeypatch.setattr(platform, "system", lambda: os_name)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    expected_xdg_path = tmp_path / ".config" / "spotdl"
    expected_legacy_path = tmp_path / ".spotdl"

    if xdg_exists:
        expected_xdg_path.mkdir(parents=True)
    if legacy_exists:
        expected_legacy_path.mkdir()

    result_path = get_spotdl_path()

    if expected_path_type == "xdg":
        assert result_path == expected_xdg_path
    else:
        assert result_path == expected_legacy_path

    assert get_config_file() == result_path / "config.json"
    assert get_cache_path() == result_path / ".spotipy"
    assert get_spotify_cache_path() == result_path / ".spotify_cache"
