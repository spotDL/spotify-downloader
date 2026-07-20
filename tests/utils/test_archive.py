import pytest

from spotdl.utils.archive import Archive


def test_load_archive(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    archive1 = Archive(["a", "b", "c"])
    assert archive1.save("archive.txt") is True
    assert (tmp_path / "archive.txt").is_file() is True
    archive2 = Archive()
    assert archive2.load("archive.txt") is True
    assert len(archive2) == len(archive1)
    diff = archive2 ^ archive1
    assert len(diff) == 0
