"""Tests for confined web destinations."""

import pytest

from spotdl.utils.web_folders import folder_destination, music_folders, music_root


def test_default_and_created_destination(tmp_path):
    output = str(tmp_path / "{artist}" / "{title}.{output-ext}")
    assert music_root(output) == tmp_path
    assert folder_destination(output, "") == output
    chosen = folder_destination(output, "My Music", create=True)
    assert chosen == str(tmp_path / "My Music" / "{artists} - {title}.{output-ext}")
    assert music_folders(output) == ["My Music"]
    assert folder_destination(output, "My Music") == chosen


@pytest.mark.parametrize(
    "name", ["..", "../outside", "a/b", "a\\b", "{artist}", "CON", "bad.", "bad:"]
)
def test_invalid_folder_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        folder_destination(str(tmp_path / "{title}.mp3"), name, create=True)


def test_symlink_rejected(tmp_path):
    root = tmp_path / "music"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable")
    output = str(root / "{title}.mp3")
    assert music_folders(output) == []
    with pytest.raises(ValueError):
        folder_destination(output, "escape")
